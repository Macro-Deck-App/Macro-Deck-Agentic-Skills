#!/usr/bin/env python3
"""Static consistency checks for a Macro Deck 3 plugin repository.

Usage: check-plugin.py [repository-root] [--manifest path/to/manifest.json] [--artifact file.macroDeckPlugin]

Checks manifest.json against macrodeck-build.json, the project files, the release workflow and the
repository files, and scans for template leftovers and likely secrets. It complements, and never
replaces, `macrodeck-plugin validate --level publication` and the Creator Guidelines review.

Exit code 0: no errors (warnings may exist). 1: at least one error. 2: usage problem.
Secret findings print the file, line and pattern name only, never the matched value.
Python 3 standard library only.
"""
import json
import pathlib
import re
import subprocess
import sys
import zipfile

ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*(\.[a-z][a-z0-9]*(-[a-z0-9]+)*)+$")
KNOWN_RIDS = {"win-x64", "win-arm64", "osx-x64", "osx-arm64", "linux-x64", "linux-arm64"}
SKIP_DIRS = {"bin", "obj", ".git", "node_modules", "artifacts", ".macrodeck-dev-state", ".macrodeck-policies"}
TEXT_SUFFIXES = {
    ".cs", ".csproj", ".props", ".targets", ".json", ".md", ".yml", ".yaml", ".resx", ".xml", ".txt",
    ".slnx", ".sln", ".config", ".svg", ".sh", ".ps1", ".py", ".js", ".ts",
}
PLACEHOLDER_VALUES = {
    "name": {"my plugin", "macro deck plugin template"},
    "description": {"a macro deck plugin.", "a minimal macro deck 3 plugin."},
}
SECRET_PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("credentials in URL", re.compile(r"https?://[^/\s:@]+:[^/\s:@]{3,}@[^/\s]+")),
    (
        "secret-like assignment",
        re.compile(
            r"""(?ix)\b(password|passwd|secret|api[_-]?key|access[_-]?token|client[_-]?secret|enrollment[_-]?token)\b
            ["']?\s*[:=]\s*["'][^"'\s<>{}$%]{8,}["']"""
        ),
    ),
]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌]")

findings = []


def add(level, message):
    findings.append((level, message))


def rel(path, root):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001
        add("ERROR", f"{path.name}: not valid JSON ({error})")
        return None


def walk(root):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def find_manifests(root):
    return [p for p in walk(root) if p.name == "manifest.json" and (p.parent / "macrodeck-build.json").exists()]


def check_icon(path, declared):
    if (
        "\\" in declared or declared.startswith("/")
        or any(part in ("", ".", "..") for part in declared.split("/"))
        or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}
    ):
        add("ERROR", f"manifest: icon '{declared}' must be a relative path to a png, jpg, jpeg, webp or svg file")
        return
    if path.suffix.lower() == ".svg":
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"<\s*(script|foreignObject|iframe|object|embed|use\b[^>]*href=\"(?!#))", text, re.IGNORECASE):
            add("ERROR", f"icon {declared}: SVG contains active or embedded content (script, foreignObject, iframe, object, embed or external use); the Store accepts passive SVG only")
        if re.search(r"\son[a-z]+\s*=", text, re.IGNORECASE):
            add("ERROR", f"icon {declared}: SVG contains event handler attributes; the Store accepts passive SVG only")
        if re.search(r"(href|src)\s*=\s*[\"'](?!#|data:image/)[a-z]+:", text, re.IGNORECASE) or re.search(r"url\(\s*[\"']?https?:", text, re.IGNORECASE):
            add("ERROR", f"icon {declared}: SVG references something outside itself; only an embedded raster image is allowed")


