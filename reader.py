import constants
import pandas as pd
import numpy as np
from utils.excel_utils import mergeBooks, read_sheet, merge_sheets
import re

# Make an aggregated book just to make viewing exceleasier during development
#mergeBooks(constants.INVOICE_DATA_FILE_NAME,constants.CUSTOMER_DATA_FILE_NAME,constants.PRODUCT_DATA_FILE_NAME,constants.INVOICE_SHEET_NAME,constants.CUSTOMER_SHEET_NAME,constants.PRODUCT_SHEET_NAME)


# Choose which columns to read out of the quickbooks generated excel report
invoice_columns_to_use = "Date Num Memo Name Qty Amount Item".split() + ["Sales Price"]
prod_cols_to_use = "Item Description U/M Price UPC FED_DESCRIPTION BRAND UNIT".split() + ["UNIT DESCRIPTION"]
cust_cols_to_use = "Customer FEIN LICENSE".split() + ["Bill to 1", "Bill to 2", "Sales Tax Code", "Customer Type"]


# Read The Excel Report into Pandas DataFrames
inv = read_sheet(constants.INVOICE_DATA_FILE_NAME, constants.INVOICE_SHEET_NAME, invoice_columns_to_use)
cust = read_sheet(constants.CUSTOMER_DATA_FILE_NAME, constants.CUSTOMER_SHEET_NAME, cust_cols_to_use)
prod = read_sheet(constants.PRODUCT_DATA_FILE_NAME, constants.PRODUCT_SHEET_NAME, prod_cols_to_use)


# Prepare DF's for merge
inv['Item'] = inv['Item'].str.replace(r'\(.*\)', '', regex=True).str.strip()
inv.rename(columns={'Name' : 'Customer'}, inplace=True)  # Match Invoice DF Customer's Name column header to Customer DF Customer's Name column header to merge on that column
inv.dropna(subset=['Num'], inplace=True)  # Get rid of all rows of invoices where num is na because invoices will be the correct length of the final df

prod['UNIT'] = prod['UNIT'].apply(lambda x: int(re.sub(r'\D', '', str(x))) if pd.notna(x) and re.sub(r'\D', '', str(x)) else 0)

# Merge the DF's
print(f'Inv: {inv.shape}')

merge1 = pd.merge(inv, prod, on='Item')
print(f'Merge1: {merge1.shape}')

merge2 = pd.merge(merge1, cust, on='Customer')
print(f'Merge2: {merge2.shape}')


# Process The Data
merge2['FED_DESCRIPTION'] = merge2['FED_DESCRIPTION'].fillna('')
merge2['BRAND'] = merge2['BRAND'].fillna('')
merge2['UNIT'] =  merge2['UNIT'].fillna(0)

condition2 = merge2['BRAND'].apply(
    lambda x: any(brand.lower() in x.lower() for brand in constants.MS_BRANDS) if isinstance(x, str) else False
)
conditions = [
    merge2['FED_DESCRIPTION'].isin(['E-liquid Product', 'Vapor Products']),
    condition2
]
choices = ['ECIG', 'MS']


# Build th New DataFrame
df = pd.DataFrame(columns=constants.TP_1_IL_STRUCTURE)


# Populate the New DataFrame
df["Schedule Code"] = merge2['Customer Type'].map(constants.SCHEDULE_CODES)
df["Document Date"] = merge2['Date'].dt.strftime('%m-%d-%Y')
df["Document Type"] = constants.DOCUMENT_TYPE
df["Document Number"] = merge2['Num']
df["Type of Customer"] = merge2['Customer Type']
df["Name"] = merge2['Customer']
df["Street Address"] = merge2['Bill to 1']
df["City"] = merge2['Bill to 2'].apply(lambda x: x.split(',')[0] if isinstance(x, str) and ',' in x else None)
df["State"] = merge2['Bill to 2'].apply(lambda x: x.split(',')[1].strip().split(' ')[0] if isinstance(x, str) and ',' in x else None)
df["Country"] = constants.COUNTRY
df["Zip"] = merge2['Bill to 2'].apply(lambda x: x.split(',')[1].strip().split(' ')[1] if isinstance(x, str) and ',' in x and len(x.split(',')) > 1 and len(x.split(',')[1].strip().split(' ')) > 1 else None)
df["Customer FEIN"] = merge2['FEIN']
df["Customer ID"] = merge2['LICENSE']
df["Fed Description"] = merge2['FED_DESCRIPTION']
df["State Description"] = np.select(conditions, choices, default='OTP')
df["MSA Status"] = constants.MSA_STATUS
df["Price"] = "N/A"
df["Tax Jurisdiction"] = merge2['Sales Tax Code']
df["UPC Number"] = merge2['UPC']
df["UPCs Unit of Measure"] = merge2['U/M']
df["Product Description"] = merge2['Description']

# Temporary Series
df["Temp_Price"] = merge2["Price"]
df["Temp_Unit"] = merge2["UNIT"]

# In Progress
df['Manufacturer'] = merge2['BRAND'].map(constants.MANUFACTURERS).fillna('N/A')  # TODO - create map for manufacturers to brands
df["Manufacturer EIN"] = "N/A"  # TODO - create map for manufacturer EINs to manufacturers


# Complete
df["Brand Family"] = merge2['BRAND']
df["Unit"] = merge2['UNIT']
df["Unit Description"] = merge2['UNIT DESCRIPTION']

# In Progress
df["Weight/Volume"] = np.where(df['State Description'] == 'MS', '1', '')
df["Value"] = np.where(df['State Description'] != 'MS', np.round(np.where(np.isinf(df['Temp_Price'] / df['Temp_Unit']), 0, df['Temp_Price'] / df['Temp_Unit']), 2), 0)
df["Quantity"] = merge2['Qty'] * merge2['UNIT']

#

filtered_df = df[(df['Unit'] != 0)].sort_values(by='Product Description')
filtered_df['Unit'] = 1
print(f'Filtered: {filtered_df.shape}')
print(filtered_df[[
    'Name',
    'Product Description',
    'Manufacturer',
    'Manufacturer EIN',
    'Unit',
    'Weight/Volume',
    'Value',
    'Quantity',
    'Temp_Price',
    'Temp_Unit',
    'Fed Description',
    'State Description',
]].head(7))

filtered_df.drop(['Temp_Price', 'Temp_Unit'], axis=1, inplace=True)
filtered_df.to_excel('TP_1_IL_Report_V1.xlsx', index=False)