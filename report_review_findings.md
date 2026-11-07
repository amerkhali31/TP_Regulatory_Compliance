# TP-1-IL Report Review: Findings & How the Automation Works

What I learned while investigating the pipeline and building `report_review.py` (November 2026).
The investigation re-ran the pipeline on every month in `Customers/dream/` (output written to a temp
folder; nothing in `Customers/` was modified) and compared the output to the hand-edited final reports.

---

## 1. How the pipeline works

```
python -m pipeline [-md N]
  ├─ get_month_year(N)            -> e.g. "SEPTEMBER_2026"
  ├─ create_folder()              -> Customers/dream/<MONTH>/{Current_Data,Reports}
  ├─ move_files(~/Downloads -> Current_Data)   CUSTOMERS, INVOICES, PRODUCTS, TAX, PURCHASING
  ├─ reader.do_taxes()            -> builds the TP-1-IL report + diagnostic workbooks
  └─ report_review.review_report()  -> checks, auto-fixes, explains, summarizes (new)
```

### `reader.do_taxes` step by step
1. Reads the QuickBooks exports (`Sheet1` of each workbook; `Unnamed:` spacer columns dropped).
2. **Invoices:** strips `(...)` from `Item`, renames `Name` to `Customer`, drops rows with no `Num`
   (customer header/subtotal rows).
3. **Products:** `Sales Tax Code` is renamed `Taxable Status`; `UNIT` is reduced to its digits (blank = 0).
4. `merge1` = invoices ⨝ products on `Item` (inner join; lines with unknown items disappear).
5. `merge2` = merge1 ⨝ customers on `Customer` (inner join; lines with unknown customers disappear).
6. Builds the 29 official columns; only these are written to the report.
7. **Keeps only rows with `UNIT != 0`**, then sets `Unit = 1`. *This UNIT filter, not the taxable
   flag, decides what is on the report.*
8. **Reporting = Σ Value × Quantity**, compared with the liability from the TAX file (computed in `report_review.py`).
9. Writes the report plus `missing_due_to_invoice_filter`, `missing_after_merge1`,
   `missing_after_merge2`, `missing_after_filtering`, and `rows_with_missing_data`.

### Input file facts
| File | Notes |
|---|---|
| CUSTOMERS | Newer exports have dedicated `City`, `State`, `Zip`, `Street1` columns (all populated). Older ones (2025) only have `Bill to 1` / `Bill to 2`. `Sales Tax Code` values seen: CKC, IL, Tax, CHC, CCC, plus out-of-state codes (PA, VA, NJ, MI, IN, KS, …) and `Non`. `Customer Type`: Retail / Wholesale / blank. |
| INVOICES | QuickBooks "sales by customer detail". Some exports have a first sheet `QuickBooks Desktop Export Tips`, so always read `Sheet1`. |
| PRODUCTS | `UPC` comes in as strings and **preserves leading zeros** (382 of 822 UPCs start with 0). UPC lengths vary (9–15). |
| TAX | QuickBooks sales-tax liability report. Lines: `IL`, `IL TP TAX`, `V TAX`, then `Total ILLINOIS STATE TAX`, the no-tax-vendor section and `TOTAL`. |
| PURCHASING | Exists from 2026 on. Already in TP-1-IL layout (schedule 1B, purchases from e.g. a wholesaler). Was moved into place but **never read by anything** before; it is now used for UPC → manufacturer lookup. |

---

## 2. Bugs found (and fixed)

### 2.1 Liability read from the wrong cell (critical)
`LIABILTY_VALUE_CELL = 'H6'` pointed at the `IL TP TAX` line. From at least May 2026 on, QuickBooks
adds an `IL` line above it, so **H6 lands on `V TAX` and reads 0 every month**. The Difference column
has been meaningless since then, and liability had to be reconciled by hand.

The correct liability is the **`TOTAL` row's `Taxable Sales`**, which covers IL + IL TP TAX + V TAX.
Example, May 2026: 957.75 (IL) + 77,231 (IL TP TAX) = 78,188.75, exactly equal to Reporting.

**Fix:** `extract_liability` now finds the value by its row and column labels; the fixed cell is only
a fallback, and it prints a warning when used. With this change, 11 of the 13 months that have a TAX
file reconcile to the cent.

