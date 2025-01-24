import constants
import pandas as pd
from utils.excel_utils import mergeBooks, read_sheet, merge_sheets

# Set Up the Columns I want to read from
invoice_columns_to_use = "Name Item Qty Amount Balance Num Memo Date".split() + ["Sales Price"]
prod_cols_to_use = "Item Description Price UPC".split() + ["Sales Tax Code"]
cust_cols_to_use = ["Customer", "Tax item", "Bill to 1", "Bill to 2", "Bill to 3", "Bill to 4", "Bill to 5"] + ['Customer Type']

# Read The Data
inv = read_sheet(constants.INVOICE_DATA_FILE_NAME, constants.INVOICE_SHEET_NAME, invoice_columns_to_use)
cust = read_sheet(constants.CUSTOMER_DATA_FILE_NAME, constants.CUSTOMER_SHEET_NAME, cust_cols_to_use)
prod = read_sheet(constants.PRODUCT_DATA_FILE_NAME, constants.PRODUCT_SHEET_NAME, prod_cols_to_use)

# Clean The Data
inv.rename(columns={'Name' : 'Customer'}, inplace=True)
inv.rename(columns={'Memo' : 'Description'}, inplace=True)
cust['Customer Type'] = 'Retailer'

# Compile The Data
merge1 = pd.merge(inv, prod, on='Description')
merge2 = pd.merge(merge1, cust, on='Customer')

# Build th New DataFrame
df = pd.DataFrame(index=range(len(inv)), columns=constants.TP_1_IL_STRUCTURE)

# Populate the New DataFrame
df["Schedule Code"] = merge2['Customer Type'].map(constants.SCHEDULE_CODES)
df["Document Date"] = merge2['Date']
df["Document Type"] = constants.DOCUMENT_TYPE
df["Document Number"] = merge2['Num']
df["Type of Customer"] = merge2['Customer Type']
df["Name"] = merge2['Customer']
df["Street Address"]
df["City"]
df["State"]
df["Country"]
df["Zip"]
df["Customer FEIN"]
df["Customer ID"]
df["Fed Description"]
df["State Description"]
df["MSA Status"]
df["Price"]
df["Tax Jurisdiction"]
df["UPC Number"]
df["UPCs Unit of Measure"]
df["Product Description"]
df["Manufacturer"]
df["Brand Family"]
df["Unit"]
df["Unit Description"]
df["Weight/Volume"]
df["Value"]
df["Quantity"]
print(df.head(22))


# Upload the new DataFrame to Excel Document