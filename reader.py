import constants
import pandas as pd
import numpy as np
from utils.excel_utils import mergeBooks, read_sheet, merge_sheets

# Set Up the Columns I want to read from
invoice_columns_to_use = "Name Item Qty Amount Balance Num Memo Date".split() + ["Sales Price"]
prod_cols_to_use = "Item Description Price UPC".split() + ["FED DESCRIPTION", "BRAND", "UM", "Unit", "Unit Description"]
cust_cols_to_use = ["Customer", "Tax item", "Bill to 1", "Bill to 2", "Bill to 3", "Bill to 4", "Bill to 5", "Customer Type","License", "Customer FEIN", "Sales Tax Code"]

# Read The Data
inv = read_sheet(constants.INVOICE_DATA_FILE_NAME, constants.INVOICE_SHEET_NAME, invoice_columns_to_use)
cust = read_sheet(constants.CUSTOMER_DATA_FILE_NAME, constants.CUSTOMER_SHEET_NAME, cust_cols_to_use)
prod = read_sheet(constants.PRODUCT_DATA_FILE_NAME, constants.PRODUCT_SHEET_NAME, prod_cols_to_use)

# Prepare DF's for merge
inv.rename(columns={'Name' : 'Customer'}, inplace=True)
inv.rename(columns={'Memo' : 'Description'}, inplace=True)
inv.dropna(subset=['Num'], inplace=True)
cust['Customer Type'] = 'Retailer'

# Process The Data
merge1 = pd.merge(inv, prod, on='Description')
merge2 = pd.merge(merge1, cust, on='Customer')

merge2['FED DESCRIPTION'] = merge2['FED DESCRIPTION'].fillna('')
merge2['BRAND'] = merge2['BRAND'].fillna('')

condition2 = merge2['BRAND'].apply(
    lambda x: any(brand in x for brand in constants.MS_BRANDS) if isinstance(x, str) else False
)
conditions = [
    merge2['FED DESCRIPTION'].isin(['E-liquid Product', 'Vapor Products']),
    condition2
]
choices = ['ECIG', 'MS']
# Build th New DataFrame
df = pd.DataFrame(columns=constants.TP_1_IL_STRUCTURE)

# Populate the New DataFrame
df["Schedule Code"] = merge2['Customer Type'].map(constants.SCHEDULE_CODES)
df["Document Date"] = merge2['Date']
df["Document Type"] = constants.DOCUMENT_TYPE
df["Document Number"] = merge2['Num'].fillna(0).astype(int)
df["Type of Customer"] = merge2['Customer Type']
df["Name"] = merge2['Customer']
df["Street Address"] = merge2['Bill to 1']
df["City"] = merge2['Bill to 2'].apply(lambda x: x.split(',')[0] if isinstance(x, str) and ',' in x else None)
df["State"] = merge2['Bill to 2'].apply(lambda x: x.split(',')[1].strip().split(' ')[0] if isinstance(x, str) and ',' in x else None)
df["Country"] = constants.COUNTRY
df["Zip"] = merge2['Bill to 2'].apply(lambda x: x.split(',')[1].strip().split(' ')[1] if isinstance(x, str) and ',' in x and len(x.split(',')) > 1 and len(x.split(',')[1].strip().split(' ')) > 1 else None)
df["Customer FEIN"] = merge2['Customer FEIN']
df["Customer ID"] = merge2['License']
df["Fed Description"] = merge2['FED DESCRIPTION']
df["State Description"] = np.select(conditions, choices, default='OTP')
df["MSA Status"] = constants.MSA_STATUS
df["Price"] = "N/A"
df["Tax Jurisdiction"] = merge2['Sales Tax Code']
df["UPC Number"] = merge2['UPC']
df["UPCs Unit of Measure"] = merge2['UM']
df["Product Description"] = merge2['Description']
df["Brand Family"] = merge2['BRAND']
df["Unit"] = merge2['Unit']
df["Unit Description"] = merge2['Unit Description']

df["Weight/Volume"] = "TBD"
df["Value"] = "TBD"
df["Quantity"] = "TBD"
df["Manufacturer"] = "TBD"
df["Manufacturer EIN"] = "TBD"

print(df)