### 2.2 City/State/Zip blank (common error #2, root cause found)
The reader did `Bill to 2.split(',')`. When `Bill to 2` has no comma (e.g. `CHICAGO IL 60651-2623`),
City, State and Zip all came out blank. It also left trailing spaces (`"CHICAGO , IL"` gave `"CHICAGO "`).
September 2026 had 7 such customers; in September 2025 the only manual edits made to the final
report were filling in City/State/Zip on about 20 rows.
- Duplicate customer names were **not** the cause (0 duplicates found in the months checked).
- Some customers truly have no zip in QuickBooks (e.g. `SHIV GANGA INC` → `CREVE COEUR , IL`).

**Fix:** `utils/address_utils.py` prefers the dedicated City/State/Zip columns, then falls back to a regex
that handles a missing comma, a missing zip and ZIP+4. The review step also pulls a missing piece
from **other months'** customer files.

### 2.3 "Missing data rows exported: N" was wrong
When no rows had missing data, assigning the full-length `Missing Columns` Series to the empty
frame re-expanded it to every row, so the terminal printed 3016 when the real answer was 0.
**Fixed** by computing the column on the filtered frame.

### 2.4 "Missing due to invoice filter" was always 0
It was computed *after* `dropna(subset=['Num'])`. It is now captured before the drop and limited to
lines that have an `Item` (the 149 other no-number rows per month are just customer subtotals).

### 2.5 `Wholesale` is not a valid IDOR customer type
The reader only mapped `Retail` to `Retailer`. It now also maps `Wholesale` to `Wholesaler`.

### 2.6 `N/A` reads as blank in pandas
Reading the report with default pandas settings turns `"N/A"` (Manufacturer, MSA Status) into NaN.
Any analysis of the report must use `dtype=str, keep_default_na=False`.

---

## 3. Decisions (resolved November 2026)

1. **UPC leading zeros moved to the end is an intentional workaround. Do not change it.** `reader.py` does
   `x.lstrip("0") + "0"*n` (`047995100926` → `479951009260`). The review compares UPCs with zeros
   stripped from both ends so that UPC lookups still match.
2. **Tax Jurisdiction:** `CKC` is always translated to `IL`. `CHC` is legitimate and must be left as-is.
   `constants.TAX_JURISDICTION_FIXES = {'CKC': 'IL', 'Tax': 'IL'}`, `VALID_TAX_JURISDICTIONS = {'IL', 'CHC'}`.
   Any other code (e.g. `CCC`, seen in late 2025) still gets a warning.
3. **`TUB` is allowed in both** Unit of Measure (rule 4) and Unit Description (rule 5). `report_rules.md`
   and `constants.VALID_UPC_UNITS_OF_MEASURE` were updated, and the `TIN. FOI` typo in rule 4 was fixed.
4. **`BLACK SMOOTH` → `GOOD TIMES LLC`.** Added to `constants.MANUFACTURERS`, which takes priority over
   the past-reports value (THROWBACK INC). Note: the other Good Times brands in constants use
   `GOOD TIMES USA LLC`.
5. **Manufacturer EIN stays `999999999`.** This is accepted, not an error.
6. **Customer IDs in the early reports (2025) can be ignored.** The sales-tax account numbers used
   there (`2278633`, `42329140`) date from when reporting was new. Rule R8 still applies to current months.
7. Early 2025 months (`APRIL/FEBRUARY/MARCH/MAY_2025`, `January_2025`) have no TAX file and can't be reviewed.

---

## 4. Causes of a Reporting ≠ Liability difference

Since the report keeps rows by `UNIT != 0` while QuickBooks counts rows by taxable status, any item
where the two disagree creates a difference. The review measures each of these:

| Key | Cause | Effect on Reporting − Liability | Seen in |
|---|---|---|---|
| A | Taxable item dropped because UNIT is missing/0 | − | **Dec 2025: exactly −$68** (MR FOG AURA 5CT PUNCHY PEACH) |
| B | Invoice item not in product list (merge1 loss) | − | |
| C | Taxable line for a customer not in customer list (merge2 loss) | − | Jan/Mar/Jun 2026 had losses but they were non-taxable |
| D | Item has a UNIT but is marked **Non**-taxable (found from the PRODUCTS + INVOICES files) | + | **Jun 2025: +$2,072** (HAVANA LEAF 2PK), with an $18 residual |
| E | Sales to wholesale customers | + | |
| F | Customer with sales tax code `Non` or out of state | + | |
| G | UPC bought tax-paid from a wholesaler this month (PURCHASING) | + | hypothesis from common-errors doc |
| H | Lines duplicated by duplicate customer names | + | |
| I | Qty × Sales Price ≠ QuickBooks Amount (price override/rounding) | ± | |

**Unexplained case:** September 2025, +$98. No category, item, invoice or customer adds up to it. Most likely an
item's taxable flag changed in QuickBooks between invoicing and the product export. The tool reports
this honestly instead of guessing.

### Month-by-month result (after the fixes)
| Month | Difference | Status |
|---|---|---|
| Aug 2025, Oct 2025, Nov 2025, Jan 2026 – Sep 2026 | 0.00 | reconciled |
| Jun 2025 | +2,054 | D explains 2,072; −18 left |
| Sep 2025 | +98 | unexplained |
| Dec 2025 | −68 | fully explained by A |
| Jul 2026, Jun 2026, Sep 2026 | 0.00 | **READY TO UPLOAD** with no manual work |

---

## 5. Manufacturer resolution (common error #3)

Fuzzy brand-name matching alone is **dangerous**. Scores against `constants.MANUFACTURERS`:

| Brand | Best fuzzy match | Score | Correct answer |
|---|---|---|---|
| BASS LEAF | GRABBA LEAF | 0.70 | LEAF MAFIA GROUP LLC (a typo of DA BOSS LEAF) |
| DA BOSS LEAF | LOOSE LEAF | 0.64 | LEAF MAFIA GROUP LLC |
| BLACK SMOOTH | BLACK& MIL | 0.64 | GOOD TIMES LLC (now in constants) |
| GOODTIME | GOOD TIMES | 0.95 | ✔ |
| BACK WOOD | BACKWOOD | 0.94 | ✔ |

The order of trust used instead:
1. `constants.MANUFACTURERS`, ignoring spacing and punctuation (`MRFOG` = `MR FOG`)
2. Your past final reports, same brand
3. PURCHASING files (all months), same UPC; supplier names normalized to your existing spelling
4. Your past final reports, same UPC (caught `SISHER` and `GOLDEN HARVES` typos)
5. Brand spelling similarity of at least `MANUFACTURER_FUZZY_CUTOFF` (0.85); anything lower is only suggested

Each assignment prints a line you can paste into `constants.MANUFACTURERS` to make it permanent.

---

## 6. What hand edits looked like (comparing regenerated reports with final reports)

- **September 2026:** `Tax Jurisdiction` CKC→IL on 1,406 rows; helper columns deleted. The 15 `N/A`
  manufacturers were still in the final.
- **September 2025:** City/State/Zip filled in on about 20 rows; nothing else.
- **December 2025:** the final was saved **without a header row** (the review code handles both layouts).

---

## 7. Using the review

```bash
python -m pipeline                      # generate + review last month
python -m report_review                 # review only (applies fixes)
python -m report_review -md 2           # two months back
python -m report_review -m JUNE_2026    # explicit folder
python -m report_review --no-fix        # analyze only
```

Outputs in `Reports/`:
- `REVIEW_TP_1_IL_<MONTH>.xlsx`: Summary, Issues (errors first), Auto-Fixes, Difference Analysis,
  Manufacturer Suggestions
- `TP_1_IL_Report_<MONTH>_Dream.xlsx`: only the 29 official columns (the old helper columns from
  `Product Sales Tax Code` through `Difference` were removed; reconciliation now lives in the review
  workbook and the terminal). Fixed in place cell by cell, with formatting and filters kept.
  **Every cell that still has a problem is highlighted: red = error (fix before upload), yellow = warning.**
  Hover a highlighted cell to see the rule and what to do. In Excel you can also *Filter by Color* on any column.
- `TP_1_IL_Report_<MONTH>_Dream_before_review.xlsx`: copy taken before fixing (overwritten each run)