def check_manifest(root, manifest_path, manifest, build):
    source_dir = manifest_path.parent
    for key in ("manifestVersion", "id", "name", "version", "entrypoints"):
        if key not in manifest:
            add("ERROR", f"manifest: required field '{key}' is missing")
    if manifest.get("manifestVersion") != 1:
        add("ERROR", "manifest: manifestVersion must be 1")

    plugin_id = manifest.get("id", "")
    if not ID_PATTERN.match(plugin_id) or len(plugin_id) > 128:
        add("ERROR", f"manifest: id '{plugin_id}' does not match the package-id rules")
    if ID_PATTERN.match(plugin_id) and plugin_id.count(".") < 2:
        add("ERROR", f"manifest: id '{plugin_id}' has fewer than three dot-separated parts; the Creator Portal requires at least three (for example com.author.plugin-name)")
    if plugin_id.startswith("com.example.") or plugin_id.startswith("app.macro-deck"):
        add("ERROR", f"manifest: id '{plugin_id}' is a template placeholder or uses the Macro Deck namespace")
    if re.search(r"(^|[.-])macro-?deck([.-]|$)", plugin_id) and not plugin_id.startswith("app.macro-deck"):
        add("WARN", f"manifest: id '{plugin_id}' contains 'macro-deck'; guidelines forbid it as namespace or publisher identity")

    for key, placeholders in PLACEHOLDER_VALUES.items():
        if str(manifest.get(key, "")).strip().lower() in placeholders:
            add("ERROR", f"manifest: '{key}' still has the template default")
    name = str(manifest.get("name", ""))
    implies_official = re.search(r"\bofficial\b", name, re.IGNORECASE)
    uses_macro_deck = re.search(r"\bmacro ?deck\b", name, re.IGNORECASE) and "for macro deck" not in name.lower()
    if implies_official or uses_macro_deck:
        add("WARN", f"manifest: name '{name}' may imply an official relationship; check the naming rules")

    publisher = (manifest.get("publisher") or {}).get("name", "")
    if not publisher or publisher.strip().lower() == "example publisher":
        add("ERROR", "manifest: publisher.name is missing or still the template placeholder")
    repository = manifest.get("repository", "")
    if not re.match(r"^https://github\.com/[^/\s]+/[^/\s]+$", repository or "") or "/example/" in (repository or ""):
        add("ERROR", f"manifest: repository '{repository}' must be https://github.com/<owner>/<name> and not a placeholder")
    if not manifest.get("license"):
        add("ERROR", "manifest: license (SPDX identifier) is missing")
    description = manifest.get("description") or ""
    if not description:
        add("ERROR", "manifest: description is missing")
    elif len(description) > 500:
        add("ERROR", "manifest: description is longer than 500 characters; the Store registry caps the package description")
    elif len(description) > 200:
        add("WARN", "manifest: description is longer than 200 characters; the Store summary is limited to 200, keep the first sentence short")
    if not (manifest.get("compatibility") or {}).get("macroDeck"):
        add("ERROR", "manifest: compatibility.macroDeck is missing")

    icon = manifest.get("icon")
    if not icon:
        add("ERROR", "manifest: icon is missing")
    elif not (source_dir / icon).is_file():
        add("ERROR", f"manifest: icon '{icon}' does not exist next to the manifest")
    else:
        check_icon(source_dir / icon, icon)

    ai = manifest.get("ai")
    if ai is None:
        add("ERROR", "manifest: 'ai' is not declared; the Store shows 'not declared'. Declare it explicitly, even when every flag is false")
    elif not isinstance(ai, dict):
        add("ERROR", "manifest: 'ai' must be an object")
    else:
        for flag in ("interaction", "generatedContent", "generatedAssets"):
            if flag in ai and not isinstance(ai[flag], bool):
                add("ERROR", f"manifest: ai.{flag} must be true or false")
        add("INFO", f"manifest: ai = {json.dumps(ai, sort_keys=True)} (verify against the actual plugin, see references/manifests.md)")

    entrypoints = manifest.get("entrypoints") or {}
    targets = (build or {}).get("targets") or {}
    for rid in entrypoints:
        if rid not in KNOWN_RIDS:
            add("WARN", f"manifest: entrypoint rid '{rid}' is not one of the known runtime identifiers")
    if set(entrypoints) != set(targets):
        add(
            "ERROR",
            f"manifest vs build: entrypoint rids {sorted(entrypoints)} differ from macrodeck-build.json targets {sorted(targets)}",
        )

    assembly_names = set()
    for rid, entry in entrypoints.items():
        executable = entry.get("executable", "")
        runtime = (entry.get("runtime") or {})
        kind = str(runtime.get("kind", "SelfContained")).lower()
        expected_prefix = f"runtimes/{rid}/"
        if not executable.startswith(expected_prefix):
            add("ERROR", f"manifest: entrypoint '{rid}' executable '{executable}' must start with '{expected_prefix}'")
        base = executable.rsplit("/", 1)[-1]
        if kind == "frameworkdependent":
            if not base.endswith(".dll"):
                add("ERROR", f"manifest: framework-dependent entrypoint '{rid}' must name a .dll")
            if not runtime.get("dotnetVersion"):
                add("ERROR", f"manifest: entrypoint '{rid}' needs runtime.dotnetVersion")
            assembly_names.add(base[:-4] if base.endswith(".dll") else base)
        else:
            add("WARN", f"manifest: entrypoint '{rid}' is self-contained; plugins must be framework-dependent unless Macro Deck does not ship the needed runtime")
            assembly_names.add(re.sub(r"\.(exe|dll)$", "", base))
        if re.search(r"\.(sh|bat|cmd|ps1|command)$", executable):
            add("ERROR", f"manifest: entrypoint '{rid}' must not be a script")

        target = targets.get(rid)
        if not target:
            continue
        args = [str(a) for a in target.get("arguments", [])]
        joined = " ".join(args)
        if "-r" in args and args[args.index("-r") + 1] != rid:
            add("ERROR", f"build: target '{rid}' publishes for runtime '{args[args.index('-r') + 1]}'")
        if "-r" not in args and "--runtime" not in args:
            add("WARN", f"build: target '{rid}' does not pass -r {rid}")
        if kind == "frameworkdependent":
            if "--self-contained" not in args or args[args.index("--self-contained") + 1].lower() != "false":
                add("ERROR", f"build: target '{rid}' must pass --self-contained false to match its FrameworkDependent entrypoint")
            if "-p:UseAppHost=false" not in args:
                add("ERROR", f"build: target '{rid}' must pass -p:UseAppHost=false for a framework-dependent entrypoint")
        if re.search(r"SelfContained=true|--self-contained\s+true|PublishSingleFile|PublishTrimmed", joined, re.IGNORECASE):
            add("ERROR", f"build: target '{rid}' enables self-contained, single-file or trimmed publishing")
        if target.get("output") != f"bin/publish/{rid}":
            add("WARN", f"build: target '{rid}' output is '{target.get('output')}', template convention is 'bin/publish/{rid}'")
        for arg in args:
            if arg.endswith((".csproj", ".fsproj", ".vbproj")) and not (source_dir / arg).is_file():
                add("ERROR", f"build: target '{rid}' publishes '{arg}' which does not exist next to the manifest")
    return source_dir, assembly_names


