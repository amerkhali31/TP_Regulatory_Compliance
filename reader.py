import constants
import privateConstants
import pandas as pd
import numpy as np
from utils.excel_utils import mergeBooks, read_sheet, merge_sheets
import re
import os

# Choose which columns to read out of the quickbooks generated excel report
invoice_columns_to_use = "Date Num Memo Name Qty Amount Item".split() + ["Sales Price"]
prod_cols_to_use = "Item Description U/M Price UPC FED_DESCRIPTION BRAND UNIT".split() + ["UNIT DESCRIPTION"]
cust_cols_to_use = ["Customer", "FEIN", "LICENSE", "Bill to 1", "Bill to 2", "Customer Type", "Sales Tax Code"]


# Read The Excel Report into Pandas DataFrames
inv = read_sheet(privateConstants.INVOICE_DATA_FILE_NAME, privateConstants.INVOICE_SHEET_NAME, invoice_columns_to_use)
cust = read_sheet(privateConstants.CUSTOMER_DATA_FILE_NAME, privateConstants.CUSTOMER_SHEET_NAME, cust_cols_to_use)
prod = read_sheet(privateConstants.PRODUCT_DATA_FILE_NAME, privateConstants.PRODUCT_SHEET_NAME, prod_cols_to_use)

print(f'Inv Initial: {inv.shape}')

# Prepare DF's for merge
inv['Item'] = inv['Item'].str.replace(r'\(.*\)', '', regex=True).str.strip()
inv.rename(columns={'Name' : 'Customer'}, inplace=True)  # Match Invoice DF Customer's Name column header to Customer DF Customer's Name column header to merge on that column

inv.dropna(subset=['Num'], inplace=True)  # Get rid of all rows of invoices where num is na because invoices will be the correct length of the final df

prod['UNIT'] = prod['UNIT'].apply(lambda x: int(re.sub(r'\D', '', str(x))) if pd.notna(x) and re.sub(r'\D', '', str(x)) else 0)
prod_filtered = prod  # prod[prod['Sales Tax Code'] == 'Tax']

# Merge the DF's
print(f'Inv: {inv.shape}')

merge1 = pd.merge(inv, prod_filtered, on='Item')
print(f'Merge1: {merge1.shape}')

merge2 = pd.merge(merge1, cust, on='Customer')
print(f'Merge2: {merge2.shape}')


# Process The Data
merge2['FED_DESCRIPTION'] = merge2['FED_DESCRIPTION'].fillna('')
merge2['BRAND'] = merge2['BRAND'].fillna('')
merge2['UNIT'] =  merge2['UNIT'].fillna(0)
merge2['FED_DESCRIPTION'] = merge2['FED_DESCRIPTION'].replace({'VAPOR': 'VAPOR PRODUCT'}).str.strip()

condition2 = merge2['BRAND'].apply(
    lambda x: any(brand.lower() in x.lower() for brand in constants.MS_BRANDS) if isinstance(x, str) else False
)
conditions = [
    merge2['FED_DESCRIPTION'].isin(['E-liquid Product', 'VAPOR PRODUCT']),
    condition2
]
choices = ['IL-ECIG', 'IL-MS']

# Build th New DataFrame
df = pd.DataFrame(columns=constants.TP_1_IL_STRUCTURE)


# Temporary Series
df["Temp_Price"] = merge2["Sales Price"]
df["Temp_Unit"] = merge2["UNIT"]

