import constants
import pandas as pd
from utils.excel_utils import mergeBooks, read_sheet, merge_sheets

invoice_columns_to_use = "Name Item Qty Amount Balance Num Date".split() + ["Sales Price"]
prod_cols_to_use = "Item Description Price UPC".split() + ["Sales Tax Code"]
cust_cols_to_use = ["Customer", "Tax item", "Bill to 1", "Bill to 2", "Bill to 3", "Bill to 4", "Bill to 5",
                     "Ship to 1", "Ship to 2", "Ship to 3", "Ship to 4", "Ship to 5"]
inv = read_sheet(constants.INVOICE_DATA_FILE_NAME, constants.INVOICE_SHEET_NAME, invoice_columns_to_use)
cust = read_sheet(constants.CUSTOMER_DATA_FILE_NAME, constants.CUSTOMER_SHEET_NAME, cust_cols_to_use)
prod = read_sheet(constants.PRODUCT_DATA_FILE_NAME, constants.PRODUCT_SHEET_NAME, prod_cols_to_use)

print(inv.head())
print()
print(cust.head())
print()
print(prod.head())