def check_projects(root, source_dir, assembly_names):
    project_files = [p for p in walk(root) if p.suffix in {".csproj", ".fsproj", ".vbproj"}]
    props = [p for p in walk(root) if p.name in {"Directory.Build.props", "Directory.Build.targets", "Directory.Packages.props"}]
    plugin_projects = [p for p in project_files if p.parent == source_dir]
    for path in project_files + props:
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"<(Publish)?SelfContained>\s*true\s*</", text, re.IGNORECASE):
            add("ERROR", f"{rel(path, root)}: enables SelfContained; plugins must not be published self-contained")
        if re.search(r"<(PublishSingleFile|PublishTrimmed|PublishAot)>\s*true\s*</", text, re.IGNORECASE):
            add("ERROR", f"{rel(path, root)}: enables single-file, trimmed or AOT publishing, which Macro Deck plugins do not use")
        if re.search(r"<(Assembly|Root)Name>\s*MacroDeck\.", text) or re.search(r"<AssemblyName>\s*MacroDeck\b", text):
            add("ERROR", f"{rel(path, root)}: assembly or namespace starts with 'MacroDeck'; guidelines forbid it for third-party plugins")
        if re.search(r"<HintPath>|<Reference\s+Include=[^>]*\.dll", text):
            add("ERROR", f"{rel(path, root)}: references a precompiled DLL; third-party dependencies must come from NuGet")
        if re.search(r"Version=\"[^\"]*\*[^\"]*\"", text) and "MacroDeckSdkVersion" not in text and path.name != "Directory.Packages.props":
            add("WARN", f"{rel(path, root)}: floating package version found")
    for path in plugin_projects:
        text = path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"<AssemblyName>\s*([^<\s]+)\s*</AssemblyName>", text)
        assembly = match.group(1) if match else path.stem
        if assembly_names and assembly not in assembly_names:
            add("ERROR", f"project {rel(path, root)}: AssemblyName '{assembly}' does not match the manifest entrypoint executable name(s) {sorted(assembly_names)}")
        if "MacroDeck.Plugin.Analyzers" not in text:
            add("WARN", f"{rel(path, root)}: MacroDeck.Plugin.Analyzers is not referenced")
        if not re.search(r"<Content\s+Include=\"manifest\.json\"", text):
            add("WARN", f"{rel(path, root)}: manifest.json is not copied to the output directory")
    if not plugin_projects:
        add("ERROR", f"no project file next to {rel(source_dir / 'manifest.json', root)}")

    packages = (root / "Directory.Packages.props")
    if packages.exists():
        text = packages.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"<MacroDeckSdkVersion[^>]*>\s*([^<\s]+)\s*</MacroDeckSdkVersion>", text)
        if match and "*" in match.group(1):
            add("WARN", f"Directory.Packages.props: MacroDeckSdkVersion is floating ('{match.group(1)}'); pin it to the version resolve-versions.py reports")
        elif match:
            add("INFO", f"Directory.Packages.props: MacroDeckSdkVersion = {match.group(1)} (compare with scripts/resolve-versions.py and the SDK policy minimum)")


