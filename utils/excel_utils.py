import pandas as pd
import os
import constants
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

def clear_unnamed_columns(df: pd.DataFrame):
    df.drop(columns=[col for col in df.columns if 'Unnamed' in col], inplace=True)

def read_sheet(book_name: str, sheet_name: str, cols: list, dtypes: dict = {}, optional_cols: list = []) -> pd.DataFrame:
    """Read `cols` (required) plus any of `optional_cols` that exist in the sheet."""
    wanted = set(cols) | set(optional_cols)
    df = pd.read_excel(book_name, sheet_name=sheet_name, usecols=lambda c: c in wanted, dtype=dtypes)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{book_name} [{sheet_name}] is missing required columns: {missing}")
    clear_unnamed_columns(df)

    return df

def merge_sheets():
    '''
    Take the sheets in the aggregate book and make the report from it
    '''

    pass


def extract_liability(book_name: str, sheet_name: str, cell: str | None = None,
                      row_label: str = "TOTAL", col_label: str = "Taxable Sales") -> float:
    """
    Read the taxable-sales liability out of the QuickBooks sales tax report.

    The value is located by its labels (the `row_label` row, `col_label` column) rather than a
    fixed cell, because QuickBooks adds/removes tax item lines (e.g. the 'IL' line that appeared
    above 'IL TP TAX' in 2026) which shifts every cell. `cell` is only used as a fallback.
    """
    wb = load_workbook(book_name, data_only=True)  # data_only=True -> calculated values of formulas
    ws = wb[sheet_name]

    header_col = None
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.strip().lower() == col_label.lower():
                header_col = c.column
                break
        if header_col:
            break

    if header_col:
        for row in ws.iter_rows():
            first = next((c.value for c in row if c.value is not None), None)
            if isinstance(first, str) and first.strip().upper() == row_label.upper():
                value = ws.cell(row=row[0].row, column=header_col).value
                if isinstance(value, (int, float)):
                    return float(value)

    if cell:
        print(f"WARNING: could not find '{row_label}' / '{col_label}' in {book_name}; falling back to cell {cell}")
        return ws[cell].value  # type: ignore
    raise ValueError(f"Could not locate liability ('{row_label}' row, '{col_label}' column) in {book_name}")


def add_filters():
    pass


def autoresize_and_filter(book_name: str, sheet_name: str):
    wb = load_workbook(book_name)
    ws = wb[sheet_name]
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)  # type: ignore # get column letter

        for cell in col:
            if cell.value is not None:
                cell_length = len(str(cell.value))
                if cell_length > max_length:
                    max_length = cell_length

        adjusted_width = max_length + 2  # add some padding
        ws.column_dimensions[col_letter].width = adjusted_width

    # ============================
    # Add filters to all columns
    # ============================
    ws.auto_filter.ref = ws.dimensions  # automatically applies to the used range

    # Save workbook
    wb.save(book_name)

