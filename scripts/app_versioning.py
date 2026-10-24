"""Prepare commit-time application versions; never commit, push, or publish."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import NamedTuple

SOURCE: str = "src/gameoflife/__init__.py"
ASSIGNMENT: re.Pattern[str] = re.compile(
    r"(?m)^__version__(?:[ \t]*:[ \t]*str)?[ \t]*=[ \t]*(?P<quote>[\"\'])"
    r"(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))"
    r"(?P=quote)(?=[ \t]*(?:#.*)?$)"
)
HOOK_MARKER: str = "# conways-app-versioning-v1"


class VersionError(RuntimeError):
    """A recoverable version-workflow error."""


class Version(NamedTuple):
    """A strictly numeric semantic application version."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        """Render the shared version in package-compatible form."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def next_version(self, feature: bool) -> Version:
        """Allocate one feature minor or one fix patch."""
        return (
            Version(self.major, self.minor + 1, 0)
            if feature
            else Version(self.major, self.minor, self.patch + 1)
        )


def git(
    *arguments: str, data: str | None = None, check: bool = True, raw: bool = False
) -> str:
    """Run Git against the caller's repository and active index."""
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", *arguments], input=data, capture_output=True, text=True, check=False
    )
    if check and result.returncode:
        raise VersionError(
            f"Git {' '.join(arguments[:2])} failed: {result.stderr.strip()}"
        )
    return result.stdout if raw else result.stdout.rstrip("\n")


def root() -> Path:
    """Locate this worktree without assuming .git is a directory."""
    return Path(git("rev-parse", "--show-toplevel"))


def config(key: str, default: str = "") -> str:
    """Read a clone-local policy setting without exposing remote URLs."""
    return git("config", "--get", key, check=False) or default


