import pandas as pd

def mergeBooks(book1_name: str, book2_name: str, book3_name: str, sheet1_name: str, sheet2_name: str, sheet3_name: str) -> None:

    # Load specific sheets from the source Excel workbooks
    sheet1 = pd.read_excel(book1_name, sheet_name=sheet1_name)
    sheet2 = pd.read_excel(book2_name, sheet_name=sheet2_name)
    sheet3 = pd.read_excel(book3_name, sheet_name=sheet3_name)

    # Create a new Excel writer to save the combined sheets
    with pd.ExcelWriter("aggregated_book.xlsx", engine="openpyxl") as writer:
        # Write each sheet to the new workbook
        sheet1.to_excel(writer, sheet_name="Sheet1", index=False)
        sheet2.to_excel(writer, sheet_name="Sheet2", index=False)
        sheet3.to_excel(writer, sheet_name="Sheet3", index=False)