def check_ci(root, path, text):
    name = rel(path, root)
    sdk = sdk_version(root)
    for match in re.finditer(r"MacroDeck\.Plugin\.Cli\s+--version\s+(\S+)", text):
        if sdk and "*" not in sdk and match.group(1) != sdk:
            add("ERROR", f"{name}: CLI version {match.group(1)} must equal the Macro Deck SDK version {sdk}")
    for match in re.finditer(r"uses:\s*(\S+)@(\S+)", text):
        if not re.fullmatch(r"[0-9a-f]{40}", match.group(2)):
            add("WARN", f"{name}: action {match.group(1)} is not pinned to a full commit SHA")
    if "permissions:" not in text:
        add("WARN", f"{name}: no explicit permissions block; set contents: read")
    if re.search(r"<[A-Z_]+>", text):
        add("ERROR", f"{name}: unresolved template placeholder")


def sdk_version(root):
    props = root / "Directory.Packages.props"
    if props.exists():
        match = re.search(r"<MacroDeckSdkVersion[^>]*>\s*([^<\s]+)\s*</MacroDeckSdkVersion>", props.read_text(encoding="utf-8", errors="replace"))
        if match:
            return match.group(1)
    return None


def check_workflows(root, source_dir):
    workflows = root / ".github" / "workflows"
    release = None
    if workflows.is_dir():
        for path in sorted(workflows.iterdir()):
            if path.suffix in {".yml", ".yaml"}:
                text = path.read_text(encoding="utf-8", errors="replace")
                if "publish-plugin.yml" in text:
                    release = (path, text)
                elif re.search(r"MacroDeck\.Plugin\.Templates|dotnet new install|packaging/MacroDeck", text, re.IGNORECASE):
                    add("ERROR", f"{rel(path, root)}: looks like a leftover template workflow; remove it")
                elif path.stem == "ci":
                    check_ci(root, path, text)
                else:
                    add("INFO", f"{rel(path, root)}: extra workflow, review that it is intended and minimally permissioned")
    if not any(p.stem == "ci" for p in workflows.iterdir() if p.suffix in {".yml", ".yaml"}) if workflows.is_dir() else True:
        add("WARN", "no CI workflow (.github/workflows/ci.yaml) that builds and tests the plugin")
    if not release:
        add("ERROR", "no release workflow calling Macro-Deck-App/GitHub-Actions/.github/workflows/publish-plugin.yml")
        return
    path, text = release
    name = rel(path, root)
    if not path.name.startswith("release."):
        add("WARN", f"{name}: expected file name release.yaml")
    if not re.search(r"uses:\s*Macro-Deck-App/GitHub-Actions/\.github/workflows/publish-plugin\.yml@v\d+", text):
        add("ERROR", f"{name}: must call the official workflow at a version tag (the Platform only accepts a v* tag)")
    if not re.search(r"types:\s*\[\s*published\s*\]", text):
        add("ERROR", f"{name}: must trigger on release types: [published]")
    if "id-token: write" not in text or "contents: read" not in text:
        add("ERROR", f"{name}: the publish job needs permissions contents: read and id-token: write")
    extra = re.findall(r"^\s+(?!contents|id-token)([a-z-]+):\s*(write|read)", text, re.MULTILINE)
    if extra:
        add("ERROR", f"{name}: grants more than contents: read and id-token: write ({extra})")
    if "github.event.release.tag_name" not in text:
        add("ERROR", f"{name}: version must come from github.event.release.tag_name")
    match = re.search(r"^\s+source:\s*(\S+)", text, re.MULTILINE)
    expected = source_dir.relative_to(root).as_posix() if source_dir != root else "."
    if not match:
        add("ERROR", f"{name}: 'source' input is missing")
    elif match.group(1).strip("'\"").rstrip("/") != expected:
        add("ERROR", f"{name}: source '{match.group(1)}' differs from the directory holding manifest.json ('{expected}')")
    cli = re.search(r"^\s+cli-version:\s*['\"]?([^\s'\"#]+)", text, re.MULTILINE)
    if not cli:
        add("ERROR", f"{name}: cli-version is not pinned; the default resolves by SemVer order and may pick an old preview")
    else:
        sdk = sdk_version(root)
        if sdk is None or "*" in sdk:
            add("WARN", f"{name}: cannot compare cli-version {cli.group(1)} with the SDK version (not pinned in Directory.Packages.props)")
        elif cli.group(1) != sdk:
            add("ERROR", f"{name}: cli-version {cli.group(1)} must equal the Macro Deck SDK version {sdk}")
    if re.search(r"run-stub-host:\s*false|run-tests:\s*false", text):
        add("ERROR", f"{name}: do not disable the stub host or the tests")
    if "secrets." in text:
        add("ERROR", f"{name}: the publish workflow needs no secrets")


