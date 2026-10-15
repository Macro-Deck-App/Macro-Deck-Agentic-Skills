#!/usr/bin/env python3
"""Resolve the Macro Deck package versions a new plugin should use, from live sources.

Prints JSON. Needs only Python 3 and network access to nuget.org and api.macro-deck.app.
Nothing here is cached: run it again at the start of every task.

Rules applied:
  1. Latest stable version if one is listed, otherwise
  2. the most recently PUBLISHED listed prerelease (not the highest SemVer, because SemVer sorts
     `beta` before `preview` and unlisted versions are invisible to NuGet restore), and
  3. the result must satisfy minimumSdkVersion from the dependency policy. That comparison uses the
     Creator Portal's own ordering, where release stages rank alpha < preview < beta < rc < release
     (so 3.0.0-preview.10 is OLDER than 3.0.0-beta.4), not NuGet's alphabetical order, and
  4. the plugin CLI version must equal the SDK version (Creator Portal moderators require it).
"""
import gzip
import json
import re
import sys
import urllib.request

REGISTRATION = "https://api.nuget.org/v3/registration5-gz-semver2/{id}/index.json"
FLAT_CONTAINER = "https://api.nuget.org/v3-flatcontainer/{id}/index.json"
SDK_POLICY = "https://api.macro-deck.app/api/v1/public/dependency-policy/sdk"
DEFAULT_PACKAGES = [
    "MacroDeck.Sdk",
    "MacroDeck.Plugin.Hosting",
    "MacroDeck.Plugin.Analyzers",
    "MacroDeck.Plugin.Serilog",
    "MacroDeck.Plugin.Testing",
    "MacroDeck.Localization",
    "MacroDeck.Plugin.Protocol",
    "MacroDeck.Ui",
    "MacroDeck.Ui.Model",
    "MacroDeck.Ui.Testing",
    "MacroDeck.Plugin.Cli",
    "MacroDeck.Plugin.Templates",
]


def get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "macro-deck-plugin-creator"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return json.loads(data)


def semver_key(version):
    """Sort key following SemVer 2.0 precedence (build metadata ignored)."""
    version = version.split("+", 1)[0]
    core, _, pre = version.partition("-")
    nums = tuple(int(p) for p in core.split("."))
    if not pre:
        return (nums, (1,))
    parts = []
    for ident in pre.split("."):
        parts.append((0, int(ident), "") if ident.isdigit() else (1, 0, ident))
    return (nums, (0, tuple(parts)))


STAGES = {"alpha": 0, "preview": 1, "beta": 2, "rc": 3}


def platform_key(version):
    """Ordering the Creator Portal applies to the minimum SDK version (stages in release order)."""
    version = version.split("+", 1)[0]
    core, _, pre = version.partition("-")
    nums = tuple(int(p) for p in core.split("."))
    if not pre:
        return (nums, (1,))
    parts = []
    for index, ident in enumerate(pre.split(".")):
        if index == 0 and ident.lower() in STAGES:
            parts.append((0, STAGES[ident.lower()], ""))
        elif ident.isdigit():
            parts.append((1, int(ident), ""))
        else:
            parts.append((2, 0, ident.lower()))
    return (nums, (0, tuple(parts)))


def list_versions(package_id):
    index = get_json(REGISTRATION.format(id=package_id.lower()))
    entries = []
    for page in index.get("items", []):
        items = page.get("items")
        if items is None:
            items = get_json(page["@id"]).get("items", [])
        for item in items:
            entry = item["catalogEntry"]
            entries.append(
                {
                    "version": entry["version"],
                    "published": entry.get("published", ""),
                    "listed": entry.get("listed", True),
                }
            )
    return entries


def resolve(package_id):
    try:
        entries = [e for e in list_versions(package_id) if e["listed"]]
    except Exception as error:  # noqa: BLE001 - report and continue with the other packages
        return {"error": f"{type(error).__name__}: {error}"}
    if not entries:
        return {"error": "no listed versions"}
    stable = [e for e in entries if "-" not in e["version"]]
    pre = [e for e in entries if "-" in e["version"]]
    latest_stable = max(stable, key=lambda e: semver_key(e["version"]))["version"] if stable else None
    latest_published_pre = max(pre, key=lambda e: e["published"])["version"] if pre else None
    highest_semver = max(entries, key=lambda e: semver_key(e["version"]))["version"]
    floating = None
    try:
        # The flat container also lists unlisted versions; a floating range such as 3.0.0-* can resolve there.
        every = get_json(FLAT_CONTAINER.format(id=package_id.lower()))["versions"]
        floating = max(every, key=semver_key)
    except Exception:  # noqa: BLE001 - informational only
        pass
    return {
        "highestIncludingUnlisted": floating,
        "latestStable": latest_stable,
        "latestListedPrerelease": latest_published_pre,
        "highestListedBySemVer": highest_semver,
        "recommended": latest_stable or latest_published_pre,
        "recommendedIsPrerelease": latest_stable is None,
    }


def main():
    packages = sys.argv[1:] or DEFAULT_PACKAGES
    result = {"packages": {}, "warnings": []}
    try:
        policy = get_json(SDK_POLICY)
        result["policy"] = policy
        minimum = policy.get("minimumSdkVersion")
    except Exception as error:  # noqa: BLE001
        policy, minimum = {}, None
        result["warnings"].append(f"Could not read the SDK dependency policy: {error}. Stop and report this.")

    for package_id in packages:
        info = resolve(package_id)
        result["packages"][package_id] = info
        if "error" in info:
            result["warnings"].append(f"{package_id}: {info['error']}")
            continue
        if minimum and platform_key(info["recommended"]) < platform_key(minimum):
            result["warnings"].append(
                f"{package_id}: recommended {info['recommended']} is below minimumSdkVersion {minimum}."
            )
        highest = info.get("highestIncludingUnlisted") or info["highestListedBySemVer"]
        if highest != info["recommended"] and not package_id.endswith(("Cli", "Templates")):
            result["warnings"].append(
                f"{package_id}: a floating range such as '3.0.0-*' can resolve to {highest}, "
                f"not {info['recommended']}. Pin MacroDeckSdkVersion explicitly."
            )

    sdk = result["packages"].get("MacroDeck.Sdk", {})
    cli = result["packages"].get("MacroDeck.Plugin.Cli", {})
    if sdk.get("recommended") and cli.get("recommended") and sdk["recommended"] != cli["recommended"]:
        result["warnings"].append(
            f"SDK {sdk['recommended']} and CLI {cli['recommended']} differ. Use the same version for both "
            "(cli-version must equal the SDK version) and confirm that exact CLI version exists on nuget.org."
        )
    result["summary"] = {
        "sdkVersion": sdk.get("recommended"),
        "cliVersion": cli.get("recommended"),
        "cliEqualsSdk": bool(sdk.get("recommended")) and sdk.get("recommended") == cli.get("recommended"),
        "usesPrerelease": bool(sdk.get("recommendedIsPrerelease") or cli.get("recommendedIsPrerelease")),
        "minimumSdkVersion": minimum,
    }
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