Running the review twice is harmless: highlights from the previous run are cleared first, so a cell you
fixed by hand loses its color on the next run. Only the review's own colors and notes are touched.
A Reporting ≠ Liability difference has no single cell, so it shows in the terminal and in the review
workbook's Summary and Difference Analysis sheets.
A review takes about 15 s, most of it spent loading past reports and purchasing files.

### Rules checked
| Rule | Check | Severity |
|---|---|---|
| R1 | Required cells populated (Price, Weight/Volume excepted); explains *why* a cell is blank | error |
| R2 | Reporting − Liability = 0 | error |
| R3 | Fed Description in allowed list | error |
| R4 | UPCs Unit of Measure in allowed list | error |
| R5 | Unit Description in allowed list | error |
| R6 | UPC 12–20 digits (or missing) | error |
| R7 | Manufacturer not N/A | error |
| R8 | FEIN is 9 real digits; Customer ID is `CT#####`/`TP#####` and not filler | error |
| X1 | State Description / MSA Status in allowed list | error |
| X2 | Tax Jurisdiction is IL or CHC | warning |
| X3 | Schedule Code matches Type of Customer (2B wholesalers, 2C retailers) | warning |
| X4 | Illinois address, 5-digit zip | warning |
| X5 | Value and Quantity positive | warning |

### Auto-fixes and where each value comes from
| Fix | Source |
|---|---|
| Street/City/State/Zip | this month's customer list, then other months' customer lists |
| Manufacturer | see §5 |
| Fed Description / UoM / Unit Description / State Description typos | closest allowed value, score ≥ 0.85 (`LARGE CGAR`, `LARGE CIGARS`, `ROLL YOU OWN`) |
| Customer ID `16083` → `CT16083` | 5-digit ID on a retailer (confirmed by 2026 customer data showing `CT-16083`) |
| Tax Jurisdiction `CKC` → `IL` (`CHC` untouched) | `constants.TAX_JURISDICTION_FIXES` |
| Type of Customer `Retail`/`Wholesale` | `Retailer`/`Wholesaler` |

Unfixable by design (must be corrected in QuickBooks): filler/missing FEIN or license, missing
Customer Type, missing UPC, unknown manufacturer with no source, UNIT or taxable flags.

---

## 8. IDOR TP-1-IL instruction notes (from tax.illinois.gov, rev. R-07/25)
- **Price:** delivery sellers only; "not applicable in Illinois at this time."
- **Weight/Volume:** total weight or volume of the retail package; blank in every example.
- **Value:** the tax is based on the wholesale price for all tobacco products from July 1, 2025.
- **Customer FEIN:** 9 digits; no placeholder allowed. **Customer ID:** active IDOR license, CT##### for
  retailers and TP##### for distributors (examples show it without the hyphen).
- **UPC:** no length is stated; examples have 11 or 12 digits. The 12–20 limit comes from `report_rules.md`.
- **Schedules:** 2B = sold to a distributor, wholesaler or other licensee (sales between distributors for resale are not taxable);
  2C = sold to a retailer or end user.
- **MSA Status values:** OPM, NPM, SPM, N/A, PM, NPM1, NPM2, NSM. **State Description:** IL-OTP, IL-MS, IL-ECIG.

---

## 9. Files touched
| File | Change |
|---|---|
| `report_review.py` | **new**: checks, fixes, difference analysis, workbook and terminal summary |
| `utils/address_utils.py` | **new**: robust City/State/Zip parsing |
| `utils/excel_utils.py` | `extract_liability` finds the value by label; `read_sheet` accepts optional columns |
| `reader.py` | address fix, missing-rows count fix, invoice-filter fix, Wholesaler mapping, writes only the 29 official columns (helper columns and the Reporting/Liability/Difference cells removed; UPC handling untouched) |
| `constants.py` | allowed-value lists (TUB in both unit lists), filler values, Tax Jurisdiction mapping (IL + CHC valid), fuzzy cutoff, `BLACK SMOOTH` manufacturer |
| `report_rules.md` | rule 4 now includes TUB |
| `pipeline.py` | calls `review_report` after `do_taxes` |