def check_repo_files(root, manifest):
    license_file = next((root / n for n in ("LICENSE", "LICENSE.md", "LICENSE.txt") if (root / n).exists()), None)
    if not license_file:
        add("ERROR", "no LICENSE file")
    else:
        text = license_file.read_text(encoding="utf-8", errors="replace")
        if "Macro Deck Contributors" in text:
            add("ERROR", f"{license_file.name}: copyright holder is still 'Macro Deck Contributors' from the template; use the actual rights holder")
        spdx = str(manifest.get("license", ""))
        hints = {"MIT": "MIT License", "Apache-2.0": "Apache License", "GPL-3.0": "GNU GENERAL PUBLIC LICENSE", "GPL-3.0-only": "GNU GENERAL PUBLIC LICENSE", "AGPL-3.0": "GNU AFFERO", "LGPL-3.0": "GNU LESSER", "MPL-2.0": "Mozilla Public License"}
        hint = hints.get(spdx)
        if hint and hint.lower() not in text.lower():
            add("ERROR", f"{license_file.name} does not look like {spdx}, the license declared in manifest.json")
        if not re.search(r"Copyright\s*(\(c\)|©)?\s*\d{4}", text, re.IGNORECASE) and spdx in {"MIT", "BSD-2-Clause", "BSD-3-Clause", "ISC"}:
            add("WARN", f"{license_file.name}: no copyright line found")
    for name in ("README.md", "AGENTS.md"):
        if not (root / name).exists():
            add("ERROR", f"{name} is missing")
    readme = root / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="replace")
        if re.search(r"dotnet new macrodeck-plugin|A starting point for an out-of-process|Macro Deck plugin template|Acme", text):
            add("ERROR", "README.md still contains template text")
        if len(text.strip()) < 400:
            add("WARN", "README.md is very short")
    for name in ("NOTICE", "THIRD-PARTY-NOTICES"):
        if not (root / name).exists():
            add("WARN", f"{name} is missing; confirm with scripts/inventory-dependencies.py that no bundled package or asset requires it")
    if (root / "CLAUDE.md").exists() and (root / "AGENTS.md").exists():
        text = (root / "CLAUDE.md").read_text(encoding="utf-8", errors="replace")
        if len(text.strip()) > 600 and "AGENTS.md" not in text:
            add("WARN", "CLAUDE.md carries instructions that compete with AGENTS.md")


