#!/usr/bin/env python3
"""Inventory the NuGet packages a plugin actually ships, with license facts from their own metadata.

Usage:
  inventory-dependencies.py <publish-dir-or-deps.json> [--notices OUTPUT] [--header-name NAME]

<publish-dir> is a `dotnet publish` output such as src/MyPlugin/bin/publish/linux-x64, produced by
`macrodeck-plugin build`. The tool reads *.deps.json, keeps packages that contribute runtime
assets, and reads each package's .nuspec from the local NuGet cache (so run a restore first).

Output (stdout): one JSON document with id, version, license, authors, copyright, project URL,
repository URL and a `needsReview` list for anything the metadata does not settle.

--notices writes a DRAFT THIRD-PARTY-NOTICES file in the layout Macro Deck uses. License texts
come only from (a) a license file inside the package, or (b) the SPDX license-list text for the
package's license expression, downloaded from the official spdx/license-list-data repository.
Anything else is marked NEEDS MANUAL REVIEW; nothing is invented. Copyright lines come from the
package metadata only. Review the draft, and add bundled assets (icons, fonts, images) by hand.

This script does not judge compatibility, trustworthiness or vulnerabilities. See
references/dependency-security.md and references/licensing.md.
Python 3 standard library only.
"""
import json
import os
import pathlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

SPDX_TEXT = "https://raw.githubusercontent.com/spdx/license-list-data/main/text/{id}.txt"


def nuget_cache():
    env = os.environ.get("NUGET_PACKAGES")
    return pathlib.Path(env) if env else pathlib.Path.home() / ".nuget" / "packages"


def strip_ns(tag):
    return tag.split("}", 1)[-1]


def read_nuspec(package_dir):
    files = list(package_dir.glob("*.nuspec"))
    if not files:
        return {}
    root = ET.parse(files[0]).getroot()
    metadata = next((c for c in root if strip_ns(c.tag) == "metadata"), None)
    data = {}
    if metadata is None:
        return data
    for child in metadata:
        tag = strip_ns(child.tag)
        if tag == "license":
            data["licenseType"] = child.attrib.get("type")
            data["license"] = (child.text or "").strip()
        elif tag == "repository":
            data["repositoryUrl"] = child.attrib.get("url")
        elif child.text and child.text.strip():
            data[tag] = child.text.strip()
    return data


def shipped_packages(deps_path):
    deps = json.loads(deps_path.read_text(encoding="utf-8"))
    runtime_target = deps.get("runtimeTarget", {}).get("name")
    targets = deps.get("targets", {})
    target = targets.get(runtime_target) or next(iter(targets.values()), {})
    libraries = deps.get("libraries", {})
    result = {}
    for key, info in target.items():
        library = libraries.get(key, {})
        if library.get("type") != "package":
            continue
        if not (info.get("runtime") or info.get("native") or info.get("runtimeTargets")):
            continue
        name, _, version = key.partition("/")
        result[name] = version
    return result


def spdx_text(identifier, cache):
    if identifier in cache:
        return cache[identifier]
    text = None
    try:
        request = urllib.request.Request(SPDX_TEXT.format(id=identifier), headers={"User-Agent": "macro-deck-plugin-creator"})
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
    except Exception:  # noqa: BLE001
        text = None
    cache[identifier] = text
    return text


def first_spdx_id(expression):
    """Pick the first identifier of an expression like 'MIT OR Apache-2.0'; None for anything else."""
    if not expression:
        return None
    parts = re.split(r"\s+(?:OR|AND)\s+", expression.strip("() "))
    candidate = parts[0].strip("() ")
    return candidate if re.fullmatch(r"[A-Za-z0-9.+-]+", candidate) else None


def license_text(package_dir, info, cache):
    if info.get("licenseType") == "file" and info.get("license"):
        path = package_dir / info["license"]
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace").strip(), f"file {info['license']} from the package"
    if info.get("licenseType") == "expression":
        if re.search(r"\s+AND\s+", info.get("license") or ""):
            return None, None
        identifier = first_spdx_id(info.get("license"))
        if identifier:
            text = spdx_text(identifier, cache)
            if text:
                return text.strip(), f"SPDX license list text for {identifier}"
    return None, None


