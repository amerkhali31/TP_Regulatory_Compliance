"""
Automated review of a generated TP-1-IL report.

What it does
------------
1. Checks every rule in report_rules.md (plus a few extra sanity checks) row by row.
2. Auto-fixes the known, mechanical errors from report_common_errors.md:
     - blank Street/City/State/Zip      -> filled from the customer workbook
     - Manufacturer N/A                 -> resolved from constants / past reports / purchasing UPCs / close spelling
     - Tax Jurisdiction codes           -> rewritten via constants.TAX_JURISDICTION_FIXES
     - Reporting / Liability / Difference cells -> recomputed (liability located by label)
3. Explains a Reporting vs Liability difference by sizing every known cause and finding
   the combination that adds up to the difference exactly.
4. Writes REVIEW_TP_1_IL_<MONTH>.xlsx (Summary / Issues / Auto-Fixes / Difference Analysis /
   Manufacturer Suggestions), highlights every cell that still has a problem in the report\n   (red = error, yellow = warning, hover for the reason), and prints a summary.

Usage
-----
    python -m report_review              # review last month's report (fixes applied)
    python -m report_review -md 2        # two months back
    python -m report_review --no-fix     # analyze only, do not modify the report
    python -m report_review --verify     # re-check after you fixed things by hand (no auto-fix, refreshes highlights)
    python -m report_review --verify --report path/to/file.xlsx   # verify a specific copy

It also runs automatically at the end of `python -m pipeline`.
"""
from __future__ import annotations

import argparse
import glob
import itertools
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

import constants
import privateConstants
from utils.address_utils import customer_city_state_zip
from utils.excel_utils import extract_liability

TOL = 0.005
ERROR, WARN = "ERROR", "WARN"
TYPE_OF_CUSTOMER_FIXES = {"Retail": "Retailer", "Wholesale": "Wholesaler"}
BLANK_HINTS = {
    "Schedule Code": "blank - customer has no Customer Type in QuickBooks",
    "Type of Customer": "blank - customer has no Customer Type in QuickBooks",
    "Street Address": "blank - no address for this customer in any customer workbook",
    "City": "blank - no city for this customer in any customer workbook",
    "State": "blank - no state for this customer in any customer workbook",
    "Zip": "blank - no zip for this customer in any customer workbook",
    "Fed Description": "blank - FED_DESCRIPTION missing on the QuickBooks item",
    "Unit Description": "blank - UNIT DESCRIPTION missing on the QuickBooks item",
    "Brand Family": "blank - BRAND missing on the QuickBooks item",
    "UPC Number": "blank - UPC missing on the QuickBooks item",
}
WHOLESALE_TYPES = {"WHOLESALE", "WHOLESALER", "DISTRIBUTOR", "SUBJOBBER", "DISTRIBUTION CENTER"}

RULES = {
    "R1": "All required cells populated (Price, Weight/Volume excepted)",
    "R2": "Reporting - Liability difference is 0",
    "R3": "Fed Description in allowed list",
    "R4": "UPCs Unit of Measure in allowed list",
    "R5": "Unit Description in allowed list",
    "R6": f"UPC length {constants.UPC_MIN_LEN}-{constants.UPC_MAX_LEN} characters",
    "R7": "Manufacturer is not N/A",
    "R8": "Customer FEIN / Customer ID are legitimate",
    "X1": "State Description / MSA Status in allowed list",
    "X2": f"Tax Jurisdiction is {' or '.join(sorted(constants.VALID_TAX_JURISDICTIONS))}",
    "X3": "Schedule Code matches Type of Customer",
    "X4": "Customer address is in Illinois with a 5-digit zip",
    "X5": "Value and Quantity are positive",
}
# Rules whose violations block upload (WARN-level rules are shown but do not block)
RULE_SEVERITY = {"R1": ERROR, "R2": ERROR, "R3": ERROR, "R4": ERROR, "R5": ERROR, "R6": ERROR,
                 "R7": ERROR, "R8": ERROR, "X1": ERROR, "X2": WARN, "X3": WARN, "X4": WARN, "X5": WARN}


@dataclass
class Issue:
    rule: str
    row: int | None          # Excel row number in the report (None = report-level)
    column: str
    value: str
    message: str
    document: str = ""
    customer: str = ""

    @property
    def severity(self) -> str:
        return RULE_SEVERITY[self.rule]


@dataclass
class Fix:
    row: int
    column: str
    old: str
    new: str
    source: str
    document: str = ""
    customer: str = ""


@dataclass
class DiffCause:
    key: str
    title: str
    amount: float            # signed effect on (Reporting - Liability)
    how_to_fix: str
    lines: pd.DataFrame = field(default_factory=pd.DataFrame)


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------
def _s(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", _s(text).upper())


def _upc_key(upc) -> str:
    """Comparable UPC key. Strips zeros at both ends because reader.py rotates leading zeros to the end."""
    return re.sub(r"\D", "", _s(upc)).strip("0")


def _money(x: float) -> str:
    return f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


def _read_book(path: str | Path, sheet: str | int = 0, **kw) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet, **kw)
    return df[[c for c in df.columns if not str(c).startswith("Unnamed")]]


def _read_optional(path: str | Path) -> pd.DataFrame:
    return _read_book(path) if os.path.exists(path) else pd.DataFrame()


def _load_report(path: str | Path) -> pd.DataFrame:
    """Report as strings (so 'N/A' stays 'N/A'); copes with header-less final reports."""
    df = pd.read_excel(path, dtype=str, keep_default_na=False)
    df.attrs["first_data_row"] = 2
    if "Schedule Code" not in df.columns:
        df = pd.read_excel(path, dtype=str, keep_default_na=False, header=None)
        n = len(constants.TP_1_IL_STRUCTURE)
        df = df.iloc[:, :n]
        df.columns = constants.TP_1_IL_STRUCTURE[: df.shape[1]]
        df.attrs["first_data_row"] = 1
    return df