def check_package_sources(root):
    if (root / "local-feed").exists():
        add("ERROR", "local-feed/ folder exists; remove it (local NuGet feeds are flagged in the Store review)")
    for path in walk(root):
        if path.name.lower() == "nuget.config":
            text = path.read_text(encoding="utf-8", errors="replace")
            text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
            for value in re.findall(r"<add\s+key=\"[^\"]*\"\s+value=\"([^\"]+)\"", text):
                if "api.nuget.org" not in value and not value.startswith("https://nuget.org"):
                    add("ERROR", f"{rel(path, root)}: package source '{value}' other than nuget.org; remove local and alternate NuGet feeds")
        elif path.suffix in {".csproj", ".props", ".targets"}:
            if "RestoreSources" in path.read_text(encoding="utf-8", errors="replace"):
                add("ERROR", f"{rel(path, root)}: sets RestoreSources; remove alternate package sources")


def check_tracked_binaries(root):
    try:
        files = subprocess.run(
            ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True
        ).stdout.splitlines()
    except Exception:  # noqa: BLE001
        return
    for line in files:
        lower = line.lower()
        parts = lower.split("/")
        if lower.endswith((".dll", ".exe", ".so", ".dylib", ".nupkg", ".pdb", ".macrodeckplugin")) or any(p in ("bin", "obj", "publish", "artifacts") for p in parts[:-1]):
            add("ERROR", f"tracked build output or compiled binary: {line}; remove it from Git (git rm -r --cached), ignore it, and reference dependencies as NuGet packages")
    ignore = root / ".gitignore"
    text = ignore.read_text(encoding="utf-8", errors="replace") if ignore.exists() else ""
    if not re.search(r"^(\*\*/)?(\[Bb\]|b)in/?$", text, re.MULTILINE) or not re.search(r"^(\*\*/)?(\[Oo\]|o)bj/?$", text, re.MULTILINE):
        add("WARN", ".gitignore does not appear to ignore bin/ and obj/")