def build(deps_files, notices_path, header_name):
    shipped = {}
    for deps_file in deps_files:
        shipped.update(shipped_packages(deps_file))
    own = {p.stem.replace(".deps", "") for p in deps_files}
    cache_dir = nuget_cache()
    packages, needs_review = [], []
    for name in sorted(shipped, key=str.lower):
        if name in own:
            continue
        version = shipped[name]
        package_dir = cache_dir / name.lower() / version
        info = read_nuspec(package_dir) if package_dir.is_dir() else {}
        entry = {
            "id": name,
            "version": version,
            "license": info.get("license"),
            "licenseType": info.get("licenseType"),
            "licenseUrl": info.get("licenseUrl"),
            "authors": info.get("authors"),
            "copyright": info.get("copyright"),
            "projectUrl": info.get("projectUrl"),
            "repositoryUrl": info.get("repositoryUrl"),
        }
        if not package_dir.is_dir():
            needs_review.append(f"{name} {version}: not in the local NuGet cache; run a restore first")
        elif not info.get("license"):
            needs_review.append(f"{name} {version}: no license expression or file in the nuspec (legacy licenseUrl: {info.get('licenseUrl')})")
        elif info.get("licenseType") == "expression" and re.search(r"\b(GPL|AGPL|LGPL|MPL|EPL|CDDL|SSPL|BUSL)", info["license"]):
            needs_review.append(f"{name} {version}: license {info['license']} has copyleft or source-offer terms; confirm compatibility with the plugin license")
        packages.append(entry)

    output = {"shippedPackages": packages, "needsReview": needs_review, "note": "Runtime assemblies provided by the Macro Deck .NET runtime are not packages and are not listed."}
    print(json.dumps(output, indent=2))

    if notices_path:
        write_notices(pathlib.Path(notices_path), packages, cache_dir, header_name)


def write_notices(path, packages, cache_dir, header_name):
    texts, order, spdx_cache = {}, [], {}
    lines = [
        "THIRD-PARTY SOFTWARE NOTICES AND INFORMATION",
        header_name,
        "",
        f"{header_name} includes the third-party components listed below. Each component is",
        "provided under its own license, reproduced in the license texts section.",
        "",
        "=" * 80,
        "NuGet packages",
        "=" * 80,
        "",
    ]
    for pkg in packages:
        package_dir = cache_dir / pkg["id"].lower() / pkg["version"]
        text, source = license_text(package_dir, pkg, spdx_cache) if package_dir.is_dir() else (None, None)
        copyright_line = pkg.get("copyright") or ""
        key = (text, copyright_line) if text else None
        lines.append(pkg["id"])
        lines.append(f"  License: {pkg.get('license') or 'UNKNOWN'}")
        url = pkg.get("repositoryUrl") or pkg.get("projectUrl")
        if url:
            lines.append(f"  URL: {url}")
        if key:
            if key not in texts:
                texts[key] = len(order) + 1
                order.append((pkg["id"], copyright_line, text, source))
            lines.append(f"  Texts: [{texts[key]}]")
        else:
            lines.append("  Texts: NEEDS MANUAL REVIEW (no license text could be taken from the package or the SPDX list)")
        lines.append("")
    lines += ["=" * 80, "License and notice texts", "=" * 80, ""]
    for number, (name, copyright_line, text, source) in enumerate(order, 1):
        lines.append(f"[{number}] {name}")
        lines.append("-" * 80)
        if copyright_line:
            lines.append(copyright_line)
            lines.append("")
        lines.append(text)
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"draft written to {path}", file=sys.stderr)


def main():
    args = sys.argv[1:]
    notices = None
    header = "Plugin"
    if "--notices" in args:
        i = args.index("--notices")
        notices = args[i + 1]
        del args[i:i + 2]
    if "--header-name" in args:
        i = args.index("--header-name")
        header = args[i + 1]
        del args[i:i + 2]
    if not args:
        print(__doc__)
        sys.exit(2)
    target = pathlib.Path(args[0])
    deps_files = [target] if target.is_file() else sorted(target.glob("*.deps.json"))
    if not deps_files:
        print(f"no *.deps.json found in {target}; build with `macrodeck-plugin build` first")
        sys.exit(2)
    build(deps_files, notices, header)


if __name__ == "__main__":
    main()
