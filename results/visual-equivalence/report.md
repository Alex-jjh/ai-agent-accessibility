# Visual Equivalence Analysis — mode=aggregate

Generated from 60 pairs.

Thresholds source: `derived_from_baseline`


## Baseline noise distribution (base vs base2, P0-2)

- **SSIM**: n=60, mean=1.0000, std=0.0000, p05=1.0000, p95=1.0000
- **MAD**: n=60, mean=0.0000, std=0.0000, p05=0.0000, p95=0.0000
- **pHash distance**: n=60, mean=0.0, std=0.0, p05=0.0, p95=0.0

### Data-driven thresholds

- Group A (visually identical, μ−2σ of baseline):
  SSIM ≥ 1.0000, MAD < 0.0000, pHash ≤ 0.0, LPIPS ≤ 0.0500
- Group B (visible change, beyond μ−4σ):
  SSIM < 1.0000, MAD > 0.0000, pHash > 0.0, LPIPS > 0.1500

## Base-vs-low vs baseline noise (P0-2 statistical test)

- Mann-Whitney U (H1: base-vs-low SSIM < baseline SSIM):
  U=0.0, p=4.888e-24, n_low=60, n_baseline=60
- Median SSIM: base-vs-low=0.8972, baseline=1.0000
  → SIGNIFICANT: base-vs-low differs from intrinsic rendering noise.

## Per-URL base-vs-low comparison

