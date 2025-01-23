import constants
import pandas as pd
from utils.excel_utils import mergeBooks, read_sheet, merge_sheets

inv = read_sheet(constants.INVOICE_DATA_FILE_NAME, constants.INVOICE_SHEET_NAME, ["Name", "Item", "Qty"])
#cust = read_sheet(constants.AGGREGATED_BOOK, constants.AGGREGATED_BOOK_CUSTOMER_SHEET_NAME)
#prod = read_sheet(constants.AGGREGATED_BOOK, constants.AGGREGATED_BOOK_PRODUCT_SHEET_NAME)

print(inv.head())
