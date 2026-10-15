#!/usr/bin/env python3
"""Fetch the current Macro Deck Store policy documents and print what matters.

Usage: fetch-policies.py [output-dir]

Writes creator-guidelines.md, blocked-packages.json and sdk-policy.json into output-dir
(default: a new temporary directory, printed) and prints the guidelines version header plus a
summary. Pass a directory outside the repository; never commit the output. Exit code 1 means a document could not be fetched: stop and
report that instead of relying on memory.
"""
import json
import pathlib
import sys
import tempfile
import urllib.request

BASE = "https://api.macro-deck.app/api/v1/public"
DOCS = {
    "creator-guidelines.md": f"{BASE}/creator-guidelines",
    "blocked-packages.json": f"{BASE}/dependency-policy/blocked-packages",
    "sdk-policy.json": f"{BASE}/dependency-policy/sdk",
}


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "macro-deck-plugin-creator"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8"), dict(response.headers)


def main():
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(tempfile.mkdtemp(prefix="macrodeck-policies-"))
    out.mkdir(parents=True, exist_ok=True)
    print(f"output directory: {out}")
    failed = False
    for name, url in DOCS.items():
        try:
            body, headers = fetch(url)
        except Exception as error:  # noqa: BLE001
            print(f"FAILED {url}: {error}")
            failed = True
            continue
        (out / name).write_text(body, encoding="utf-8")
        version = headers.get("X-Creator-Guidelines-Version") or headers.get("x-creator-guidelines-version")
        extra = f" (guidelines version {version})" if version else ""
        print(f"ok {name}{extra}, {len(body)} bytes")

    if (out / "blocked-packages.json").exists():
        blocked = json.loads((out / "blocked-packages.json").read_text(encoding="utf-8")).get("blockedPackages", [])
        print(f"blocked packages: {len(blocked)}")
        for entry in blocked:
            print(f"  {entry.get('packagePattern')} versions={entry.get('versionPattern')} reason={entry.get('reason')}")
    if (out / "sdk-policy.json").exists():
        policy = json.loads((out / "sdk-policy.json").read_text(encoding="utf-8"))
        print(f"minimumSdkVersion: {policy.get('minimumSdkVersion')}")
        print("allowedMacroDeckPackages: " + ", ".join(policy.get("allowedMacroDeckPackages", [])))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
