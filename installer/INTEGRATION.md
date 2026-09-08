# All-branches integration evidence

main is not used as an input branch. Its current commit equals backup-before-merge; that shared history is necessarily included via the requested backup branch. Snapshots pinned on 2026-09-08.

| Branch | Snapshot | Result |
| --- | --- | --- |
| master | 7ab48303efa92b2e52702256dcdd360c9540d273 | Already included (ancestor of HEAD) |
| astra/docly-full-audit-20260906 | 7ab48303efa92b2e52702256dcdd360c9540d273 | Already included (ancestor of HEAD) |
| astra/docly-windows-installer-20260906 | 7ab48303efa92b2e52702256dcdd360c9540d273 | Already included (ancestor of HEAD) |
| backup-before-merge | d4e6da60507efb3f6aed78a1dd8ccd294e453386 | Merged; placeholder README archived in docs/branch-history, product README retained |
| astra/docly-modern-redesign-20260906 | db099db89d57a24a1255a545463cdd65e76c839c | Merged without conflicts |
| fix/docly-desktop-upgrade-safety | 59fe9e57b6bdf50083d5a261a45cb1ad4b6f092d | MERGE FAILED |

Unresolved conflicts (not discarded):
```text
README.md

Auto-merging README.md
CONFLICT (content): Merge conflict in README.md
Auto-merging package.json
Automatic merge failed; fix conflicts and then commit the result.


```