def _xrow(df: pd.DataFrame, i) -> int:
    """Excel row number of DataFrame index i."""
    return int(i) + df.attrs.get("first_data_row", 2)


def _row_total(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["Value"], errors="coerce").fillna(0) * pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)


# --------------------------------------------------------------------------------------------
# reference data (customers, manufacturers)
# --------------------------------------------------------------------------------------------
class References:
    def __init__(self, read_path: Path, write_path: Path, month_year: str):
        self.month_year = month_year
        self.customers = _read_book(read_path / f"{month_year}_CUSTOMERS.xlsx", privateConstants.CUSTOMER_SHEET_NAME)
        self.products = _read_book(read_path / f"{month_year}_PRODUCTS.xlsx", privateConstants.PRODUCT_SHEET_NAME)
        self.base = read_path.parent.parent  # Customers/dream

        self.customers["_norm"] = self.customers["Customer"].map(_norm)
        self.duplicate_customers = sorted(self.customers.loc[self.customers["Customer"].duplicated(), "Customer"].unique())
        self.duplicate_items = sorted(self.products.loc[self.products["Item"].duplicated(), "Item"].astype(str).unique())
        self._cust_by_name = {r["Customer"]: r for _, r in self.customers.drop_duplicates("Customer").iterrows()}
        self._cust_by_norm = {r["_norm"]: r for _, r in self.customers.drop_duplicates("_norm").iterrows()}
        self._load_manufacturer_sources()

    def customer(self, name: str):
        return self._cust_by_name.get(name) if name in self._cust_by_name else self._cust_by_norm.get(_norm(name))

    def address_history(self, name: str) -> dict[str, str]:
        """Street/City/State/Zip for a customer from other months' customer files (newest file first)."""
        if not hasattr(self, "_addr_hist"):
            self._addr_hist: dict[str, dict[str, str]] = {}
            files = sorted(glob.glob(str(self.base / "*" / privateConstants.DATA_DIRECTORY / "*_CUSTOMERS.xlsx")),
                           key=os.path.getmtime, reverse=True)
            for f in files:
                try:
                    c = _read_book(f, privateConstants.CUSTOMER_SHEET_NAME)
                except Exception:
                    continue
                for _, row in c.iterrows():
                    entry = self._addr_hist.setdefault(_norm(row.get("Customer")), {})
                    city, state, zip5 = customer_city_state_zip(row)
                    for k, v in (("Street Address", _s(row.get("Bill to 1"))), ("City", city), ("State", state), ("Zip", zip5)):
                        if v:
                            entry.setdefault(k, v)
        return self._addr_hist.get(_norm(name), {})

    # -- manufacturers -----------------------------------------------------------------------
    def _load_manufacturer_sources(self):
        known = constants.MANUFACTURERS
        self.mfr_by_norm_brand = {_norm(k): v for k, v in known.items()}
        canonical = sorted(set(known.values()))

        def canon(name: str) -> str:
            name = _s(name).upper()
            best = max(canonical, key=lambda c: SequenceMatcher(None, name, c).ratio(), default=name)
            return best if SequenceMatcher(None, name, best).ratio() >= 0.85 else name

        # Past final reports (your own manual corrections) - brand -> manufacturer, UPC -> manufacturer
        brand_votes, upc_votes = defaultdict(Counter), defaultdict(Counter)
        for f in glob.glob(str(self.base / "*" / privateConstants.REPORT_DIRECTORY / "TP_1_IL_Report_*.xlsx")):
            if self.month_year in f:
                continue
            try:
                d = _load_report(f)
            except Exception:
                continue
            if "Manufacturer" not in d.columns:
                continue
            d = d[~d["Manufacturer"].isin(["", "N/A"])]
            for b, m, u in zip(d["Brand Family"], d["Manufacturer"], d["UPC Number"]):
                brand_votes[_norm(b)][m] += 1
                upc_votes[_upc_key(u)][m] += 1
        self.history_brand = {k: c.most_common(1)[0][0] for k, c in brand_votes.items() if k}
        self.history_upc = {k: c.most_common(1)[0][0] for k, c in upc_votes.items() if k}

        # Purchasing files (supplier-reported manufacturers), every month
        self.purchasing_upc = {}
        for f in sorted(glob.glob(str(self.base / "*" / privateConstants.DATA_DIRECTORY / "*_PURCHASING.xlsx"))):
            try:
                p = pd.read_excel(f, dtype=str)
            except Exception:
                continue
            p.columns = [c.strip().upper() for c in p.columns]
            if {"UPC NUMBER", "MANUFACTURER"} <= set(p.columns):
                for u, m in zip(p["UPC NUMBER"], p["MANUFACTURER"]):
                    if _upc_key(u) and _s(m):
                        self.purchasing_upc[_upc_key(u)] = canon(m)

    def resolve_manufacturer(self, brand: str, upc: str) -> tuple[str | None, str, list[str]]:
        """
        Returns (manufacturer or None, source, alternatives-seen).
        Order of trust: constants (spacing/punctuation-insensitive) -> your past reports (brand) ->
        purchasing file (UPC) -> your past reports (UPC) -> very close brand spelling.
        """
        nb, nu = _norm(brand), _upc_key(upc)
        found = []
        if nb and nb in self.mfr_by_norm_brand:
            found.append((self.mfr_by_norm_brand[nb], f"constants.MANUFACTURERS (brand '{brand}')"))
        if nb and nb in self.history_brand:
            found.append((self.history_brand[nb], "past reports (same brand)"))
        if nu and nu in self.purchasing_upc:
            found.append((self.purchasing_upc[nu], "purchasing file (same UPC)"))
        if nu and nu in self.history_upc:
            found.append((self.history_upc[nu], "past reports (same UPC)"))
        if nb and not found:
            scored = sorted(((SequenceMatcher(None, nb, k).ratio(), k) for k in self.mfr_by_norm_brand), reverse=True)
            if scored and scored[0][0] >= constants.MANUFACTURER_FUZZY_CUTOFF:
                found.append((self.mfr_by_norm_brand[scored[0][1]], f"close spelling ({scored[0][0]:.2f})"))
            else:
                alts = [f"{self.mfr_by_norm_brand[k]} ({s:.2f}, not applied)" for s, k in scored[:2] if s >= 0.6]
                return None, "", alts
        if not found:
            return None, "", []
        alternatives = sorted({m for m, _ in found if m != found[0][0]})
        return found[0][0], found[0][1], alternatives


