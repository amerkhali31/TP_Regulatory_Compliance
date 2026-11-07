import re
import pandas as pd

# "CHICAGO, IL 60643", "CHICAGO , IL 60643-1234", "CHICAGO IL 60651-2623" (no comma), "OAK LAWN,IL 60453"
_CITY_STATE_ZIP = re.compile(r"^\s*(?P<city>.+?)\s*,?\s+(?P<state>[A-Za-z]{2})\.?\s+(?P<zip>\d{5})(?:-?\d{4})?\s*$")


def _clean(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def parse_city_state_zip(bill_to_2) -> tuple[str, str, str]:
    """Parse a QuickBooks 'Bill to 2' line into (city, state, zip5). Missing parts come back as ''."""
    text = _clean(bill_to_2)
    if not text:
        return "", "", ""
    m = _CITY_STATE_ZIP.match(text)
    if m:
        return m.group("city").strip(" ,"), m.group("state").upper(), m.group("zip")
    # Partial fallback: grab whatever pieces are recognisable
    zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", text)
    city = text.split(",")[0].strip() if "," in text else ""
    state_match = re.search(r"\b([A-Z]{2})\b\s+\d{5}", text) or re.search(r",\s*([A-Za-z]{2})\.?\s*$", text)
    return city, state_match.group(1).upper() if state_match else "", zip_match.group(1) if zip_match else ""


def customer_city_state_zip(row) -> tuple[str, str, str]:
    """
    Best-effort (city, state, zip5) for one customer row.
    Prefers the dedicated City / State / Zip columns of the customer export (when present),
    falling back to parsing 'Bill to 2' for any piece that is missing.
    """
    p_city, p_state, p_zip = parse_city_state_zip(row.get("Bill to 2"))
    city = _clean(row.get("City")) or p_city
    state = _clean(row.get("State")).upper() or p_state
    zip_raw = _clean(row.get("Zip"))
    zip_match = re.match(r"(\d{5})", zip_raw.zfill(5) if zip_raw.isdigit() and len(zip_raw) == 4 else zip_raw)
    zip5 = zip_match.group(1) if zip_match else p_zip
    return city, state, zip5
