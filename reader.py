import constants
import pandas as pd
import numpy as np
from utils.excel_utils import mergeBooks, read_sheet, merge_sheets

# Make an aggregated book just to make viewing exceleasier during development
#mergeBooks(constants.INVOICE_DATA_FILE_NAME,constants.CUSTOMER_DATA_FILE_NAME,constants.PRODUCT_DATA_FILE_NAME,constants.INVOICE_SHEET_NAME,constants.CUSTOMER_SHEET_NAME,constants.PRODUCT_SHEET_NAME)


# Choose which columns to read out of the quickbooks generated excel report
invoice_columns_to_use = "Date Num Memo Name Qty Amount".split() + ["Sales Price"]
prod_cols_to_use = "Item Description U/M Price UPC FED_DESCRIPTION BRAND UNIT".split() + ["UNIT DESCRIPTION"]
cust_cols_to_use = "Customer FEIN LICENSE".split() + ["Bill to 1", "Bill to 2", "Sales Tax Code", "Customer Type"]

# Read The Excel Report into Pandas DataFrames
inv = read_sheet(constants.INVOICE_DATA_FILE_NAME, constants.INVOICE_SHEET_NAME, invoice_columns_to_use)
cust = read_sheet(constants.CUSTOMER_DATA_FILE_NAME, constants.CUSTOMER_SHEET_NAME, cust_cols_to_use)
prod = read_sheet(constants.PRODUCT_DATA_FILE_NAME, constants.PRODUCT_SHEET_NAME, prod_cols_to_use)

# Prepare DF's for merge
inv.rename(columns={'Name' : 'Customer'}, inplace=True)  # Match Invoice DF Customer's Name column header to Customer DF Customer's Name column header to merge on that column
inv.rename(columns={'Memo' : 'Description'}, inplace=True)  # Match Invoice DF Item's Name column header to Products DF Item's Name column header to merge on that column
inv.dropna(subset=['Num'], inplace=True)  # Get rid of all rows of invoices where num is na because invoices will be the correct length of the final df

# Process The Data
merge1 = pd.merge(inv, prod, on='Description')
merge2 = pd.merge(merge1, cust, on='Customer')

merge2['FED_DESCRIPTION'] = merge2['FED_DESCRIPTION'].fillna('')
merge2['BRAND'] = merge2['BRAND'].fillna('')

#print(f"Columns: {merge2.columns}")

condition2 = merge2['BRAND'].apply(
    lambda x: any(brand in x for brand in constants.MS_BRANDS) if isinstance(x, str) else False
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
df['Manufacturer'] = merge2['BRAND'].map(constants.MANUFACTURERS).fillna('Unknown Manufacturer')
df["Manufacturer EIN"] = "TBD"
df["Brand Family"] = merge2['BRAND']

# Complete
df["Unit"] = merge2["UNIT"]
df["Unit Description"] = merge2['UNIT DESCRIPTION']

# In Progress
df["Weight/Volume"] = np.where(df['State Description'] == 'MS', merge2['UNIT'], np.nan)
df["Value"] = np.where(df['State Description'] != 'MS', merge2['Price'] / merge2['UNIT'], np.nan) 
df["Quantity"] = merge2['Qty']

#df.drop(['Temp_Price', 'Temp_Unit'], axis=1, inplace=True)

# print(df[["Weight/Volume",
#           "Value",
#           "Quantity",
#           "Manufacturer",
#           "Manufacturer EIN",
#           "Unit",
#           "Unit Description",
#           'Brand Family',
#           'UPC Number',
#           'State Description',
#           'Document Number',
#           'Weight/Volume',
#          ]
#         ].head(10))
filtered_df = df[(df['Unit'].notna()) & (df['Customer FEIN'].notna()) & (df['City'].notna()) & (df['Customer ID'].notna()) & (df['Document Number'] == 6066)]
print(filtered_df[[
    'Name',
    'Product Description',
    'Manufacturer',
    'Manufacturer EIN',
    'Unit',
    'Weight/Volume',
    'Value',
    'Quantity',
    'Temp_Price'
]].head(50))
#df.to_excel('test_doc.xlsx', index=False)