# --------------------------------------------------------------------------------------------
# rule checks
# --------------------------------------------------------------------------------------------
def check_rows(df: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []
    required = [c for c in constants.TP_1_IL_STRUCTURE if c in df.columns and c not in constants.OPTIONAL_COLUMNS]
    fein_re = re.compile(r"^\d{9}$")
    id_re = re.compile(constants.CUSTOMER_ID_PATTERN)

    for i, r in df.iterrows():
        excel_row = _xrow(df, i)
        doc, cust = r.get("Document Number", ""), r.get("Name", "")

        def add(rule, col, msg):
            issues.append(Issue(rule, excel_row, col, _s(r.get(col, "")), msg, doc, cust))

        for c in required:
            if _s(r[c]) == "":
                add("R1", c, BLANK_HINTS.get(c, "blank"))
        fd = _s(r.get("Fed Description")).upper()
        if fd and fd not in constants.VALID_FED_DESCRIPTIONS:
            add("R3", "Fed Description", "not an allowed Fed Description")
        uom = _s(r.get("UPCs Unit of Measure")).upper()
        if uom and uom not in constants.VALID_UPC_UNITS_OF_MEASURE:
            add("R4", "UPCs Unit of Measure", "not an allowed unit of measure")
        ud = _s(r.get("Unit Description")).upper()
        if ud and ud not in constants.VALID_UNIT_DESCRIPTIONS:
            add("R5", "Unit Description", "not an allowed unit description")
        upc = _s(r.get("UPC Number"))
        if upc.lower() in {"nan", "none", "0"}:
            add("R6", "UPC Number", "missing UPC in QuickBooks item")
        elif upc and not (constants.UPC_MIN_LEN <= len(upc) <= constants.UPC_MAX_LEN):
            add("R6", "UPC Number", f"UPC is {len(upc)} characters - must be {constants.UPC_MIN_LEN}-{constants.UPC_MAX_LEN}; fix it on the QuickBooks item")
        elif upc and not upc.isdigit():
            add("R6", "UPC Number", "contains non-digits")
        if _s(r.get("Manufacturer")).upper() in {"N/A", "NA"}:
            add("R7", "Manufacturer", f"brand '{_s(r.get('Brand Family'))}' has no manufacturer")

        fein = re.sub(r"\D", "", _s(r.get("Customer FEIN")))
        if _s(r.get("Customer FEIN")):
            if fein in constants.FILLER_FEINS or len(set(fein)) == 1:
                add("R8", "Customer FEIN", "filler FEIN - customer has no FEIN in QuickBooks")
            elif not fein_re.match(fein):
                add("R8", "Customer FEIN", "FEIN must be 9 digits")
        cid = re.sub(r"[^A-Z0-9]", "", _s(r.get("Customer ID")).upper())
        if _s(r.get("Customer ID")):
            if cid in constants.FILLER_CUSTOMER_IDS:
                add("R8", "Customer ID", "filler license - customer has no LICENSE in QuickBooks")
            elif not id_re.match(cid):
                add("R8", "Customer ID", "expected CT##### or TP#####")

        sd = _s(r.get("State Description")).upper()
        if sd and sd not in constants.VALID_STATE_DESCRIPTIONS:
            add("X1", "State Description", "not IL-OTP / IL-MS / IL-ECIG")
        msa = _s(r.get("MSA Status")).upper()
        if msa and msa not in constants.VALID_MSA_STATUSES:
            add("X1", "MSA Status", "not an allowed MSA status")
        tj = _s(r.get("Tax Jurisdiction"))
        if tj and tj not in constants.VALID_TAX_JURISDICTIONS:
            add("X2", "Tax Jurisdiction", f"'{tj}' is not {' or '.join(sorted(constants.VALID_TAX_JURISDICTIONS))} - check the customer's Sales Tax Code in QuickBooks")
        sc, toc = _s(r.get("Schedule Code")).upper(), _s(r.get("Type of Customer")).upper()
        if sc and toc and toc not in constants.SCHEDULE_CUSTOMER_TYPES.get(sc, {toc}):
            add("X3", "Schedule Code", f"{sc} does not allow customer type '{toc.title()}'")
        st, z = _s(r.get("State")).upper(), _s(r.get("Zip"))
        if st and st != "IL":
            add("X4", "State", "customer address is outside Illinois")
        if z and not re.fullmatch(r"\d{5}", z):
            add("X4", "Zip", "zip is not 5 digits")
        for c in ("Value", "Quantity"):
            v = pd.to_numeric(_s(r.get(c)), errors="coerce")
            if pd.notna(v) and v <= 0:
                add("X5", c, "zero or negative")
    return issues


# --------------------------------------------------------------------------------------------
# auto-fixes (applied to the DataFrame; written back to the workbook cell by cell later)
# --------------------------------------------------------------------------------------------
def apply_fixes(df: pd.DataFrame, refs: References) -> tuple[list[Fix], list[dict]]:
    fixes: list[Fix] = []
    mfr_report: dict[str, dict] = {}

    def set_cell(i, col, new, source):
        old = _s(df.at[i, col])
        if old != new:
            df.at[i, col] = new
            fixes.append(Fix(_xrow(df, i), col, old, new, source, df.at[i, "Document Number"], df.at[i, "Name"]))

    for i, r in df.iterrows():
        # -- address (common error #2) ----------------------------------------------------
        if any(_s(r.get(c)) == "" for c in ("Street Address", "City", "State", "Zip")):
            c = refs.customer(_s(r["Name"]))
            if c is not None:
                city, state, zip5 = customer_city_state_zip(c)
                street = re.sub(r"[^a-zA-Z0-9\s]", "", _s(c.get("Bill to 1")) or _s(c.get("Street1")))[:49]
                for col, val in (("Street Address", street), ("City", city), ("State", state), ("Zip", zip5)):
                    if _s(r.get(col)) == "" and val:
                        set_cell(i, col, val, "customer workbook")
            hist = refs.address_history(_s(r["Name"]))
            for col in ("Street Address", "City", "State", "Zip"):
                if _s(df.at[i, col]) == "" and hist.get(col):
                    val = re.sub(r"[^a-zA-Z0-9\s]", "", hist[col])[:49] if col == "Street Address" else hist[col]
                    set_cell(i, col, val, "customer workbook from another month")

        # -- typos in coded columns (e.g. 'LARGE CGAR') -------------------------------------
        for col, allowed in (("Fed Description", constants.VALID_FED_DESCRIPTIONS),
                             ("UPCs Unit of Measure", constants.VALID_UPC_UNITS_OF_MEASURE),
                             ("Unit Description", constants.VALID_UNIT_DESCRIPTIONS),
                             ("State Description", constants.VALID_STATE_DESCRIPTIONS)):
            v = _s(r.get(col)).upper()
            if v and v not in allowed:
                if v.replace("PRODUCTS", "PRODUCT") in allowed:
                    set_cell(i, col, v.replace("PRODUCTS", "PRODUCT"), "allowed-value spelling")
                    continue
                best = max(allowed, key=lambda a: SequenceMatcher(None, v, a).ratio())
                if len(v) > 3 and SequenceMatcher(None, v, best).ratio() >= 0.85:
                    set_cell(i, col, best, f"allowed-value spelling ({SequenceMatcher(None, v, best).ratio():.2f})")

        # -- customer ID missing its CT/TP prefix (QuickBooks LICENSE typed as digits only) ----
        cid = _s(r.get("Customer ID"))
        if re.fullmatch(r"\d{5}", cid) and _s(df.at[i, "Type of Customer"]).upper() in constants.SCHEDULE_CUSTOMER_TYPES["2C"]:
            set_cell(i, "Customer ID", "CT" + cid, "retailer license -> CT prefix")

        # -- type of customer (IDOR wants 'Retailer' / 'Wholesaler') -------------------------
        toc = _s(r.get("Type of Customer"))
        if toc in TYPE_OF_CUSTOMER_FIXES:
            set_cell(i, "Type of Customer", TYPE_OF_CUSTOMER_FIXES[toc], "IDOR customer type name")

        # -- tax jurisdiction ---------------------------------------------------------------
        tj = _s(r.get("Tax Jurisdiction"))
        if tj in constants.TAX_JURISDICTION_FIXES:
            set_cell(i, "Tax Jurisdiction", constants.TAX_JURISDICTION_FIXES[tj], "constants.TAX_JURISDICTION_FIXES")

        # -- manufacturer (common error #3) -------------------------------------------------
        if _s(r.get("Manufacturer")).upper() in {"", "N/A", "NA"}:
            brand, upc = _s(r.get("Brand Family")), _s(r.get("UPC Number"))
            mfr, source, alts = refs.resolve_manufacturer(brand, upc)
            entry = mfr_report.setdefault(brand or "(blank brand)", {
                "Brand Family": brand or "(blank brand)", "Example Product": _s(r.get("Product Description")),
                "Rows": 0, "Assigned Manufacturer": mfr or "", "Source": source or "UNRESOLVED",
                "Other Candidates / Conflicts": "; ".join(alts),
                "constants.MANUFACTURERS entry": f"'{brand}': '{mfr}'," if mfr and brand else "",
            })
            entry["Rows"] += 1
            if mfr:
                set_cell(i, "Manufacturer", mfr, f"manufacturer: {source}")

    return fixes, list(mfr_report.values())


# --------------------------------------------------------------------------------------------
# reporting vs liability difference
# --------------------------------------------------------------------------------------------
def explain_difference(diff: float, df: pd.DataFrame, refs: References, read_path: Path, write_path: Path) -> tuple[list[DiffCause], list[str]]:
    causes: list[DiffCause] = []
    df = df.copy()
    df["Total"] = _row_total(df)
    taxed = lambda s: s.astype(str).str.strip().str.upper().eq("TAX")

    filtered = _read_optional(write_path / "missing_after_filtering.xlsx")
    if not filtered.empty and "Taxable Status" in filtered:
        t = filtered[taxed(filtered["Taxable Status"])].copy()
        if len(t):
            t["Amount"] = t["Qty"] * t["Sales Price"]
            causes.append(DiffCause("A", "Taxable items dropped because UNIT is missing/0", -t["Amount"].sum(),
                                    "Add the UNIT to these items in QuickBooks (item list) and re-run",
                                    t[["Num", "Customer", "Item", "Description", "Qty", "Sales Price", "Amount"]]))

    m1 = _read_optional(write_path / "missing_after_merge1.xlsx")
    if not m1.empty:
        m1 = m1.copy(); m1["Amount"] = m1["Qty"] * m1["Sales Price"]
        causes.append(DiffCause("B", "Invoice lines whose Item is not in the product list", -m1["Amount"].sum(),
                                "Item was renamed/deleted in QuickBooks - re-export the product list or fix the item",
                                m1[["Num", "Customer", "Item", "Qty", "Sales Price", "Amount"]]))

    m2 = _read_optional(write_path / "missing_after_merge2.xlsx")
    if not m2.empty and "Taxable Status" in m2:
        t = m2[taxed(m2["Taxable Status"])].copy()
        if len(t):
            t["Amount"] = t["Qty"] * t["Sales Price"]
            causes.append(DiffCause("C", "Taxable invoice lines whose Customer is not in the customer list", -t["Amount"].sum(),
                                    "Customer missing from the TP1IL customers memorized report (inactive or renamed?)",
                                    t[["Num", "Customer", "Item", "Qty", "Sales Price", "Amount"]]))

    # Invoice lines that made it onto the report (tobacco items = UNIT != 0, on reported invoices/customers)
    unit = pd.to_numeric(refs.products["UNIT"].astype(str).str.replace(r"\D", "", regex=True), errors="coerce").fillna(0)
    tobacco = refs.products[unit != 0]
    inv = pd.DataFrame()
    try:
        inv = _read_book(read_path / f"{refs.month_year}_INVOICES.xlsx", privateConstants.INVOICE_SHEET_NAME).dropna(subset=["Num"])
        inv["Item"] = inv["Item"].astype(str).str.replace(r"\(.*\)", "", regex=True).str.strip()
        reported_docs = set(pd.to_numeric(df["Document Number"], errors="coerce").dropna())
        inv = inv[inv["Num"].isin(reported_docs) & inv["Name"].isin(set(df["Name"])) & inv["Item"].isin(set(tobacco["Item"].astype(str)))].copy()
        inv["Total"] = inv["Qty"] * inv["Sales Price"]
    except Exception:
        inv = pd.DataFrame()

    if len(inv):
        non_taxable = set(tobacco.loc[~taxed(tobacco["Sales Tax Code"]), "Item"].astype(str))
        n = inv[inv["Item"].isin(non_taxable)]
        if len(n):
            causes.append(DiffCause("D", "Report rows for items marked NON-taxable in QuickBooks", n["Total"].sum(),
                                    "Item has a UNIT but is marked Non - if it is tobacco, mark it taxable in QuickBooks",
                                    n[["Num", "Name", "Item", "Qty", "Sales Price", "Total"]]))

    wholesale = df[df["Schedule Code"].str.upper().eq("2B") | df["Type of Customer"].str.upper().isin(WHOLESALE_TYPES)]
    if len(wholesale):
        causes.append(DiffCause("E", "Report rows sold to wholesale customers (not in liability)", wholesale["Total"].sum(),
                                "Sales to wholesalers are not taxable - confirm they belong on the report as 2B",
                                wholesale[["Document Number", "Name", "Type of Customer", "Product Description", "Total"]]))

    cust_code = refs.customers.drop_duplicates("Customer").set_index("Customer")["Sales Tax Code"].astype(str)
    codes = df["Name"].map(cust_code).fillna("")
    out = df[codes.str.upper().eq("NON") | (df["State"].str.upper().ne("IL") & df["State"].ne(""))]
    if len(out):
        causes.append(DiffCause("F", "Report rows for non-taxable / out-of-state customers", out["Total"].sum(),
                                "Customer's QuickBooks sales tax code is Non or out-of-state",
                                out[["Document Number", "Name", "State", "Product Description", "Total"]]))

    purch_path = read_path / f"{refs.month_year}_PURCHASING.xlsx"
    if purch_path.exists():
        p = pd.read_excel(purch_path, dtype=str)
        p.columns = [c.strip().upper() for c in p.columns]
        if "UPC NUMBER" in p:
            keys = set(p["UPC NUMBER"].map(_upc_key)) - {""}
            hit = df[df["UPC Number"].map(_upc_key).isin(keys)]
            if len(hit):
                causes.append(DiffCause("G", "Report rows for UPCs bought tax-paid from a wholesaler this month", hit["Total"].sum(),
                                        "If tax on these was already paid upstream they should not count toward liability",
                                        hit[["Document Number", "Name", "UPC Number", "Product Description", "Total"]]))

    if refs.duplicate_customers:
        d = df[df["Name"].isin(refs.duplicate_customers)]
        counts = refs.customers["Customer"].value_counts()
        extra = (d["Total"] * (1 - 1 / d["Name"].map(counts))).sum()
        causes.append(DiffCause("H", "Lines duplicated by duplicate customer names in the customer list", extra,
                                "Remove/rename the duplicate customer so invoice lines are not counted twice",
                                d[["Document Number", "Name", "Product Description", "Total"]]))

    if len(inv) and "Amount" in inv:
        inv["Rounding"] = inv["Total"] - inv["Amount"]
        r = inv[inv["Rounding"].abs() > TOL]
        if len(r):
            causes.append(DiffCause("I", "Rounding: Qty x Sales Price differs from QuickBooks Amount", r["Rounding"].sum(),
                                    "Price overridden on the invoice - Value is Sales Price, QuickBooks uses Amount",
                                    r[["Num", "Name", "Item", "Qty", "Sales Price", "Amount", "Rounding"]]))

    notes: list[str] = []
    if abs(diff) <= TOL:
        return causes, notes

    # Which combination of causes explains the difference exactly?
    nonzero = [c for c in causes if abs(c.amount) > TOL]
    matches = []
    for k in range(1, len(nonzero) + 1):
        for combo in itertools.combinations(nonzero, k):
            if abs(sum(c.amount for c in combo) - diff) <= TOL:
                matches.append(combo)
        if matches:
            break
    if matches:
        for combo in matches[:3]:
            notes.append("EXPLAINED: " + " + ".join(f"[{c.key}] {c.title} ({_money(c.amount)})" for c in combo))
        return causes, notes

    # Otherwise take the combination that gets closest, then hunt for whatever is left over
    residual = diff
    best = min((combo for k in range(1, len(nonzero) + 1) for combo in itertools.combinations(nonzero, k)),
               key=lambda combo: abs(diff - sum(c.amount for c in combo)), default=())
    if best and abs(diff - sum(c.amount for c in best)) < abs(diff) - TOL:
        residual = round(diff - sum(c.amount for c in best), 2)
        notes.append("PARTIAL: " + " + ".join(f"[{c.key}] {c.title} ({_money(c.amount)})" for c in best)
                     + f" explains {_money(diff - residual)}; {_money(residual)} still unexplained.")
    else:
        notes.append(f"No combination of known causes adds up to {_money(diff)}.")
    n_before = len(notes)
    diff = residual
    if diff > 0:
        pool, label = df, "report"
        pool_total = pool["Total"]
    else:
        pool = filtered.copy() if not filtered.empty else pd.DataFrame()
        label = "dropped (non-taxable / no UNIT)"
        if len(pool):
            pool = pool.rename(columns={"Num": "Document Number", "Customer": "Name", "Description": "Product Description"})
            pool_total = pool["Qty"] * pool["Sales Price"]
    if len(pool):
        pool = pool.assign(Total=pool_total)
        for key in ("Product Description", "Document Number", "Name"):
            g = pool.groupby(key)["Total"].sum()
            hits = g[(g - abs(diff)).abs() <= TOL].index.tolist()
            for h in hits[:5]:
                notes.append(f"CANDIDATE: {key} '{h}' in the {label} rows totals exactly {_money(abs(diff))}"
                             + (" - may be non-taxable in QuickBooks" if diff > 0 else " - may be taxable in QuickBooks"))
    if len(notes) == n_before:
        notes.append(f"No single item, invoice or customer totals {_money(abs(diff))} either. Likely an item's taxable status in QuickBooks "
                     "differs from the exported product list (changed after the invoices were made) - compare item by item.")
    return causes, notes


# --------------------------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------------------------
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
OK_FILL, BAD_FILL, WARN_FILL = PatternFill("solid", fgColor="C6EFCE"), PatternFill("solid", fgColor="FFC7CE"), PatternFill("solid", fgColor="FFEB9C")


def _style_sheet(ws):
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
    for col in ws.columns:
        width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(width + 2, 70)
    ws.freeze_panes = "A2"
    if ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions


def write_review_workbook(path: Path, summary_rows: list[list], rule_table: pd.DataFrame, issues: list[Issue],
                          fixes: list[Fix], causes: list[DiffCause], notes: list[str], mfr_rows: list[dict]):
    issues_df = pd.DataFrame([{
        "Severity": x.severity, "Rule": x.rule, "Rule Description": RULES[x.rule], "Excel Row": x.row,
        "Document Number": x.document, "Customer": x.customer, "Column": x.column, "Value": x.value, "Problem": x.message,
    } for x in issues]) if issues else pd.DataFrame(columns=["Severity", "Rule", "Rule Description", "Excel Row", "Document Number", "Customer", "Column", "Value", "Problem"])
    fixes_df = pd.DataFrame([{
        "Excel Row": f.row, "Document Number": f.document, "Customer": f.customer, "Column": f.column,
        "Old Value": f.old, "New Value": f.new, "Source": f.source,
    } for f in fixes]) if fixes else pd.DataFrame(columns=["Excel Row", "Document Number", "Customer", "Column", "Old Value", "New Value", "Source"])
    issues_df = issues_df.sort_values(["Severity", "Rule", "Excel Row"], key=lambda s: s.map({ERROR: 0, WARN: 1}).fillna(s) if s.name == "Severity" else s, na_position="first")
    cause_df = pd.DataFrame([{"Cause": c.key, "Description": c.title, "Effect on Difference": round(c.amount, 2),
                              "Lines": len(c.lines), "How to fix": c.how_to_fix} for c in causes])

    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        pd.DataFrame(summary_rows, columns=["Item", "Value"]).to_excel(xw, sheet_name="Summary", index=False)
        rule_table.to_excel(xw, sheet_name="Summary", index=False, startrow=len(summary_rows) + 2)
        issues_df.to_excel(xw, sheet_name="Issues", index=False)
        fixes_df.to_excel(xw, sheet_name="Auto-Fixes", index=False)
        row = 0
        pd.DataFrame({"Analysis": notes or ["Difference is 0 - nothing to explain."]}).to_excel(xw, sheet_name="Difference Analysis", index=False)
        row += max(len(notes), 1) + 2
        if len(cause_df):
            cause_df.to_excel(xw, sheet_name="Difference Analysis", index=False, startrow=row)
            row += len(cause_df) + 2
            for c in causes:
                if len(c.lines):
                    pd.DataFrame({f"[{c.key}] {c.title}": []}).to_excel(xw, sheet_name="Difference Analysis", index=False, startrow=row)
                    c.lines.head(500).to_excel(xw, sheet_name="Difference Analysis", index=False, startrow=row + 1)
                    row += min(len(c.lines), 500) + 3
        pd.DataFrame(mfr_rows or [{"Brand Family": "(no N/A manufacturers)"}]).to_excel(xw, sheet_name="Manufacturer Suggestions", index=False)

    wb = load_workbook(path)
    for ws in wb.worksheets:
        _style_sheet(ws)
    ws = wb["Summary"]
    ws.auto_filter.ref = None
    for r in ws.iter_rows(min_row=1):
        for c in r:
            if c.value in ("PASS", "READY TO UPLOAD"):
                c.fill = OK_FILL
            elif c.value in ("FAIL", "NEEDS ATTENTION"):
                c.fill = BAD_FILL
            elif c.value == "WARN":
                c.fill = WARN_FILL
    for cell in ws[len(summary_rows) + 3]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
    ws.column_dimensions["A"].width = 48
    ws.column_dimensions["B"].width = 62
    wb["Issues"].column_dimensions["C"].width = 45
    wb.save(path)


REVIEW_AUTHOR = "TP-1-IL Review"
MARK_STYLES = {  # severity -> (fill, font)
    ERROR: (PatternFill("solid", fgColor="FF8080"), Font(bold=True, color="9C0006")),
    WARN: (PatternFill("solid", fgColor="FFE699"), Font(color="7F6000")),
}
_MARK_COLORS = {"00FF8080", "FFFF8080", "00FFE699", "FFFFE699"}


def write_back(report_path: Path, fixes: list[Fix], issues: list[Issue]):
    """
    Apply fixes cell-by-cell (so formatting/filters are preserved) and mark every cell that still has a
    problem: red = error (must fix before upload), yellow = warning. Hover a marked cell to read the
    problem. Marks from a previous review run are cleared first, so fixed cells lose their color.
    """
    wb = load_workbook(report_path)
    ws = wb.active
    header = {str(c.value): c.column for c in ws[1] if c.value is not None}
    if "Schedule Code" not in header:  # header-less final report: positional columns
        header = {name: i + 1 for i, name in enumerate(constants.TP_1_IL_STRUCTURE)}

    for row in ws.iter_rows():
        for cell in row:
            if cell.fill is not None and cell.fill.fgColor is not None and cell.fill.fgColor.rgb in _MARK_COLORS:
                cell.fill = PatternFill()
                cell.font = Font()
            if cell.comment is not None and cell.comment.author == REVIEW_AUTHOR:
                cell.comment = None

    for f in fixes:  # Fix.row is already the Excel row
        ws.cell(row=f.row, column=header[f.column], value=f.new)

    by_cell: dict[tuple[int, int], list[Issue]] = defaultdict(list)
    for i in issues:
        if i.row is not None and i.column in header:
            by_cell[(i.row, header[i.column])].append(i)
    for (r, c), cell_issues in by_cell.items():
        severity = ERROR if any(i.severity == ERROR for i in cell_issues) else WARN
        cell = ws.cell(row=r, column=c)
        cell.fill, cell.font = MARK_STYLES[severity]
        text = "\n".join(f"{i.severity} {i.rule}: {RULES[i.rule]}\n-> {i.message}" for i in cell_issues)
        cell.comment = Comment(text, REVIEW_AUTHOR, width=320, height=110)
    wb.save(report_path)


# --------------------------------------------------------------------------------------------
# terminal summary
# --------------------------------------------------------------------------------------------
def _c(text, code):
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def print_summary(month_year, n_rows, reporting, liability, rule_table, fixes, causes, notes, mfr_rows, refs, review_path, report_path, marked, ready):
    diff = reporting - liability
    line = "=" * 78
    print(f"\n{line}\n TP-1-IL REVIEW - {month_year}   ({n_rows} report rows)\n{line}")
    ok = abs(diff) <= TOL
    print(f" Reporting {_money(reporting):>14}   Liability {_money(liability):>14}   Difference "
          + _c(f"{_money(diff)}", "32" if ok else "31;1"))
    if not ok:
        for n in notes:
            print("   -> " + n)
        for c in sorted(causes, key=lambda c: -abs(c.amount)):
            if abs(c.amount) > TOL:
                print(f"      [{c.key}] {c.title:<62} {_money(c.amount):>11}  ({len(c.lines)} lines)")
    print(f"\n {'Rule':<5}{'Check':<56}{'Found':>7}{'Fixed':>7}{'Left':>6}")
    for _, r in rule_table.iterrows():
        status = r["Status"]
        mark = _c("PASS", "32") if status == "PASS" else (_c("WARN", "33") if status == "WARN" else _c("FAIL", "31;1"))
        print(f" {r['Rule']:<5}{r['Check'][:55]:<56}{r['Found']:>7}{r['Auto-fixed']:>7}{r['Remaining']:>6}  {mark}")

    if fixes:
        by_src = Counter((f.column if not f.source.startswith("manufacturer") else "Manufacturer") for f in fixes)
        print("\n Auto-fixed: " + ", ".join(f"{col} x{n}" for col, n in by_src.most_common()))
    unresolved = [m for m in mfr_rows if m["Source"] == "UNRESOLVED"]
    conflicts = [m for m in mfr_rows if m["Source"] != "UNRESOLVED" and m["Other Candidates / Conflicts"]]
    assigned = [m for m in mfr_rows if m["Source"] != "UNRESOLVED"]
    if assigned:
        print(" Manufacturers assigned (add to constants.MANUFACTURERS to make permanent):")
        for m in assigned:
            print(f"     {m['constants.MANUFACTURERS entry']:<52} # {m['Source']}")
    for m in conflicts:
        print(_c(f"   ! {m['Brand Family']}: also seen as {m['Other Candidates / Conflicts']} - verify", "33"))
    for m in unresolved:
        print(_c(f"   ! No manufacturer found for brand '{m['Brand Family']}' ({m['Rows']} rows)", "31")
              + (f" - nearest: {m['Other Candidates / Conflicts']}" if m["Other Candidates / Conflicts"] else ""))
    if refs.duplicate_customers:
        print(_c(f"   ! Duplicate customer names in customer list: {', '.join(refs.duplicate_customers[:5])}", "33"))
    if refs.duplicate_items:
        print(_c(f"   ! Duplicate item names in product list: {', '.join(refs.duplicate_items[:5])}", "33"))

    verdict = _c("READY TO UPLOAD", "32;1") if ready else _c("NEEDS ATTENTION", "31;1")
    print(f"\n Status: {verdict}")
    print(f" Review workbook: {review_path}")
    if marked:
        print(f" Report:          {report_path}")
        print(_c(f"                  {marked} cell(s) highlighted (red = error, yellow = warning) - hover a cell for the reason", "33"))
    print(line + "\n")


# --------------------------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------------------------
def review_report(read_path: str, write_path: str, month_year: str, apply: bool = True,
                  verify: bool = False, report_file: str | Path | None = None) -> dict:
    """
    apply=True   normal run: auto-fix the report, back it up first, highlight what is left.
    verify=True  re-check a report you have fixed by hand: NO auto-fixes, the backup of the original is
                 left alone, stale highlights are cleared and anything still wrong is re-highlighted.
                 The result goes to REVIEW_..._VERIFY.xlsx so the first review stays for reference.
    report_file  review this file instead of the default report (e.g. a copy saved elsewhere).
    """
    if verify:
        apply = False
    read_p, write_p = Path(read_path), Path(write_path)
    report_path = Path(report_file).expanduser() if report_file else write_p / f"TP_1_IL_Report_{month_year}_Dream.xlsx"
    df = _load_report(report_path)
    refs = References(read_p, write_p, month_year)
    liability = float(extract_liability(str(read_p / f"{month_year}_TAX.xlsx"), privateConstants.LIABILITY_SHEET_NAME,
                                        privateConstants.LIABILTY_VALUE_CELL))

    issues_before = check_rows(df)
    fixes, mfr_rows = apply_fixes(df, refs) if apply else ([], [])
    if not apply:  # still report what *would* be resolved
        _, mfr_rows = apply_fixes(df.copy(), refs)
    issues_after = check_rows(df) if apply else issues_before

    reporting = round(float(_row_total(df).sum()), 2)
    diff = round(reporting - liability, 2)
    causes, notes = explain_difference(diff, df, refs, read_p, write_p)
    if abs(diff) > TOL:
        issues_after.insert(0, Issue("R2", None, "Difference", _money(diff), "Reporting does not match liability - see Difference Analysis"))

    before, after = Counter(i.rule for i in issues_before), Counter(i.rule for i in issues_after)
    if abs(diff) > TOL:
        before["R2"] = after["R2"] = 1
    rule_rows = []
    for rule, desc in RULES.items():
        left = after[rule]
        status = "PASS" if left == 0 else ("WARN" if RULE_SEVERITY[rule] == WARN else "FAIL")
        rule_rows.append({"Rule": rule, "Check": desc, "Found": before[rule], "Auto-fixed": max(before[rule] - left, 0),
                          "Remaining": left, "Status": status})
    rule_table = pd.DataFrame(rule_rows)
    ready = not any(i.severity == ERROR for i in issues_after)

    marked = 0
    if apply or verify:
        if apply:  # never overwrite the backup of the original with a hand-edited file
            backup = report_path.with_name(report_path.stem + "_before_review.xlsx")
            shutil.copyfile(report_path, backup)
        write_back(report_path, fixes, issues_after)
        marked = len({(i.row, i.column) for i in issues_after if i.row is not None})

    pipeline_counts = []
    for label, fname in (("Lines with no invoice number", "missing_due_to_invoice_filter.xlsx"),
                         ("Lines with unknown item", "missing_after_merge1.xlsx"),
                         ("Lines with unknown customer", "missing_after_merge2.xlsx"),
                         ("Lines dropped for UNIT = 0", "missing_after_filtering.xlsx")):
        d = _read_optional(write_p / fname)
        extra = ""
        if len(d) and "Taxable Status" in d:
            extra = f"  ({d['Taxable Status'].astype(str).str.upper().eq('TAX').sum()} marked taxable)"
        pipeline_counts.append([label, f"{len(d)}{extra}"])

    summary_rows = [
        ["Month", month_year],
        ["Status", "READY TO UPLOAD" if ready else "NEEDS ATTENTION"],
        ["Report rows", len(df)],
        ["Reporting (sum of Value x Quantity)", reporting],
        ["Liability (QuickBooks TOTAL taxable sales)", liability],
        ["Difference", diff],
        *[["Difference analysis", n] for n in notes],
        ["Errors remaining", sum(1 for i in issues_after if i.severity == ERROR)],
        ["Warnings remaining", sum(1 for i in issues_after if i.severity == WARN)],
        ["Cells auto-fixed", len(fixes) if apply else "0 (not applied)"],
        ["Cells highlighted in report", marked if (apply or verify) else "0 (--no-fix)"],
        *pipeline_counts,
        ["Duplicate customer names", ", ".join(refs.duplicate_customers) or "none"],
        ["Duplicate product items", ", ".join(refs.duplicate_items) or "none"],
    ]
    review_path = write_p / f"REVIEW_TP_1_IL_{month_year}{'_VERIFY' if verify else ''}.xlsx"
    write_review_workbook(review_path, summary_rows, rule_table, issues_after, fixes, causes, notes, mfr_rows)
    print_summary(month_year, len(df), reporting, liability, rule_table, fixes, causes, notes, mfr_rows, refs,
                  review_path, report_path, marked, ready)
    return {"ready": ready, "difference": diff, "issues": issues_after, "fixes": fixes, "review_path": review_path}


if __name__ == "__main__":
    from pipeline import get_month_year

    parser = argparse.ArgumentParser(description="Review (and auto-fix) a generated TP-1-IL report.")
    parser.add_argument("--month_delta", "-md", type=int, default=1, help="How many months back (default: %(default)s)")
    parser.add_argument("--month_year", "-m", type=str, default=None, help="Explicit folder name, e.g. SEPTEMBER_2026")
    parser.add_argument("--no-fix", action="store_true", help="Analyze only; do not modify the report")
    parser.add_argument("--verify", action="store_true",
                        help="Re-check a report you fixed by hand: no auto-fixes, refreshes highlights, writes REVIEW_..._VERIFY.xlsx")
    parser.add_argument("--report", type=str, default=None, help="Path to the report file to review (default: the month's report)")
    args = parser.parse_args()

    month_year = args.month_year or get_month_year(args.month_delta)
    base = Path(privateConstants.BASE_PATH) / month_year
    review_report(str(base / privateConstants.DATA_DIRECTORY), str(base / privateConstants.REPORT_DIRECTORY), month_year, apply=not args.no_fix,
                  verify=args.verify, report_file=args.report)
