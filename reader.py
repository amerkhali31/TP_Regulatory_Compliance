import constants
import pandas as pd
from utils.excel_utils import mergeBooks
#invoice_path = f'{constants.DATA_PATH}/{constants.CUSTOMER_DATA_FILE_NAME}'
#invoice_df = pd.read_excel(invoice_path, sheet_name=constants.INVOICE_SHEET_NAME)
#invoice_df.drop(columns=[col for col in invoice_df.columns if 'Unnamed' in col], inplace=True)

mergeBooks()
