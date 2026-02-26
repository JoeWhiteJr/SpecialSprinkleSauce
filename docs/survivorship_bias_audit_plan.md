# Survivorship Bias Audit Plan

> Version 1.0 | Week 3 Planning Document
> Audit execution: Week 3 (after screening pipeline is operational)

## Background

All data from the 32GB minute dataset and Emery 10-year S&P 500 dataset is currently tagged `survivorship_bias_audited: false` per PROJECT_STANDARDS_v2.md Section 1. This audit will verify data integrity and update the flag.

## Audit Scope

### Dataset 1: Dow Jones Historical (1928-2009)
- **Source:** Dow Jones daily OHLCV + adjusted close CSV
- **Risk:** Low — index composition changes are well-documented for Dow 30
- **Checks:**
  1. Verify all known Dow delistings are present (companies removed from index)
  2. Cross-reference against published Dow Jones composition changes
  3. Check for suspicious gaps (missing trading days)
  4. Verify adjusted close accounts for splits and dividends

### Dataset 2: Emery S&P 500 (Last 10 Years)
- **Source:** Emery OHLCV CSV, all US stocks
- **Risk:** Medium — S&P 500 has ~20-30 constituent changes per year
- **Checks:**
  1. Count total unique tickers vs expected (~700-800 over 10 years including removals)
  2. Verify presence of known delistings (e.g., companies acquired, bankrupted)
  3. Check for "zombie tickers" (data stops abruptly without delisting record)
  4. Cross-reference against S&P 500 historical constituent lists
  5. Verify delisted tickers have `delisted_date` and `delisted_reason` populated

### Dataset 3: Bloomberg Fundamentals (Daily Snapshots)
- **Source:** JMWFM_Bloomberg_YYYY-MM-DD.xlsx uploads
- **Risk:** Low for fundamentals (point-in-time), but ADR handling needs verification
- **Checks:**
  1. Verify ADR tickers flagged with `is_adr: true`
  2. Check that PE ratio fallback (BEST_PE_RATIO for ADRs) is working
  3. Verify no look-ahead bias in fundamental data dates

## Audit Process

### Phase 1: Automated Checks
1. Run SQL queries to identify gaps, missing dates, abrupt ticker endings
2. Generate report of tickers needing manual review
3. Cross-reference against known delistings list

### Phase 2: Manual Review
1. Review automated check results
2. Spot-check 10 random delistings from each dataset
3. Verify at least 3 known bankruptcy cases are present with full history

### Phase 3: Flag Update
1. For each dataset passing all checks:
   - Set `survivorship_bias_audited = true` for all rows
   - Log audit completion in decision journal
2. For datasets with issues:
   - Document specific failures
   - Keep `survivorship_bias_audited = false`
   - Create remediation plan

## Completion Criteria
- [ ] All automated checks pass or exceptions documented
- [ ] Manual spot-checks completed (minimum 30 tickers)
- [ ] Both partners review and approve audit results
- [ ] `survivorship_bias_audited` flags updated in Supabase
- [ ] Audit summary logged in weekly bias monitoring report

## Timeline
- Day 1: Automated checks and report generation
- Day 2: Manual review and spot-checks
- Day 3: Partner review, flag updates, documentation
