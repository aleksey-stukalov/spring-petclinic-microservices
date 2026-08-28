# Report template

Write reports in this structure and order. Replace angle-bracket fields with verified values. Use `Unavailable — <reason>` rather than guessing. Remove parenthetical guidance from the finished report, but retain every heading and table column shown here.

````markdown
# Review report — `<head-label>`

## Head

| Field | Value |
| --- | --- |
| Head | `<full SHA, INDEX, or WORKTREE>` |
| Head branch/ref | `<source branch/ref or detached>` |
| Head commit | `<full SHA>` — `<subject>` |
| Head author / authored | `<name>` · `<ISO-8601 timestamp>` |
| Head committer / committed | `<name>` · `<ISO-8601 timestamp>` |
| Related refs | `<concise local/remote refs containing head>` |
| Pull/merge request | `<provider and number, linked when known; title; otherwise unavailable>` |
| Review state | `<open/draft/merged/closed, mergeability, and concise labels; otherwise unavailable>` |
| Change author / created | `<PR/MR author and creation time; otherwise head commit author/time, explicitly labeled as fallback>` |
| Branch creator / created | `Unavailable — Git does not record branch creation metadata` (unless authoritative provider evidence exists) |

## Comparison and provenance

| Field | Value |
| --- | --- |
| Repository | `<normalized network-remote identity, local/<history-fingerprint>, or unavailable for an unborn local repository; credential-free remote URL when useful>` |
| Review kind | `<pull request, branch, commit range, index, or worktree>` |
| Base branch/ref | `<target ref or unavailable>` |
| Base commit | `<full SHA>` |
| Diff base | `<merge-base or base SHA actually reviewed>` |
| Reviewed range | `<diff-base>...<head SHA, INDEX, or WORKTREE>` |
| Generated | `<UTC ISO-8601 timestamp>` |
| Reviewer | `<agent/model when known, otherwise automated review>` |
| Tool / skill | `<Review Report Tool version or unavailable>` · `review-report skill 0.1.0` |
| Policy provenance | `installed SKILL.md (built-in, precedence 0) · sha256:<64 hex>; built-in rubric (built-in, precedence 0) · sha256:<64 hex>; <one semicolon-separated entry with source, precedence, and full SHA-256 for every loaded review-requirements.md>` |
| Worktree state | `<clean, or concise staged/unstaged/untracked counts>` |
| Commits and authors | `<reviewed commit count, author names, earliest and latest reviewed commit timestamps>` |
| Diff statistics | `<files changed, insertions, deletions, binary files>` |

## Executive summary

**Verdict:** `<Ready | Ready with follow-ups | Ready with concerns | Changes requested | Blocked — review incomplete>`

**Change:** <One or two sentences describing intent and approach, not a file list.>

**Risk and blast radius:** <Affected callers/users/services/data/platforms, failure containment, reversibility, and overall risk.>

**Review coverage:** <What was inspected, relevant dimensions, validation run, and material exclusions or assumptions.>

## Dimension coverage

| Dimension | Coverage | Evidence or limitation |
| --- | :---: | --- |
| Architecture cleanliness | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| Correctness and data integrity | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| Implementation quality | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| Security and privacy | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| Performance and resource use | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| Concurrency and state | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| Reliability and observability | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| Maintainability and testability | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| API, data, and schema compatibility | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| Dependencies, supply chain, and licenses | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| UX, accessibility, and internationalization | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| Operations and deployment | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |
| Risk and blast radius | `<Full | Partial | Not assessed>` | <Concise scope or reason.> |

## Findings

| Finding | Severity | Short explanation | Proposal |
| --- | :---: | --- | --- |
| [RR-001 — <short title>](#rr-001) | 🔴 Red | <one concrete sentence> | <one concrete sentence> |
| [RR-002 — <short title>](#rr-002) | 🟡 Yellow | <one concrete sentence> | <one concrete sentence> |

(If none, the only row is:)

| No actionable findings | 🟢 Green | The reviewed change has no evidence-backed issues above the configured threshold. | Proceed with the stated validation and rollout plan. |

## Detailed findings

<a id="rr-001"></a>

### RR-001 — <short title>

- **Severity:** 🔴 Red
- **Dimension:** <primary dimension; add a secondary dimension only when useful>
- **Confidence:** <High or Medium>
- **Evidence:** [<semantic description of selected changed lines>](vscode://review-report-tool.review-report-tool/open?v=1&repo=<encoded-repo-id>&path=<encoded-path>&base=<encoded-base>&head=<encoded-head>&side=right&start=<n>&end=<n>)
- **Observed:** <What the code does and the concrete failure mechanism.>
- **Impact and blast radius:** <Who or what is affected, scope, containment, detection, recovery, and reversibility.>
- **Proposal:** <Smallest robust fix or decision.>
- **Verification:** <Focused test, command, measurement, or inspection that proves the proposal.>

(Repeat in descending severity, then by execution/data-flow order. If there are no findings, write `No detailed findings.` under this heading.)

## Validation

| Check | Result |
| --- | --- |
| `<command or inspection>` | `<Passed, Failed, or Not run>` — <concise evidence or reason> |

## Reviewer comments

<!-- review-report-tool:comments:start -->
_Append human review comments below. Content from this marker to end of file belongs to the reviewer and publishing automation, not to the generated findings._

````

## Formatting rules

- Assign identifiers in descending severity and then logical execution/data-flow order. Keep an identifier attached to the same finding within one report.
- Replace the verdict placeholder with exactly one allowed phrase as plain text. Do not retain angle brackets, add emoji, or wrap the value in backticks or other Markdown styling.
- Escape Markdown table pipes and replace embedded newlines with `<br>`.
- Keep summary explanations and proposals to one sentence each. Put nuance in details.
- Separate Policy provenance entries with semicolons (or `<br>`) and put one full `sha256:` digest in every entry; omit policies that were not loaded.
- Use semantic anchor text that states the relevant behavior; never use `here`, a raw path, or a bare line number.
- Link PR/MR URLs normally. Link code evidence only with the diff-link contract.
- Do not add per-file sections, scores, a changed-file appendix, or empty dimension headings.
- `Full` means the relevant changed paths and supporting context were inspected; `Partial` names a concrete limit; `Not assessed` states why the dimension is inapplicable or unavailable. Never use coverage as a quality score.
- The comments marker occurs exactly once and the reviewer-comments section is always last.