def check_artifact(path):
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except Exception as error:  # noqa: BLE001
        add("ERROR", f"artifact {path.name}: not a readable archive ({error})")
        return
    add("INFO", f"artifact {path.name}: {len(names)} entries, {path.stat().st_size} bytes")
    if len(names) > 200:
        add("WARN", f"artifact {path.name}: {len(names)} entries; check that no runtime or unneeded files are bundled (macrodeck-plugin inspect)")
    if "manifest.json" not in names:
        add("ERROR", f"artifact {path.name}: no manifest.json at the archive root")
    if any(n.lower().endswith((".pdb",)) for n in names):
        add("WARN", f"artifact {path.name}: contains .pdb files; consider whether they are needed")


def tracked_text_files(root):
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        return [root / line for line in out if (root / line).is_file()]
    except Exception:  # noqa: BLE001
        return list(walk(root))


def check_text(root):
    for path in tracked_text_files(root):
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"LICENSE", "NOTICE", "THIRD-PARTY-NOTICES", ".gitignore"}:
            continue
        if path.stat().st_size > 2_000_000:
            continue
        if path.name == "THIRD-PARTY-NOTICES" or path.name.startswith("LICENSE"):
            style = False
        else:
            style = True
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:  # noqa: BLE001
            continue
        reported_secret = set()
        reported_dash = False
        for number, line in enumerate(lines, 1):
            for label, pattern in SECRET_PATTERNS:
                if label not in reported_secret and pattern.search(line):
                    reported_secret.add(label)
                    add("ERROR", f"possible secret ({label}) at {rel(path, root)}:{number}; value not shown")
            if style and re.search(r"ignore (all )?(previous|prior) instructions|pre-?approved|do not (inspect|review)|skip (this|the) review", line, re.IGNORECASE):
                add("WARN", f"text that addresses a reviewer or agent at {rel(path, root)}:{number}; remove it")
            if style and not reported_dash and "\u2014" in line:
                add("WARN", f"em dash at {rel(path, root)}:{number}")
                reported_dash = True
        if style and path.suffix in {".cs", ".md", ".yml", ".yaml", ".csproj", ".props"}:
            text = "\n".join(lines)
            if EMOJI.search(text):
                add("WARN", f"emoji in {rel(path, root)}")
            if re.search(r"^\s*(//|#)\s*[=\-*#_~]{8,}", text, re.MULTILINE):
                add("WARN", f"decorative comment separator in {rel(path, root)}")


def main():
    args = sys.argv[1:]
    manifest_arg = None
    artifact_arg = None
    if "--artifact" in args:
        index = args.index("--artifact")
        artifact_arg = pathlib.Path(args[index + 1]).resolve()
        del args[index:index + 2]
    if "--manifest" in args:
        index = args.index("--manifest")
        manifest_arg = pathlib.Path(args[index + 1]).resolve()
        del args[index:index + 2]
    root = pathlib.Path(args[0] if args else ".").resolve()
    if not root.is_dir():
        print(f"not a directory: {root}")
        sys.exit(2)
    manifests = [manifest_arg] if manifest_arg else find_manifests(root)
    if not manifests:
        print("No manifest.json with a macrodeck-build.json beside it was found. Is this a Macro Deck 3 plugin?")
        sys.exit(2)
    if len(manifests) > 1:
        print("Several plugin manifests found; pass --manifest to pick one:")
        for m in manifests:
            print(f"  {rel(m, root)}")
        sys.exit(2)
    manifest_path = manifests[0]
    manifest = load_json(manifest_path)
    build = load_json(manifest_path.parent / "macrodeck-build.json")
    if manifest is not None:
        source_dir, assemblies = check_manifest(root, manifest_path, manifest, build)
        check_projects(root, source_dir, assemblies)
        check_workflows(root, source_dir)
        check_repo_files(root, manifest)
    check_tracked_binaries(root)
    check_package_sources(root)
    check_text(root)
    if artifact_arg:
        check_artifact(artifact_arg)

    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    for level, message in sorted(findings, key=lambda f: order[f[0]]):
        print(f"{level}: {message}")
    errors = sum(1 for level, _ in findings if level == "ERROR")
    warnings = sum(1 for level, _ in findings if level == "WARN")
    print(f"\n{errors} error(s), {warnings} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
