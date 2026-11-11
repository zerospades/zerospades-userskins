#!/usr/bin/env python3
"""Check a pull request's skin changes and warn. Never fails the job.

Every finding is a warning, so a maintainer can always merge. Findings are printed as
GitHub workflow warnings and collected into the job summary.

Who owns a skin is not written down anywhere: it is whoever created the folder, which git
already records. The owner is read from the earliest commit that touched the folder, so
deleting and re-adding a skin in a pull request does not reassign it.

Usage: check-skins.py <pr-author> [base-ref]
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESERVED, USER = "reserved-skins", "user-skins"

PARTS = {
    "Arm.kv6", "ArmRight.kv6", "Arms.kv6", "Dead.kv6", "Head.kv6",
    "Leg.kv6", "LegCrouch.kv6", "LegRight.kv6", "LegRightCrouch.kv6",
    "Torso.kv6", "TorsoCrouch.kv6", "UpperArm.kv6", "UpperArmRight.kv6",
}
VARIANTS = {"Rifle", "SMG", "Shotgun"}
SHARED = {"Headlamp.kv6", "XmasHat.kv6"}  # never shipped by a skin
EXTRA = {"meta.json", "Player.2kv6", "Readme.md"}

# GitHub's own commit addresses, which carry the login: 1234+login@... or login@...
NOREPLY = re.compile(r"^(?:\d+\+)?([A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)"
                     r"@users\.noreply\.github\.com$", re.I)

warnings = []


def warn(message, path=None):
    warnings.append((path, message))
    where = f" file={path}::" if path else "::"
    print(f"::warning{where}{message}")


def fold(name):
    """How the client keys a name: trimmed and lowercased."""
    return name.strip().lower()


def git(*args):
    out = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    )
    return out.stdout.splitlines() if out.returncode == 0 else []


def skin_dirs(folder):
    root = REPO / folder
    return sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []


_login_cache = {}


def login_of(sha):
    """Ask GitHub which account authored a commit. None when offline or unknown."""
    if sha in _login_cache:
        return _login_cache[sha]
    _login_cache[sha] = None
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if not repo:
        return None
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/commits/{sha}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "check-skins"},
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.load(response)
        _login_cache[sha] = ((body.get("author") or {}).get("login") or "").lower() or None
    except Exception as exc:  # offline, rate-limited, unknown commit
        print(f"::debug::could not resolve the author of {sha}: {exc}")
    return _login_cache[sha]


def creator(folder, name):
    """The GitHub login that created this skin, from the earliest commit touching it.

    The commits API knows the account behind a commit whatever address it was made with;
    a GitHub noreply address, then the author's name, stand in when it cannot be asked.
    """
    log = git("log", "--reverse", "--format=%H%x09%ae%x09%an", "--", f"{folder}/{name}")
    if not log:
        return None
    sha, email, author = (log[0].split("\t") + ["", ""])[:3]
    known = login_of(sha)
    if known:
        return known
    match = NOREPLY.match(email.strip())
    return (match.group(1) if match else author).strip().lower() or None


def created_by():
    """login -> [skin names] across user-skins, from git history."""
    result = {}
    for skin in skin_dirs(USER):
        who = creator(USER, skin.name)
        if who:
            result.setdefault(who, []).append(skin.name)
    return result


def check_meta(skin):
    """meta.json is optional and holds credits only. It must at least parse."""
    path = skin / "meta.json"
    if not path.is_file():
        return
    try:
        json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        warn(f"{skin.name}: meta.json is not valid JSON ({exc})",
             str(path.relative_to(REPO)))


def check_contents(skin):
    """Only known part names, and nothing a skin must not ship."""
    for path in sorted(skin.rglob("*")):
        if path.is_dir():
            if path.parent == skin and path.name not in VARIANTS:
                warn(f"{skin.name}: unexpected folder {path.name!r} "
                     f"(expected one of {', '.join(sorted(VARIANTS))})")
            continue
        rel = path.relative_to(skin)
        if path.name in SHARED:
            warn(f"{skin.name}: {rel} is shared by every skin and must not be "
                 f"shipped in one", str(path.relative_to(REPO)))
        elif path.name not in PARTS and path.name not in EXTRA:
            warn(f"{skin.name}: {rel} is not a known part name",
                 str(path.relative_to(REPO)))


def check_collisions():
    seen = {}
    for folder in (RESERVED, USER):
        for skin in skin_dirs(folder):
            key = fold(skin.name)
            if key in seen:
                warn(f"{folder}/{skin.name} collides with {seen[key]}: the client "
                     f"folds names, so both resolve to {key!r}")
            else:
                seen[key] = f"{folder}/{skin.name}"

    # A name ending in digits is also what a server's name numbering produces for the
    # name without them, so the two are easy to confuse.
    for key, where in sorted(seen.items()):
        stripped = re.sub(r"\d+$", "", key)
        if stripped != key and stripped in seen:
            warn(f"{where} ends in digits, and a server numbering a second "
                 f"{seen[stripped]} would produce the same name")


def main():
    author = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    base = sys.argv[2] if len(sys.argv) > 2 else "origin/main"

    changed = [l for l in git("diff", "--name-only", f"{base}...HEAD") if l]
    renamed = git("diff", "--diff-filter=R", "--name-status", f"{base}...HEAD")
    deleted = [l for l in git("diff", "--diff-filter=D", "--name-only", f"{base}...HEAD") if l]

    touched = {}  # (folder, skin) -> [files]
    for path in changed:
        bits = path.split("/")
        if len(bits) >= 2 and bits[0] in (RESERVED, USER):
            touched.setdefault((bits[0], bits[1]), []).append(path)

    held = created_by()

    for folder, name in sorted(touched):
        if folder == RESERVED:
            warn(f"{folder}/{name} is a reserved skin: servers depend on its name and "
                 f"look, so it needs a maintainer's review")
            continue
        if not author:
            continue
        owner = creator(folder, name)
        if owner and owner != author:
            warn(f"{folder}/{name} was created by {owner!r}, so {author!r} should not "
                 f"be editing it")

    mine = sorted(name for folder, name in touched if folder == USER)
    if len(mine) > 1:
        warn(f"this pull request changes {len(mine)} user skins ({', '.join(mine)}): "
             f"a GitHub user may create and edit only one")
    if author and len(held.get(author, [])) > 1:
        warn(f"{author!r} now has {', '.join(sorted(held[author]))}: a GitHub user may "
             f"create and edit only one skin")

    for line in renamed:
        warn(f"a skin folder was renamed ({line.split(chr(9))[-1]}): the folder name is the "
             f"lookup key, so renaming takes the skin away from the player wearing it")
    for path in deleted:
        if path.split("/")[0] == RESERVED:
            warn(f"{path} was deleted from a reserved skin, which servers depend on")

    for folder, name in sorted(touched):
        skin = REPO / folder / name
        if skin.is_dir():
            check_meta(skin)
            check_contents(skin)
    check_collisions()

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            if warnings:
                fh.write(f"### {len(warnings)} skin warning(s)\n\n")
                for path, message in warnings:
                    fh.write(f"- {message}" + (f" (`{path}`)\n" if path else "\n"))
                fh.write("\nNone of these block the merge.\n")
            else:
                fh.write("### Skins look fine\n")

    print(f"\n{len(warnings)} warning(s). Not failing the job.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
