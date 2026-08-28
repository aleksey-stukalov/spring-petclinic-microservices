#!/usr/bin/env python3
"""Collect read-only Git context for a Review Report Tool review.

The script never contacts a remote and never writes to the repository. It emits
JSON to stdout so different agents can use the same base/head and metadata rules.
"""

from __future__ import print_function

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


SCHEMA_VERSION = 1
COLLECTOR_VERSION = "0.1.0"
SENTINELS = {"INDEX", "WORKTREE"}
REVIEW_PATHSPEC = (".", ":(exclude).review", ":(exclude).review/**")
LOCAL_HISTORY_DOMAIN = "review-report-tool:local-history:v1\n"


class GitError(RuntimeError):
    """A Git command failed or returned unusable data."""


def utc_now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git(repo, *args, **kwargs):
    """Run a local, non-interactive Git command and return stdout."""
    check = kwargs.pop("check", True)
    input_text = kwargs.pop("input_text", None)
    if kwargs:
        raise TypeError("unexpected git() keyword argument")

    # Git needs only process/runtime locations for offline inspection. Do not
    # forward unrelated credentials, loader hooks, Git indirection, or agent
    # authentication into the child process.
    runtime_names = (
        "PATH",
        "HOME",
        "USERPROFILE",
        "TMPDIR",
        "TMP",
        "TEMP",
        "SystemRoot",
        "WINDIR",
        "ComSpec",
        "PATHEXT",
    )
    environment = {}
    inherited_by_casefold = {name.upper(): value for name, value in os.environ.items()}
    for name in runtime_names:
        if name.upper() in inherited_by_casefold:
            environment[name] = inherited_by_casefold[name.upper()]
    environment.update(
        {
            "LANG": "C",
            "LC_ALL": "C",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": "3",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_KEY_0": "core.fsmonitor",
            "GIT_CONFIG_VALUE_0": "false",
            "GIT_CONFIG_KEY_1": "core.hooksPath",
            "GIT_CONFIG_VALUE_1": os.devnull,
            "GIT_CONFIG_KEY_2": "core.excludesFile",
            "GIT_CONFIG_VALUE_2": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    command = ["git", "-C", str(repo)] + list(args)
    try:
        completed = subprocess.run(
            command,
            input=input_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("Git is not installed or is not on PATH") from exc

    if check and completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "unknown Git error"
        raise GitError("git {} failed: {}".format(" ".join(args), message))
    if not check:
        return completed.returncode, completed.stdout, completed.stderr
    return completed.stdout


def resolve_root(candidate):
    supplied = Path(candidate).expanduser().resolve()
    code, stdout, stderr = git(supplied, "rev-parse", "--show-toplevel", check=False)
    if code != 0:
        raise GitError(stderr.strip() or "not inside a Git worktree: {}".format(supplied))
    root = stdout.strip()
    if not root:
        raise GitError("Git returned an empty repository root")
    return Path(root).resolve()


def resolve_commit(repo, revision, required=True):
    code, stdout, _ = git(repo, "rev-parse", "--verify", "{}^{{commit}}".format(revision), check=False)
    if code == 0 and stdout.strip():
        return stdout.strip()
    if required:
        raise GitError("revision is not a commit: {}".format(revision))
    return None


def resolve_tree(repo, revision, required=True):
    code, stdout, _ = git(repo, "rev-parse", "--verify", "{}^{{tree}}".format(revision), check=False)
    if code == 0 and stdout.strip():
        return stdout.strip()
    if required:
        raise GitError("revision is not a tree: {}".format(revision))
    return None


def empty_tree(repo):
    value = git(repo, "hash-object", "-t", "tree", "--stdin", input_text="").strip()
    if not value:
        raise GitError("could not calculate the empty-tree object ID")
    return value


def commit_metadata(repo, revision):
    if not revision:
        return None
    format_string = "%H%x00%h%x00%P%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%s"
    raw = git(repo, "show", "-s", "--format={}".format(format_string), revision).rstrip("\n")
    fields = raw.split("\x00", 9)
    if len(fields) != 10:
        raise GitError("unexpected commit metadata for {}".format(revision))
    return {
        "sha": fields[0],
        "short_sha": fields[1],
        "parents": fields[2].split() if fields[2] else [],
        "author": {"name": fields[3], "email": fields[4]},
        "authored_at": fields[5],
        "committer": {"name": fields[6], "email": fields[7]},
        "committed_at": fields[8],
        "subject": fields[9],
    }


def current_branch(repo):
    code, stdout, _ = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    return stdout.strip() if code == 0 and stdout.strip() else None


def upstream_ref(repo):
    code, stdout, _ = git(
        repo,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
        check=False,
    )
    return stdout.strip() if code == 0 and stdout.strip() else None


def remote_names(repo):
    return sorted(line.strip() for line in git(repo, "remote").splitlines() if line.strip())


def remote_default_refs(repo, remotes):
    refs = []
    ordered = (["origin"] if "origin" in remotes else []) + [name for name in remotes if name != "origin"]
    for remote in ordered:
        code, stdout, _ = git(
            repo,
            "symbolic-ref",
            "--quiet",
            "refs/remotes/{}/HEAD".format(remote),
            check=False,
        )
        if code == 0 and stdout.strip():
            refs.append(stdout.strip())
    return refs


def configured_remote_default_ref(repo, remotes):
    defaults = remote_default_refs(repo, remotes)
    origin_default = [ref for ref in defaults if ref.startswith("refs/remotes/origin/")]
    if len(origin_default) == 1:
        return origin_default[0]
    unique = sorted(set(defaults))
    return unique[0] if len(unique) == 1 else None


def merge_base(repo, left, right):
    code, stdout, _ = git(repo, "merge-base", left, right, check=False)
    if code == 0 and stdout.strip():
        return stdout.splitlines()[0].strip()
    return None


def choose_base(repo, requested, head_selector, head_commit, remotes):
    tree = empty_tree(repo)
    if requested and requested.upper() in ("EMPTY", "EMPTY_TREE"):
        return {
            "selector": "EMPTY_TREE",
            "commit": tree,
            "diff_base": tree,
            "reason": "explicit empty-tree base",
            "is_empty_tree": True,
        }
    if requested and requested.lower() != "auto":
        base_commit = resolve_commit(repo, requested, required=False)
        if not base_commit:
            requested_tree = resolve_tree(repo, requested, required=False)
            if requested_tree == tree:
                return {
                    "selector": "EMPTY_TREE",
                    "commit": tree,
                    "diff_base": tree,
                    "reason": "explicit empty-tree base",
                    "is_empty_tree": True,
                }
            raise GitError("revision is not a commit or the empty tree: {}".format(requested))
        diff_base = merge_base(repo, base_commit, head_commit) if head_commit else base_commit
        return {
            "selector": requested,
            "commit": base_commit,
            "diff_base": diff_base or base_commit,
            "reason": "explicit base",
            "is_empty_tree": False,
        }

    if head_selector in SENTINELS:
        if head_commit:
            return {
                "selector": "HEAD",
                "commit": head_commit,
                "diff_base": head_commit,
                "reason": "local {} review defaults to HEAD".format(head_selector.lower()),
                "is_empty_tree": False,
            }
        return {
            "selector": "EMPTY_TREE",
            "commit": tree,
            "diff_base": tree,
            "reason": "unborn HEAD uses the empty tree",
            "is_empty_tree": True,
        }

    parent = resolve_commit(repo, "{}^".format(head_commit), required=False) if head_commit else None
    if not parent:
        return {
            "selector": "EMPTY_TREE",
            "commit": tree,
            "diff_base": tree,
            "reason": "root commit uses the empty tree",
            "is_empty_tree": True,
        }

    candidate = configured_remote_default_ref(repo, remotes)
    if candidate:
        candidate_commit = resolve_commit(repo, candidate)
        common = merge_base(repo, candidate_commit, head_commit)
        if common:
            return {
                "selector": candidate,
                "commit": candidate_commit,
                "diff_base": common,
                "reason": "configured remote default branch",
                "is_empty_tree": False,
            }
    raise GitError(
        "review base is unresolved; pass --base explicitly or configure a symbolic remote default such as origin/HEAD"
    )


def local_history_repository_id(repo):
    """Hash the sorted reachable root commits into a non-secret local identity."""
    raw = git(repo, "rev-list", "--max-parents=0", "--all")
    roots = sorted({line.strip().lower() for line in raw.splitlines() if line.strip()})
    if not roots:
        return None
    if any(not re.match(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$", root) for root in roots):
        raise GitError("Git returned an invalid root commit object ID")
    canonical = "{}{}\n".format(LOCAL_HISTORY_DOMAIN, "\n".join(roots))
    return "local/{}".format(hashlib.sha256(canonical.encode("utf-8")).hexdigest())


def parse_remote(remote_url):
    """Return a credential-free display URL and optional network repository identifier."""
    raw = (remote_url or "").strip()
    if not raw:
        return None, None

    display = None
    path = None
    if "://" in raw:
        parsed = urlsplit(raw)
        path = unquote(parsed.path or "")
        if parsed.hostname:
            host = parsed.hostname
            if parsed.port:
                host = "{}:{}".format(host, parsed.port)
            display = "{}://{}{}".format(parsed.scheme, host, parsed.path or "")
        else:
            display = "local:{}".format(Path(path).name or "repository")
    else:
        scp_match = re.match(r"^(?:[^@/:]+@)?([^:]+):(.+)$", raw)
        if scp_match and not re.match(r"^[A-Za-z]:[\\/]", raw):
            host, path = scp_match.groups()
            display = "{}:{}".format(host, path)
        else:
            path = raw
            display = "local:{}".format(Path(raw).name or "repository")

    normalized = (path or "").replace("\\", "/").strip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    components = [part for part in normalized.split("/") if part not in ("", ".", "..")]

    parsed_remote = urlsplit(raw) if "://" in raw else None
    is_network_remote = bool(
        parsed_remote
        and parsed_remote.scheme in ("http", "https", "ssh", "git")
        and parsed_remote.hostname
    ) or bool(
        re.match(r"^(?:[^@/:]+@)?[^:]+:.+$", raw) and not re.match(r"^[A-Za-z]:[\\/]", raw)
    )
    repo_id = "/".join(components) if is_network_remote and len(components) >= 2 else None
    return display, repo_id


def primary_remote(repo, remotes):
    if not remotes:
        return {
            "name": None,
            "url": None,
            "repo_id": local_history_repository_id(repo),
            "default_ref": None,
        }
    name = "origin" if "origin" in remotes else remotes[0]
    code, stdout, _ = git(repo, "remote", "get-url", name, check=False)
    remote_url = stdout.strip() if code == 0 else None
    display, repo_id = parse_remote(remote_url)
    if not repo_id:
        repo_id = local_history_repository_id(repo)
    defaults = remote_default_refs(repo, [name])
    return {
        "name": name,
        "url": display,
        "repo_id": repo_id,
        "default_ref": defaults[0] if defaults else None,
    }


def refs_containing(repo, commit):
    if not commit:
        return {"values": [], "truncated": False}
    raw = git(
        repo,
        "for-each-ref",
        "--format=%(refname:short)",
        "--contains={}".format(commit),
        "refs/heads",
        "refs/remotes",
        "refs/tags",
    )
    values = sorted({line.strip() for line in raw.splitlines() if line.strip()})
    return {"values": values[:100], "truncated": len(values) > 100}


def diff_arguments(base, head_selector, mode, output_options):
    common = ["--no-ext-diff", "--no-textconv", "--find-renames", "--find-copies"] + list(output_options)
    if mode == "index":
        return ["diff", "--cached"] + common + [base]
    if mode == "worktree":
        return ["diff"] + common + [base]
    return ["diff"] + common + [base, head_selector]


def parse_name_status(raw):
    tokens = raw.split("\x00")
    if tokens and tokens[-1] == "":
        tokens.pop()
    counts = {}
    rename_count = 0
    copy_count = 0
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            continue
        code = status[0]
        counts[code] = counts.get(code, 0) + 1
        path_count = 2 if code in ("R", "C") else 1
        if code == "R":
            rename_count += 1
        elif code == "C":
            copy_count += 1
        index += path_count
    return counts, rename_count, copy_count


def diff_statistics(repo, base, head_selector, mode):
    name_arguments = diff_arguments(base, head_selector, mode, ("--name-status", "-z"))
    name_status = git(repo, *(name_arguments + ["--"] + list(REVIEW_PATHSPEC)))
    status_counts, renamed, copied = parse_name_status(name_status)

    stat_arguments = diff_arguments(base, head_selector, mode, ("--numstat",))
    numstat = git(repo, *(stat_arguments + ["--"] + list(REVIEW_PATHSPEC)))
    additions = 0
    deletions = 0
    binary = 0
    for line in numstat.splitlines():
        fields = line.split("\t", 2)
        if len(fields) < 3:
            continue
        if fields[0] == "-" or fields[1] == "-":
            binary += 1
            continue
        try:
            additions += int(fields[0])
            deletions += int(fields[1])
        except ValueError:
            continue
    return {
        "tracked_files_changed": sum(status_counts.values()),
        "insertions": additions,
        "deletions": deletions,
        "binary_files": binary,
        "renamed_files": renamed,
        "copied_files": copied,
        "status_counts": dict(sorted(status_counts.items())),
    }


def count_nul_items(raw):
    return len([item for item in raw.split("\x00") if item])


def worktree_state(repo):
    paths = ["--"] + list(REVIEW_PATHSPEC)
    staged = count_nul_items(
        git(repo, *(["diff", "--cached", "--no-ext-diff", "--no-textconv", "--name-only", "-z"] + paths))
    )
    unstaged = count_nul_items(
        git(repo, *(["diff", "--no-ext-diff", "--no-textconv", "--name-only", "-z"] + paths))
    )
    untracked = count_nul_items(
        git(repo, *(["ls-files", "--others", "--exclude-standard", "-z"] + paths))
    )
    conflicted = count_nul_items(
        git(repo, *(["diff", "--no-ext-diff", "--no-textconv", "--name-only", "--diff-filter=U", "-z"] + paths))
    )
    return {
        "clean": staged == 0 and unstaged == 0 and untracked == 0 and conflicted == 0,
        "staged_files": staged,
        "unstaged_files": unstaged,
        "untracked_files": untracked,
        "conflicted_files": conflicted,
    }


def commit_range(repo, base, head, base_is_empty_tree):
    if not head:
        return {"commit_count": 0, "authors": [], "first_commit": None, "last_commit": None}
    range_args = [head] if base_is_empty_tree else ["{}..{}".format(base, head)]
    count = int(git(repo, "rev-list", "--count", *range_args).strip() or "0")
    if count == 0:
        return {"commit_count": 0, "authors": [], "first_commit": None, "last_commit": None}

    record_format = "%H%x1f%an%x1f%ae%x1f%aI%x1e"
    raw = git(repo, "log", "--reverse", "--format={}".format(record_format), *range_args)
    commits = []
    authors = []
    seen_authors = set()
    for record in raw.split("\x1e"):
        cleaned = record.strip("\n")
        if not cleaned:
            continue
        fields = cleaned.split("\x1f")
        if len(fields) != 4:
            continue
        entry = {"sha": fields[0], "author": {"name": fields[1], "email": fields[2]}, "authored_at": fields[3]}
        commits.append(entry)
        identity = (fields[1], fields[2])
        if identity not in seen_authors:
            seen_authors.add(identity)
            authors.append({"name": fields[1], "email": fields[2]})
    return {
        "commit_count": count,
        "authors": authors,
        "first_commit": commits[0] if commits else None,
        "last_commit": commits[-1] if commits else None,
    }


def collect(args):
    repo = resolve_root(args.repo)
    branch = current_branch(repo)
    remotes = remote_names(repo)
    remote = primary_remote(repo, remotes)

    requested_head = args.head
    if requested_head in SENTINELS:
        head_commit = resolve_commit(repo, "HEAD", required=False)
        mode = requested_head.lower()
    else:
        head_commit = resolve_commit(repo, requested_head)
        mode = "branch" if requested_head == "HEAD" and branch else "commit"

    base = choose_base(repo, args.base, requested_head, head_commit, remotes)
    diff = diff_statistics(repo, base["diff_base"], head_commit or requested_head, mode)
    state = worktree_state(repo)
    diff["untracked_files_not_in_diff"] = state["untracked_files"] if mode == "worktree" else 0
    diff["excluded_paths"] = [".review/**"]

    limitations = [
        "Git does not record a reliable branch creator or branch creation timestamp.",
        "Pull/merge-request metadata requires provider context and is not fetched by this offline collector.",
    ]
    if mode == "worktree" and state["untracked_files"]:
        limitations.append(
            "Untracked files are counted but absent from Git diff statistics; inspect them separately before completing the review."
        )

    checked_out_commit = resolve_commit(repo, "HEAD", required=False)
    return {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at": utc_now(),
        "repository": {
            "root": str(repo),
            "name": repo.name,
            "repo_id": remote["repo_id"],
            "primary_remote": {"name": remote["name"], "url": remote["url"]},
            "remote_default_ref": remote["default_ref"],
        },
        "review": {
            "kind": mode,
            "requested_base": args.base,
            "requested_head": requested_head,
            "base_selection_reason": base["reason"],
        },
        "head": {
            "selector": requested_head,
            "snapshot": requested_head if requested_head in SENTINELS else head_commit,
            "branch": branch if head_commit and head_commit == checked_out_commit else None,
            "checked_out_branch": branch,
            "upstream_ref": upstream_ref(repo),
            "commit": commit_metadata(repo, head_commit),
            "related_refs": refs_containing(repo, head_commit),
        },
        "base": {
            "selector": base["selector"],
            "commit": commit_metadata(repo, base["commit"]) if not base["is_empty_tree"] else None,
            "diff_base": base["diff_base"],
            "is_empty_tree": base["is_empty_tree"],
        },
        "range": commit_range(repo, base["diff_base"], head_commit, base["is_empty_tree"]),
        "diff": diff,
        "worktree": state,
        "limitations": limitations,
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Collect read-only Git metadata for a structured code review.")
    parser.add_argument("--repo", default=".", help="A path inside the Git worktree (default: current directory).")
    parser.add_argument(
        "--base",
        default="auto",
        help="Base commit-ish, or 'auto' to use a configured remote-default ref (local reviews use HEAD).",
    )
    parser.add_argument(
        "--head",
        default="HEAD",
        help="Head commit-ish, INDEX, or WORKTREE (default: HEAD).",
    )
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON instead of indented JSON.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        result = collect(args)
    except (GitError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc), "schema_version": SCHEMA_VERSION}), file=sys.stderr)
        return 2
    if args.compact:
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    else:
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