def branch() -> str:
    """Require a named branch for normal version allocation."""
    name: str = git("symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if not name:
        raise VersionError(
            "Detached HEAD: switch to a branch before creating a new batch."
        )
    return name


def read_version(content: str) -> Version:
    """Parse exactly one authoritative assignment, including legacy untyped form."""
    matches: list[re.Match[str]] = list(ASSIGNMENT.finditer(content))
    if len(matches) != 1:
        raise VersionError(
            f"Expected exactly one numeric __version__ assignment in {SOURCE}."
        )
    return Version(*(int(part) for part in matches[0]["version"].split(".")))


def replace_version(content: str, version: Version) -> str:
    """Replace only the numeric field, retaining annotation, comments, and spacing."""
    read_version(content)
    match: re.Match[str] | None = ASSIGNMENT.search(content)
    assert match is not None
    return (
        content[: match.start("version")]
        + str(version)
        + content[match.end("version") :]
    )


def source_at(revision: str) -> str:
    """Read a version source from a tree or the active Git index."""
    return git("show", f"{revision}:{SOURCE}", raw=True)


def revision_exists(revision: str) -> bool:
    """Report whether a commit is present locally."""
    return bool(git("rev-parse", "--verify", f"{revision}^{{commit}}", check=False))


def ancestor(older: str, newer: str) -> bool:
    """Check ancestry rather than using version equality as publication evidence."""
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise VersionError(
            "Cannot establish publication ancestry; fetch and reconcile history."
        )
    return result.returncode == 0


def replaying() -> bool:
    """Recognize Git-managed rebase replay and preserve its existing allocations."""
    return any(
        Path(git("rev-parse", "--git-path", name)).exists()
        for name in ("rebase-merge", "rebase-apply")
    )


def trailer(name: str, revision: str = "HEAD") -> str:
    """Read the most recent commit's durable workflow metadata."""
    message: str = git("log", "-1", "--format=%B", revision, check=False)
    matches: list[str] = re.findall(rf"(?m)^{re.escape(name)}: (\S+)$", message)
    return matches[-1] if matches else ""


def remote_commit(name: str) -> str:
    """Query the actual designated branch; never trust stale tracking refs."""
    remote: str = config("appVersion.remote")
    if not remote:
        raise VersionError(
            "Run scripts/app_versioning.py install to configure publication."
        )
    upstream_remote: str = config(f"branch.{name}.remote")
    target: str = config(f"branch.{name}.merge", f"refs/heads/{name}")
    if upstream_remote and upstream_remote != remote:
        raise VersionError(
            "Branch upstream uses another remote; correct its upstream first."
        )
    if not target.startswith("refs/heads/") or "\n" in target:
        raise VersionError("Branch upstream must designate exactly one remote branch.")
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", remote, target],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 2:
        return ""
    if result.returncode:
        raise VersionError(
            "Cannot verify the published branch. Restore remote access and retry."
        )
    rows: list[list[str]] = [line.split() for line in result.stdout.splitlines()]
    if len(rows) != 1 or len(rows[0]) != 2 or rows[0][1] != target:
        raise VersionError(
            "Unexpected publication ref mapping; correct the branch upstream."
        )
    commit: str = rows[0][0]
    if not revision_exists(commit):
        raise VersionError(
            "Published history is missing locally; git fetch, then reconcile and retry."
        )
    if not revision_exists("HEAD") or not ancestor(commit, "HEAD"):
        raise VersionError(
            "Published branch is ahead or divergent; merge/rebase it before committing."
        )
    return commit


def feature_identity(name: str) -> str:
    """Recover an existing feature identity across clones, recreations, and renames."""
    if name == config("appVersion.primary"):
        return ""
    kind: str = config(f"branch.{name}.appVersionKind")
    if kind == "fix":
        return ""
    return config(f"branch.{name}.appVersionFeature") or trailer("App-Version-Feature")


def feature_allocated(identity: str) -> bool:
    """Require a successful commit carrying this allocation before using patch batches."""
    return bool(
        identity
        and git(
            "log",
            "-1",
            "--format=%H",
            "--fixed-strings",
            f"--grep=App-Version-Feature: {identity}",
            "HEAD",
            check=False,
        )
    )


def has_payload() -> bool:
    """Ignore version-only retries and empty commits when allocating new versions."""
    names: list[str] = git("diff", "--cached", "--name-only", "HEAD").splitlines()
    if any(name != SOURCE for name in names):
        return True
    if SOURCE not in names:
        return False
    return replace_version(source_at(""), Version(0, 0, 0)) != replace_version(
        source_at("HEAD"), Version(0, 0, 0)
    )


def desired_version(name: str, published: str, current: Version) -> Version:
    """Choose a branch-specific batch from verified publication and durable intent."""
    identity: str = feature_identity(name)
    if identity and not feature_allocated(identity):
        return current.next_version(feature=True)
    if published:
        baseline: Version = read_version(source_at(published))
        if current.major != baseline.major and not trailer("App-Version-Major"):
            raise VersionError(
                "Unrecorded major change: make an explicit major-version decision."
            )
        if current < baseline:
            raise VersionError(
                "Local version is below the published version; reconcile history."
            )
        if current > baseline and trailer("App-Version-Batch"):
            return current
    elif trailer("App-Version-Branch") == name or (
        identity and feature_allocated(identity)
    ):
        return current
    return current.next_version(feature=False)


def stage_version(version: Version) -> None:
    """Update only the assignment in the active index and preserve worktree edits."""
    staged: str = source_at("")
    path: Path = root() / SOURCE
    working: str = path.read_text()
    if read_version(working) not in (read_version(staged), version):
        raise VersionError(
            "Version has a separate unstaged edit; stage or restore that field first."
        )
    updated: str = replace_version(staged, version)
    if updated == staged:
        return
    mode: str = git("ls-files", "--stage", "--", SOURCE).split()[0]
    blob: str = git("hash-object", "-w", "--stdin", data=updated)
    git("update-index", "--cacheinfo", f"{mode},{blob},{SOURCE}")
    path.write_text(replace_version(working, version))
    print(f"Application version: {version}")


def prepare(merging: bool = False) -> None:
    """Prepare a nonempty commit or preserve the higher compatible merge version."""
    if replaying() or not revision_exists("HEAD"):
        return
    name: str = branch()
    current: Version = read_version(source_at("HEAD"))
    staged: Version = read_version(source_at(""))
    major_override: bool = os.environ.get("APP_VERSION_ALLOW_MAJOR") == "1"
    merge_path: Path = Path(git("rev-parse", "--git-path", "MERGE_HEAD"))
    if merging or merge_path.exists():
        versions: list[Version] = [current, staged]
        if merge_path.exists():
            versions.extend(
                read_version(source_at(commit))
                for commit in merge_path.read_text().split()
            )
        if len({version.major for version in versions}) != 1 and not (
            major_override and staged == max(versions)
        ):
            raise VersionError(
                "Merge crosses major versions; stage the chosen higher major and commit "
                "with APP_VERSION_ALLOW_MAJOR=1 after explicit authorization."
            )
        stage_version(max(versions))
        return
    if not has_payload() and not (major_override and staged != current):
        if staged != current:
            raise VersionError(
                "Version-only changes require an explicitly authorized major override."
            )
        return
    published: str = remote_commit(name)
    if major_override:
        if staged.major <= current.major or staged <= current:
            raise VersionError(
                "Major override requires a staged increase of the major field."
            )
        return
    if staged.major != current.major:
        raise VersionError(
            "Major edits require explicit authorization and APP_VERSION_ALLOW_MAJOR=1."
        )
    expected: Version = desired_version(name, published, current)
    if staged not in (current, expected):
        raise VersionError(
            f"Unexpected staged version {staged}; expected {current} or {expected}."
        )
    stage_version(expected)


def write_message(path: Path, fields: list[str]) -> None:
    """Replace workflow trailers without duplicating them on retries or amendments."""
    message: str = path.read_text()
    message = re.sub(
        r"(?m)^App-Version-(?:Batch|Branch|Feature|Major): .*\n?", "", message
    )
    path.write_text(message.rstrip() + "\n\n" + "\n".join(fields) + "\n")


def commit_message(arguments: list[str]) -> None:
    """Record allocations in successful commit history, including feature identity."""
    if replaying() or not revision_exists("HEAD"):
        return
    path: Path = Path(arguments[0])
    comment: str = config("core.commentChar", "#")
    meaningful_lines: list[str] = [
        line
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith(comment)
    ]
    if not meaningful_lines:
        return
    if not git("diff", "--cached", "--name-only", "HEAD"):
        previous: str = git("log", "-1", "--format=%B")
        existing: list[str] = re.findall(
            r"(?m)^App-Version-(?:Batch|Branch|Feature|Major): \S+$", previous
        )
        if existing:
            write_message(path, existing)
        return
    name: str = branch()
    identity: str = feature_identity(name)
    fields: list[str] = [
        f"App-Version-Batch: {read_version(source_at(''))}",
        f"App-Version-Branch: {name}",
    ]
    if identity:
        fields.append(f"App-Version-Feature: {identity}")
    if os.environ.get("APP_VERSION_ALLOW_MAJOR") == "1" or trailer("App-Version-Major"):
        fields.append("App-Version-Major: explicit")
    write_message(path, fields)


def classify(kind: str, new_feature: bool) -> None:
    """Declare branch intent without editing or consuming an application version."""
    name: str = branch()
    if name == config("appVersion.primary") and kind == "feature":
        raise VersionError(
            "Create a feature branch before classifying it as a feature."
        )
    existing: str = config(f"branch.{name}.appVersionFeature") or trailer(
        "App-Version-Feature"
    )
    if new_feature and kind != "feature":
        raise VersionError("--new-feature requires feature classification.")
    if new_feature and trailer("App-Version-Branch") == name:
        raise VersionError(
            "Start a new feature on a new branch from the primary branch."
        )
    identity: str = existing if existing and not new_feature else uuid.uuid4().hex
    git("config", f"branch.{name}.appVersionKind", kind)
    if kind == "feature":
        git("config", f"branch.{name}.appVersionFeature", identity)
    print(f"{name}: {kind}. Version will be prepared at the next nonempty commit.")


def merge_versions(base: Path, ours: Path, theirs: Path) -> int:
    """Merge non-version content normally and choose the higher compatible version."""
    contents: list[str] = [path.read_text() for path in (base, ours, theirs)]
    versions: list[Version] = [read_version(content) for content in contents]
    if len({version.major for version in versions}) != 1:
        raise VersionError(
            "Version merge crosses majors; explicitly resolve the version source."
        )
    with tempfile.TemporaryDirectory(prefix="life-version-merge-") as temporary:
        paths: list[Path] = [
            Path(temporary) / name for name in ("base", "ours", "theirs")
        ]
        for path, content in zip(paths, contents):
            path.write_text(replace_version(content, versions[0]))
        result: subprocess.CompletedProcess[str] = subprocess.run(
            [
                "git",
                "merge-file",
                "-p",
                "-L",
                "ours",
                "-L",
                "base",
                "-L",
                "theirs",
                str(paths[1]),
                str(paths[0]),
                str(paths[2]),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    if result.returncode < 0 or result.returncode > 127:
        raise VersionError("Git could not merge version-source content.")
    ours.write_text(replace_version(result.stdout, max(versions)))
    return 1 if result.returncode else 0


def finalize_index() -> None:
    """Reconcile selected-file commits without staging unrelated source-file edits."""
    if not revision_exists("HEAD^") or replaying():
        return
    committed: Version = read_version(source_at("HEAD"))
    previous: Version = read_version(source_at("HEAD^"))
    indexed: Version = read_version(source_at(""))
    if indexed == previous and indexed < committed:
        stage_version(committed)


def install(remote: str, primary: str) -> None:
    """Install owned hooks and a merge driver only after all conflict checks pass."""
    repository: Path = root()
    if remote not in git("remote").splitlines():
        raise VersionError(
            f"Remote {remote!r} is missing; add the intended publication remote first."
        )
    mapping: str = config(f"remote.{remote}.fetch")
    if mapping != f"+refs/heads/*:refs/remotes/{remote}/*":
        raise VersionError(
            "Nonstandard fetch mapping; configure standard branch tracking first."
        )
    for key, value in (("appVersion.remote", remote), ("appVersion.primary", primary)):
        if config(key) and config(key) != value:
            raise VersionError(
                f"Existing {key} differs; reconcile policy before reinstalling."
            )
    hook_directory: Path = Path(git("rev-parse", "--git-path", "hooks"))
    if not hook_directory.is_absolute():
        hook_directory = repository / hook_directory
    hooks: tuple[str, ...] = (
        "pre-commit",
        "pre-merge-commit",
        "commit-msg",
        "post-commit",
    )
    for hook in hooks:
        target: Path = hook_directory / hook
        if target.exists() and HOOK_MARKER not in target.read_text():
            raise VersionError(
                f"Existing hook {target}; integrate it explicitly before installation."
            )
    command: str = f"{shlex.quote(sys.executable)} scripts/app_versioning.py"
    driver: str = command + ' merge-driver "%O" "%A" "%B"'
    existing_driver: str = config("merge.app-version.driver")
    if existing_driver and existing_driver != driver:
        raise VersionError(
            "Existing app-version merge driver differs; reconcile it before reinstalling."
        )
    hook_directory.mkdir(parents=True, exist_ok=True)
    for hook in hooks:
        action: str = {
            "commit-msg": "message",
            "pre-merge-commit": "prepare-merge",
            "post-commit": "finalize-index",
        }.get(hook, "prepare")
        target = hook_directory / hook
        target.write_text(
            f"#!/bin/sh\n{HOOK_MARKER}\n"
            'cd "$(git rev-parse --show-toplevel)" || exit 1\n'
            f'exec {command} {action} "$@"\n'
        )
        target.chmod(0o755)
    git("config", "appVersion.remote", remote)
    git("config", "appVersion.primary", primary)
    git("config", "merge.app-version.name", "Preserve compatible application versions")
    git("config", "merge.app-version.driver", driver)
    print(f"Installed in {hook_directory}; publication: {remote}/{primary}.")


def main() -> int:
    """Dispatch explicit installation, classification, and Git hook operations."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__)
    commands: argparse._SubParsersAction[argparse.ArgumentParser] = (
        parser.add_subparsers(dest="command", required=True)
    )
    setup: argparse.ArgumentParser = commands.add_parser("install")
    setup.add_argument("--remote", default="origin")
    setup.add_argument("--primary", default="master")
    classification: argparse.ArgumentParser = commands.add_parser("classify")
    classification.add_argument("kind", choices=("feature", "fix"))
    classification.add_argument("--new-feature", action="store_true")
    commands.add_parser("prepare")
    commands.add_parser("prepare-merge")
    commands.add_parser("finalize-index")
    message: argparse.ArgumentParser = commands.add_parser("message")
    message.add_argument("arguments", nargs="+")
    driver: argparse.ArgumentParser = commands.add_parser("merge-driver")
    driver.add_argument("paths", nargs=3, type=Path)
    args: argparse.Namespace = parser.parse_args()
    try:
        if args.command == "install":
            install(args.remote, args.primary)
        elif args.command == "classify":
            classify(args.kind, args.new_feature)
        elif args.command in ("prepare", "prepare-merge"):
            prepare(merging=args.command == "prepare-merge")
        elif args.command == "message":
            commit_message(args.arguments)
        elif args.command == "finalize-index":
            finalize_index()
        else:
            return merge_versions(*args.paths)
    except (VersionError, OSError) as error:
        print(f"App versioning: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
