import os
import re
import shutil
from pathlib import Path
from typing import Iterable
from difflib import SequenceMatcher


def _normalize_filename(name: str) -> str:
    """
    Normalize a filename for comparison:
    - lowercase
    - remove extension
    - replace separators with spaces
    - collapse extra spaces
    """
    stem = Path(name).stem.lower()
    for ch in ["_", "-", ".", "(", ")", "[", "]"]:
        stem = stem.replace(ch, " ")
    return " ".join(stem.split())


def _similarity(a: str, b: str) -> float:
    """Return similarity score between 0 and 1."""
    return SequenceMatcher(None, a, b).ratio()


def fix_filenames_in_folder(
    basepath: str | Path,
    file_list: Iterable[str],
    cutoff: float = 0.75,
    rename: bool = True,
) -> dict:
    """
    Match files in `basepath` to expected names in `file_list`, allowing typos,
    and optionally rename them to the expected names.

    Parameters
    ----------
    basepath : str | Path
        Folder to search in.
    file_list : Iterable[str]
        Expected filenames, e.g.
        ['MARCH_2026_CUSTOMERS.xlsx', 'MARCH_2026_INVOICES.xlsx', ...]
    cutoff : float
        Minimum similarity score required for a fuzzy match.
        Higher = stricter. Good starting values: 0.70 to 0.85
    rename : bool
        If True, rename matched files on disk.

    Returns
    -------
    dict
        {
            "matched": [(old_name, new_name, score), ...],
            "unmatched_expected": [expected_name, ...],
            "unmatched_actual": [actual_name, ...],
            "skipped": [(actual_name, expected_name, reason), ...]
        }
    """
    basepath = Path(basepath)
    expected_files = [str(x) for x in file_list]

    actual_files = [p for p in basepath.iterdir() if p.is_file()]

    matched = []
    skipped = []
    unmatched_expected = []
    used_actual_paths = set()

    # First pass: exact name match
    actual_name_map = {p.name.lower(): p for p in actual_files}

    for expected in expected_files:
        expected_lower = expected.lower()
        if expected_lower in actual_name_map:
            p = actual_name_map[expected_lower]
            used_actual_paths.add(p)
            matched.append((p.name, expected, 1.0))
    
    # Second pass: fuzzy match the remaining expected files
    remaining_expected = [
        e for e in expected_files
        if all(e != new_name for _, new_name, _ in matched)
    ]
    remaining_actual = [p for p in actual_files if p not in used_actual_paths]

    for expected in remaining_expected:
        expected_norm = _normalize_filename(expected)

        best_path = None
        best_score = -1.0

        for actual in remaining_actual:
            if actual in used_actual_paths:
                continue

            # Compare normalized full names
            score = _similarity(expected_norm, _normalize_filename(actual.name))

            # Small boost if extension matches
            if actual.suffix.lower() == Path(expected).suffix.lower():
                score += 0.03

            if score > best_score:
                best_score = score
                best_path = actual

        if best_path is not None and best_score >= cutoff:
            target_path = basepath / expected

            if rename and best_path.name != expected:
                if target_path.exists():
                    skipped.append(
                        (best_path.name, expected, "target filename already exists")
                    )
                else:
                    best_path.rename(target_path)
                    matched.append((best_path.name, expected, round(best_score, 3)))
                    used_actual_paths.add(target_path)
            else:
                matched.append((best_path.name, expected, round(best_score, 3)))
                used_actual_paths.add(best_path)
        else:
            unmatched_expected.append(expected)

    # Build unmatched actual list
    matched_old_names = {old for old, _, _ in matched}
    unmatched_actual = [
        p.name for p in actual_files
        if p.name not in matched_old_names
    ]

    for old_name, new_name, score in matched:
        if old_name != new_name:
            print(f"Would rename: {old_name} -> {new_name} (score={score})")
        else:
            print(f'Didnt need to rename: {old_name}')


    return {
        "matched": matched,
        "unmatched_expected": unmatched_expected,
        "unmatched_actual": unmatched_actual,
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------------------------
# Locating the monthly exports in a messy folder (e.g. Downloads)
# ---------------------------------------------------------------------------------------------

_MONTHS = ["january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december"]


def _split_tokens(name: str) -> list[str]:
    """
    Break a filename into lowercase tokens regardless of delimiter style.
    'MARCH_2026_INVOICES (1).xlsx', 'march 2026 invoices.xlsx', 'MarchInvoices2026-final.xlsx'
    all become word/number tokens. Browser duplicate suffixes like ' (1)' / ' - Copy' are dropped.
    """
    stem = Path(name).stem
    stem = re.sub(r"\s*\(\d+\)\s*$", "", stem)                  # "name (1)"
    stem = re.sub(r"[\s_-]*copy(\s*\d+)?\s*$", "", stem, flags=re.I)  # "name - Copy"
    stem = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", stem)               # camelCase boundary
    stem = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", stem)  # letter<->digit boundary
    return [t for t in re.split(r"[^A-Za-z0-9]+", stem.lower()) if t]


def _month_of_token(tok: str) -> int | None:
    """Month number if the token is a month name, abbreviation or prefix (mar, sept, febr, MARCH)."""
    if tok.isalpha() and len(tok) >= 3:
        for i, m in enumerate(_MONTHS, 1):
            if m.startswith(tok):
                return i
    return None


def _kind_of_token(tok: str) -> str | None:
    """Which export type a token refers to (customers/invoices/products/tax/purchasing), tolerating abbreviations and typos."""
    if not tok.isalpha():
        return None
    if tok.startswith("custom") or tok in {"cust", "custs", "cstmr", "cstmrs"}:
        return "customers"
    if tok.startswith("invoi") or tok in {"inv", "invs", "invc", "invcs"}:
        return "invoices"
    if tok.startswith("product") or tok in {"prod", "prods", "item", "items"}:
        return "products"
    if tok.startswith("purchas") or tok in {"purch", "po", "pos"}:
        return "purchasing"
    if tok in {"tax", "taxes", "stax"}:
        return "tax"
    if len(tok) >= 5:  # typos like 'custmers', 'invoces', 'prodcts'
        for word, kind in (("customers", "customers"), ("invoices", "invoices"),
                           ("products", "products"), ("purchasing", "purchasing")):
            if _similarity(tok, word) >= 0.8:
                return kind
    return None


def _kind_of_filename(name: str) -> str | None:
    """Single export type for a filename, or None if it names none (or several, which is ambiguous)."""
    kinds = {k for k in map(_kind_of_token, _split_tokens(name)) if k}
    return kinds.pop() if len(kinds) == 1 else None


def _is_for_month(name: str, month: int, year: int) -> bool:
    """
    True if the filename's date refers to the given month and year. Understands:
    month names / abbreviations ('March 2026', 'mar_26', 'SEPT-2025'), numeric forms
    ('2026-03', '03-2026', '03_15_2026', '202603', '03-26'). A file with a different month, a
    different year, several different months, or no recognisable date at all is NOT a match.
    """
    toks = _split_tokens(name)
    year2 = year % 100

    def year_near(i: int, reach: int) -> bool:
        """4-digit year == target within `reach` tokens of i (2-digit year only directly adjacent)."""
        four = [(j, int(t)) for j, t in enumerate(toks) if len(t) == 4 and t.isdigit() and 2000 <= int(t) <= 2099]
        if four:  # an explicit 4-digit year must agree
            return any(y == year for j, y in four if abs(j - i) <= reach) or all(y == year for _, y in four)
        return any(0 <= j < len(toks) and len(toks[j]) == 2 and toks[j].isdigit() and int(toks[j]) == year2
                   for j in (i - 1, i + 1))

    named = [(i, m) for i, t in enumerate(toks) if (m := _month_of_token(t))]
    if named:
        if len({m for _, m in named}) > 1 or named[0][1] != month:
            return False
        return year_near(named[0][0], reach=2)

    # numeric dates
    for i, t in enumerate(toks):
        if len(t) == 6 and t.isdigit():  # 202603 or 032026
            if (int(t[:4]) == year and int(t[4:]) == month) or (int(t[2:]) == year and int(t[:2]) == month):
                return True
        if t.isdigit() and len(t) <= 2 and int(t) == month and year_near(i, reach=2) and any(len(x) == 4 and x.isdigit() and int(x) == year for x in toks):
            return True
    # 'mm-yy' (month directly followed by 2-digit year) - only when no 4-digit year exists
    if not any(len(t) == 4 and t.isdigit() for t in toks):
        for a, b in zip(toks, toks[1:]):
            if a.isdigit() and b.isdigit() and len(a) <= 2 and len(b) == 2 and int(a) == month and int(b) == year2:
                return True
    return False


def _month_year_parts(month_year: str) -> tuple[int, int]:
    """'MARCH_2026' -> (3, 2026)"""
    toks = _split_tokens(month_year)
    month = next((m for t in toks if (m := _month_of_token(t))), None)
    year = next((int(t) for t in toks if len(t) == 4 and t.isdigit()), None)
    if month is None or year is None:
        raise ValueError(f"Cannot read month/year from '{month_year}'")
    return month, year


def find_month_files(from_dir: str | Path, month_year: str, kinds: Iterable[str]) -> dict[str, list[Path]]:
    """
    Search `from_dir` for .xlsx exports belonging to `month_year`, keyed by kind.
    Candidates are sorted newest first (so 'name (1).xlsx' re-downloads beat older copies).
    """
    month, year = _month_year_parts(month_year)
    wanted = {k.lower() for k in kinds}
    found: dict[str, list[Path]] = {k: [] for k in wanted}
    for p in Path(from_dir).expanduser().iterdir():
        if not p.is_file() or p.suffix.lower() != ".xlsx" or p.name.startswith(("~$", ".")):
            continue
        kind = _kind_of_filename(p.name)
        if kind in wanted and _is_for_month(p.name, month, year):
            found[kind].append(p)
    for paths in found.values():
        paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


def move_files(from_dir: str | Path, to_dir: str | Path, files: list[str], month_year: str | None = None) -> dict[str, str]:
    """
    Move this month's exports from `from_dir` (Downloads) into `to_dir`, renamed to the expected names
    in `files`. A matching file in `from_dir` REPLACES whatever is already in `to_dir`; if there is
    no match, the existing copy in `to_dir` is kept. Only files whose name says they belong to
    `month_year` are used, so another month's export is never picked up.

    Returns {expected_name: 'moved' | 'replaced' | 'kept existing' | 'MISSING'}.
    """
    destination_dir = Path(to_dir).expanduser()
    destination_dir.mkdir(parents=True, exist_ok=True)

    if month_year is None:  # expected names look like '<MONTH_YEAR>_<KIND>.xlsx'
        month_year = "_".join(Path(files[0]).stem.split("_")[:2])
    kind_of = {f: Path(f).stem[len(month_year):].strip("_ ").lower() for f in files}
    found = find_month_files(from_dir, month_year, kind_of.values())

    results: dict[str, str] = {}
    for expected in files:
        candidates = found.get(kind_of[expected], [])
        destination = destination_dir / expected

        if not candidates:
            if destination.exists():
                results[expected] = "kept existing"
                print(f"No new {expected} in Downloads - using existing file in Current_Data")
            else:
                results[expected] = "MISSING"
                print(f"MISSING {expected}: not in Downloads and not in Current_Data")
            continue

        source = candidates[0]  # newest
        existed = destination.exists()
        staging = destination_dir / f".incoming_{expected}"
        shutil.move(str(source), str(staging))
        os.replace(staging, destination)  # atomic overwrite - old file survives if the move failed
        results[expected] = "replaced" if existed else "moved"
        print(f"{'Replaced' if existed else 'Moved'}: {source.name} -> {expected}")
        for extra in candidates[1:]:
            print(f"  (older match left in Downloads: {extra.name})")
    return results
