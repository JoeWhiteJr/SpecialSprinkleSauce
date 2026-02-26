# Survivorship Bias Audit Plan

> Structured template for the Week 3 formal audit of historical datasets.
> Scope defined. Formal audit execution planned for Week 3.

---

## Scope

### Datasets Under Audit

| Dataset | Source | Date Range | Format | Status |
|---------|--------|-----------|--------|--------|
| Dow Jones Historical | Joe | 1928-2009, daily OHLCV + adjusted close | CSV | Available, loaded to `price_history` |
| Emery S&P 500 | Emery | Last 10 years, all US stocks, OHLCV | CSV | Available, loaded to `price_history` |
| 32GB Minute Data | — | 5 years, all US equities, every minute | CSV | Available on local + hard drive |

### Current Tagging

All data loaded with `survivorship_bias_audited = false` in the `price_history` table.
Models trained on this data are tagged `survivorship_bias_unaudited` in their manifests.

Per PROJECT_STANDARDS_v2.md:
> "All data from 32GB minute dataset and Emery 10-year dataset tagged survivorship_bias_unaudited: true until Week 3 audit sets survivorship_bias_audited: true"

---

## What Is Survivorship Bias

Survivorship bias occurs when historical datasets only include companies that survived to the present day, excluding those that were delisted, went bankrupt, or were acquired. This creates artificially optimistic backtesting results because:

1. Failed companies (often with the worst returns) are excluded
2. Remaining companies are "winners" by definition
3. Strategy performance appears better than it would have been in reality

---

## What to Check

### Dow Jones (1928-2009)
- [ ] Identify all DJIA component changes from 1928-2009
- [ ] Verify that removed/replaced companies are present in the dataset
- [ ] Check for missing tickers that were historically in the index
- [ ] Verify corporate action handling (splits, mergers, name changes)
- [ ] Cross-reference against known DJIA composition history

### Emery S&P 500 (10yr)
- [ ] Identify all S&P 500 additions/removals in the covered period
- [ ] Check if delisted companies appear in the dataset with data up to their delisting date
- [ ] Verify that ticker changes (e.g., FB → META) are handled
- [ ] Check for gaps in data that may indicate removals
- [ ] Cross-reference against S&P 500 historical constituent lists

### 32GB Minute Data (5yr)
- [ ] Determine which exchanges/markets are covered
- [ ] Check if OTC/delisted stocks are included
- [ ] Verify SPACs that de-SPACed or dissolved are present
- [ ] Spot-check known bankruptcies (e.g., SVB, Bed Bath & Beyond) for presence

---

## Known Risks

| Risk | Dataset | Impact | Mitigation |
|------|---------|--------|------------|
| Missing delisted companies | All | Backtests overstate returns | Flag models as unaudited until verified |
| Incomplete corporate actions | Dow Jones | Incorrect adjusted prices | Cross-reference with CRSP or similar |
| Selection bias in Emery data | Emery | Only "interesting" stocks included | Verify against S&P 500 constituent lists |
| Ticker reuse | All | Old ticker assigned to new company | Verify with date-bounded lookups |

---

## Audit Process (Week 3)

1. **Download reference data:** S&P 500 historical constituents, DJIA historical components
2. **Run comparison scripts:** Match dataset tickers against reference lists
3. **Document gaps:** Create a list of missing tickers with date ranges
4. **Assess impact:** Estimate the effect of survivorship bias on model training
5. **Decision:** Accept dataset with documented limitations OR source additional data
6. **Update flag:** Set `survivorship_bias_audited = true` for verified rows

---

## Timeline

| Task | Target | Owner |
|------|--------|-------|
| Define audit scope | Week 2 (this document) | Joe |
| Source reference constituent lists | Week 3 Day 1 | Joe |
| Run automated checks | Week 3 Day 2-3 | System |
| Manual review of gaps | Week 3 Day 4 | Joe + Jared |
| Sign-off and flag update | Week 3 Day 5 | Both |

---

## References

- PROJECT_STANDARDS_v2.md Section 1: Trading Data Standards
- PROJECT_STANDARDS_v2.md Section 9: Testing Standards (stress tests on historical data)
- KNOWLEDGE_BASE_v2.md Section 20: Data Sources
