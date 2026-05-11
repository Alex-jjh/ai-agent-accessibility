# SSIM Audit Candidates — Human Review Guide

**Generated**: by `scripts/stage3/ssim-analysis.py`
**Purpose**: Spot-check 20 (operator, URL) pairs to visually confirm SSIM findings.

For each entry: open `data/stage4b-ssim-replay/<slug>/base.png` and `<operator>.png` side by side.

| # | Operator | SSIM | pHash | Slug | Reason |
|---|----------|------|-------|------|--------|
| 1 | L5 | 0.5272 | 28 | `gitlab__thoughtbot-administrate-graphs-main__a9bd6134` | L5 most-changed URL |
| 2 | L5 | 0.5393 | 32 | `gitlab__umano-AndroidSlidingUpPanel-graphs-maste__b7e95421` | L5 most-changed URL |
| 3 | L5 | 0.5402 | 28 | `gitlab__CellularPrivacy-Android-IMSI-Catcher-Det__e09009c2` | L5 most-changed URL |
| 4 | L5 | 0.5402 | 28 | `gitlab__CellularPrivacy-Android-IMSI-Catcher-Det__1e296d88` | L5 most-changed URL |
| 5 | L6 | 0.6854 | 12 | `shopping__root__cceb90cc` | L6 most-changed URL |
| 6 | L6 | 0.6854 | 12 | `shopping__root__15074aac` | L6 most-changed URL |
| 7 | L6 | 0.7617 | 4 | `gitlab__thoughtbot-administrate__c76da737` | L6 most-changed URL |
| 8 | L6 | 0.7651 | 4 | `gitlab__CellularPrivacy-Android-IMSI-Catcher-Det__357a9952` | L6 most-changed URL |
| 9 | L9 | 0.7005 | 22 | `shopping_admin__admin-reports-report-review-product-filt__1cd9503b` | L9 most-changed URL |
| 10 | L9 | 0.7038 | 22 | `shopping_admin__admin-reports-report-review-product__71af165c` | L9 most-changed URL |
| 11 | L9 | 0.7419 | 16 | `gitlab__amwhalen-archive-my-tweets-tree-php52__41b1bd66` | L9 most-changed URL |
| 12 | L9 | 0.7910 | 20 | `gitlab__CellularPrivacy-Android-IMSI-Catcher-Det__0667600c` | L9 most-changed URL |
| 13 | L11 | 0.8000 | 28 | `gitlab__search__331b6653` | L11 most-changed URL |
| 14 | L11 | 0.8335 | 8 | `gitlab__project-245-bot__369dafee` | L11 most-changed URL |
| 15 | L11 | 0.8339 | 14 | `gitlab__Primer__7f8f04eb` | L11 most-changed URL |
| 16 | L11 | 0.8354 | 10 | `gitlab__amwhalen__797eec92` | L11 most-changed URL |
| 17 | L1 | 0.9042 | 2 | `shopping_admin__admin-reports-report-review-product-filt__1cd9503b` | L1 most-changed URL |
| 18 | L1 | 0.9086 | 2 | `shopping_admin__admin-reports-report-review-product__71af165c` | L1 most-changed URL |
| 19 | L1 | 0.9903 | 4 | `shopping_admin__admin-catalog-product-edit-id-23__a0447bf1` | L1 most-changed URL |
| 20 | L1 | 0.9915 | 2 | `shopping_admin__admin-catalog-product-edit-id-18__9e6c8730` | L1 most-changed URL |

## What to look for

- **L5 (Shadow DOM)**: buttons/controls should lose styling
- **L6 (heading→div)**: heading text should shrink to body size
- **L9 (table→div)**: table borders/structure should disappear
- **L11 (link→span)**: links should still appear blue+underlined
- **L1 (landmark→div)**: page should look IDENTICAL (SSIM≈1.0)
- **H-operators**: page should look IDENTICAL (enhancements invisible)