# Populate the New DataFrame
df["Schedule Code"] = merge2['Customer Type'].map(constants.SCHEDULE_CODES)
df["Document Date"] = merge2['Date'].dt.strftime('%m-%d-%Y')
df["Document Type"] = constants.DOCUMENT_TYPE
df["Document Number"] = merge2['Num']
df["Type of Customer"] = merge2['Customer Type'].replace({'Retail': 'Retailer'})
df["Name"] = merge2['Customer']
df["Street Address"] = merge2['Bill to 1']
df["City"] = merge2['Bill to 2'].apply(lambda x: x.split(',')[0] if isinstance(x, str) and ',' in x else None)
df["State"] = merge2['Bill to 2'].apply(lambda x: x.split(',')[1].strip().split(' ')[0] if isinstance(x, str) and ',' in x else None)
df["Country"] = constants.COUNTRY
df["Zip"] = merge2['Bill to 2'].apply(lambda x: x.split(',')[1].strip().split(' ')[1] if isinstance(x, str) and ',' in x and len(x.split(',')) > 1 and len(x.split(',')[1].strip().split(' ')) > 1 else None)
df["Customer FEIN"] = merge2['FEIN'].apply(lambda x: re.sub(r'[^0-9]', '', str(x)) if pd.notna(x) and str(x).strip() else '999999999')
df["Customer ID"] = merge2['LICENSE'].apply(lambda x: re.sub(r'[^a-zA-Z0-9]', '', str(x)) if pd.notna(x) and str(x).strip() else 'CT99999')
df["Fed Description"] = merge2['FED_DESCRIPTION']
df["State Description"] = np.select(conditions, choices, default='IL-OTP')
df["MSA Status"] = constants.MSA_STATUS
df["Price"] = ""
df["Tax Jurisdiction"] = merge2['Sales Tax Code'].replace("Tax", "IL")
df["UPC Number"] = merge2['UPC']
df["UPCs Unit of Measure"] = merge2['U/M'].apply(lambda x: re.search(r'\((.*?)\)', str(x)).group(1) if pd.notna(x) and re.search(r'\((.*?)\)', str(x)) else 'BOX')
df["Product Description"] = merge2['Description']
df["Brand Family"] = merge2['BRAND']
df["Unit"] = merge2['UNIT']
df["Unit Description"] = merge2['UNIT DESCRIPTION']
df["Weight/Volume"] = np.where(df['State Description'] == 'IL-MS', '1', '')
df["Value"] = np.where(df['State Description'] != 'IL-MS', df['Temp_Price'], 0)
df["Quantity"] = merge2['Qty']

# In Progress
df['Manufacturer'] = merge2['BRAND'].apply(lambda x: constants.MANUFACTURERS.get(x, 'N/A'))
df["Manufacturer EIN"] = "999999999"  # TODO - create map for manufacturer EINs to manufacturers

# Post Process
filtered_df = df[(df['Unit'] != 0)].sort_values(by='Document Number')
filtered_df['Unit'] = 1
filtered_df.drop(['Temp_Price', 'Temp_Unit'], axis=1, inplace=True)

print(f'Final: {filtered_df.shape}')

# Convert Data to Excel Sheet
output_path_report_excel = os.path.join(privateConstants.WRITE_PATH, "TP_1_IL_Report.xlsx")
output_path_report_csv = os.path.join(privateConstants.WRITE_PATH, "TP_1_IL_Report.csv")

filtered_df.to_excel(output_path_report_excel, index=False)
filtered_df.to_csv(output_path_report_csv, index=False, header=False)

# Find rows where 'Num' is NaN before dropping them
output_path_report_inv = os.path.join(privateConstants.WRITE_PATH, "missing_due_to_invoice_filter.xlsx")
missing_due_to_invoice_filter = inv[inv['Num'].isna()]
missing_due_to_invoice_filter.to_excel(output_path_report_inv, index=False)


# Find missing invoices after merge1 (missing Items)
output_path_report_merge1 = os.path.join(privateConstants.WRITE_PATH, "missing_after_merge1.xlsx")
missing_after_merge1 = inv[~inv['Item'].isin(prod['Item'])]
missing_after_merge1.to_excel(output_path_report_merge1, index=False)

# Find missing invoices after merge2 (missing Customers)
output_path_report_merge2 = os.path.join(privateConstants.WRITE_PATH, "missing_after_merge2.xlsx")
missing_after_merge2 = merge1[~merge1['Customer'].isin(cust['Customer'])]
missing_after_merge2.to_excel(output_path_report_merge2, index=False)

# Find missing invoices after filtering (Unit == 0)
output_path_report_final = os.path.join(privateConstants.WRITE_PATH, "missing_after_filtering.xlsx")
missing_after_filtering = merge2[merge2["UNIT"] == 0]
missing_after_filtering.to_excel(output_path_report_final, index=False)

print(f"Missing due to invoice filter: {missing_due_to_invoice_filter.shape[0]}")
print(f"Missing after first merge: {missing_after_merge1.shape[0]}")
print(f"Missing after second merge: {missing_after_merge2.shape[0]}")
print(f"Missing after filtering: {missing_after_filtering.shape[0]}")