| slug | App | SSIM | LPIPS | MAD | pHash | pct changed | Group |
|---|---|---|---|---|---|---|---|
| gitlab__a11yproject-a11yproject-com-commits-main__fe8fb481 | gitlab | 0.5555 | N/A | 0.2335 | 30 | 63.65% | B |
| gitlab__a11yproject-a11yproject-com-commits__50959bf8 | gitlab | 0.5555 | N/A | 0.2335 | 30 | 63.65% | B |
| gitlab__a11yproject__02805057 | gitlab | 0.6060 | N/A | 0.2163 | 30 | 64.12% | B |
| gitlab__convexegg-super-awesome-robot__a7c17886 | gitlab | 0.6176 | N/A | 0.2257 | 30 | 63.79% | B |
| gitlab__primer-design-blob-main-eslintignore__f24dcbb7 | gitlab | 0.6145 | N/A | 0.2284 | 28 | 59.99% | B |
| gitlab__primer-design-commits-main__4d9564af | gitlab | 0.5508 | N/A | 0.2347 | 32 | 63.83% | B |
| gitlab__primer-design-commits-main__d1b0bf89 | gitlab | 0.5508 | N/A | 0.2347 | 32 | 63.83% | B |
| gitlab__primer-design-commits__08b271f0 | gitlab | 0.5508 | N/A | 0.2347 | 32 | 63.83% | B |
| gitlab__primer-design-find-file-main__491f1e33 | gitlab | 0.5975 | N/A | 0.2105 | 34 | 47.11% | B |
| gitlab__primer-design-graphs-contributors__8393864d | gitlab | 0.9315 | N/A | 0.0085 | 18 | 2.28% | B |
| gitlab__primer-design-graphs-main-contributors__dda1088d | gitlab | 0.5482 | N/A | 0.2213 | 32 | 55.47% | B |
| gitlab__primer-design-graphs-main__f2f4fff3 | gitlab | 0.5482 | N/A | 0.2213 | 32 | 55.47% | B |
| gitlab__primer-design-merge-requests__21cb9131 | gitlab | 0.5673 | N/A | 0.2426 | 36 | 70.12% | B |
| gitlab__primer-design__793b74e0 | gitlab | 0.6018 | N/A | 0.2247 | 30 | 60.06% | B |
| gitlab__root__99bf4fe3 | gitlab | 0.5926 | N/A | 0.2162 | 32 | 48.17% | B |
| port443__primer-design__c503ed7f | gitlab | 0.5723 | N/A | 0.0819 | 20 | 20.47% | B |
| reddit__f-DIY__22cb7fbf | reddit | 0.6732 | N/A | 0.0976 | 18 | 19.22% | B |
| reddit__f-DIY__a5ea5a0d | reddit | 0.6732 | N/A | 0.0976 | 18 | 19.22% | B |
| reddit__f-books__54c48968 | reddit | 0.6286 | N/A | 0.1124 | 20 | 21.45% | B |
| reddit__forums__afa827bc | reddit | 0.7498 | N/A | 0.0668 | 12 | 17.92% | B |
| reddit__search__62fee688 | reddit | 0.8857 | N/A | 0.0420 | 16 | 7.14% | B |
| reddit__search__7978a3cf | reddit | 0.8910 | N/A | 0.0406 | 18 | 6.91% | B |
| reddit__search__92f83713 | reddit | 0.8809 | N/A | 0.0431 | 14 | 7.33% | B |
| reddit__search__943f3825 | reddit | 0.8765 | N/A | 0.0445 | 12 | 7.55% | B |
| reddit__u-jaaassshhh-comments__8ed95214 | reddit | 0.9900 | N/A | 0.0022 | 12 | 0.44% | B |
| reddit__u-jaaassshhh__f9d915cf | reddit | 0.6730 | N/A | 0.0854 | 16 | 17.57% | B |
| reddit__user-Sorkill-comments__c1ba13fd | reddit | 0.6706 | N/A | 0.0778 | 18 | 16.56% | B |
| reddit__user-ziostraccette-comments__ef2319e5 | reddit | 0.6574 | N/A | 0.0822 | 14 | 17.64% | B |
| shopping__3-pack-samsung-galaxy-s6-screen-protecto__3691f643 | ecommerce | 0.7197 | N/A | 0.0593 | 12 | 13.51% | B |
| shopping__epson-workforce-wf-3620-wifi-direct-all-__895fc32b | ecommerce | 0.7295 | N/A | 0.0572 | 14 | 14.76% | B |
| shopping__haflinger-men-s-wool-felt-open-back-slip__3be3cee5 | ecommerce | 0.7916 | N/A | 0.0485 | 16 | 11.05% | B |
| shopping_admin__admin-admin-dashboard__81d2a7c3 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-admin-reports__23af6fa8 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-admin-sales-invoice__be6b6b91 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-admin-sales-order__eb9ed952 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-admin-sales__8bd469a0 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-admin__c8dcaf2f | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-analytics-reports-show__c2c5c2a7 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-report-product-bestsellers__1d893cc1 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-reports-report-sales-bestsellers-f__21df62c6 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-reports-report-sales-bestsellers-f__b1963035 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-sales-invoice-index__10ae7a58 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-sales-invoice-view-invoice-id-0000__ae24f452 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-sales-invoice-view-invoice-id-1__c1ee4fbd | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-sales-invoice__aff677a9 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-sales-order-index-order-id-159__94211299 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-sales-order-index__2e0c5218 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-sales-order-index__c017cceb | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-sales-order__3d711ed8 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report-sort-popularity__04eff38c | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report-sort-popularity__23794300 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report-sort-popularity__255acc33 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report-sort-popularity__360df86d | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report-sort-popularity__36408c7c | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report-sort-popularity__43a72324 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report-sort-popularity__4892733e | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report-sort-popularity__5a3d5e87 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report-sort-popularity__bbab3d8d | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report-sort-popularity__e7cd7eab | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |
| shopping_admin__admin-search-term-report__44d80634 | ecommerce_admin | 0.8972 | N/A | 0.0413 | 20 | 7.57% | B |

## Summary

- Mean SSIM (base vs low, n=60): 0.7845 ± 0.1448
- Median SSIM: 0.8972 (p05=0.5508, p95=0.8972)
- Group A: 0 / 60
- Group B: 60 / 60
- Group C: 0 / 60
- Group ambiguous: 0 / 60
- Group error: 0 / 60