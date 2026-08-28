# Diff-link contract

Every detailed finding must link its evidence to the Review Report Tool VS Code handler. Generate standard Markdown links with semantic labels and this canonical URI:

```text
vscode://review-report-tool.review-report-tool/open?v=1&repo=<repo-id>&path=<repo-relative-path>&base=<revision>&head=<revision-or-sentinel>&side=<left-or-right>&start=<line>&end=<line>
```

The canonical parameter order is `v`, `repo`, `path`, `base`, `head`, `side`, `start`, `end`. Emit the literal `v=1` immediately after `/open?`. Encode every other query value as UTF-8 with `encodeURIComponent`-equivalent percent encoding; do not encode the parameter names. Do not put credentials, tokens, remote URLs, or absolute filesystem paths in a URI.

Example:

```markdown
[cache entries are reused across tenants](vscode://review-report-tool.review-report-tool/open?v=1&repo=acme%2Fpayments&path=src%2Fcache.ts&base=0123456789abcdef0123456789abcdef01234567&head=89abcdef0123456789abcdef0123456789abcdef&side=right&start=41&end=48)
```

## Parameters

| Parameter | Requirement |
| --- | --- |
| `v` | Contract version. Reports must emit `1`; omission is reserved for backward compatibility in receivers. |
| `repo` | A normalized primary network-remote path such as `owner/repository`, or `local/<64-hex-history-fingerprint>` when no usable network remote exists. Never use a directory basename. In an unborn local repository, omit `repo`; a receiver may use the sole open repository but must show a chooser when several are open. |
| `path` | POSIX-style path relative to the Git root on the selected side, with no leading slash and no `.` or `..` segment. Encode `/` as `%2F`. For renames, use the path belonging to the selected side. |
| `base` | The immutable diff-base commit SHA whenever available. Use the merge base for branch and PR reviews. The empty-tree SHA is valid for an initial commit. |
| `head` | An immutable commit SHA, or exactly `INDEX` or `WORKTREE` for a local diff. |
| `side` | `right` for head, index, worktree, added, or ordinary changed-line evidence. Use `left` only for deleted or base-only evidence. Receivers may accept `head`/`base` aliases, but reports generate only `right`/`left`. |
| `start` | One-based inclusive line number on the selected side. Must be a positive integer. |
| `end` | One-based inclusive line number on the selected side. Must be greater than or equal to `start`. |

For a rename or copy whose old and new paths differ, append `basePath=<encoded-old-path>&headPath=<encoded-new-path>`. Both are POSIX paths relative to the Git root. `path` remains mandatory and matches the selected side; receivers default omitted `basePath` and `headPath` to `path`.

For a binary or genuinely file-level change without a meaningful text line, set `start=1&end=1` and say `file-level evidence` in the link label. Prefer the narrowest range that establishes the claim; do not link an entire function when two lines suffice.

## Resolution expectations

For a local repository, the fingerprint is SHA-256 over these exact UTF-8 bytes: `review-report-tool:local-history:v1\n`, followed by the lowercase, deduplicated reachable root commit object IDs in lexical order, each terminated by `\n`. This is stable as ordinary descendants are added. Rewriting a root or adding an unrelated reachable root intentionally changes it.

The receiver resolves `repo` against open workspace roots and normalized Git remotes or the same local-history fingerprint, validates that the resolved path remains inside the repository, opens the `base` versus `head` diff, selects the requested side, and highlights the inclusive range when supported or centers it otherwise. An ambiguous or absent repository identity should prompt the user rather than selecting silently. An invalid revision, path traversal, nonexistent line, or repository outside the workspace should fail safely with a visible explanation.

Anchors are evidence pointers, not proof by themselves. The surrounding finding must explain what the selected lines do, the failure mechanism, and the impact.
