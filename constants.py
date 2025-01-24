DATA_PATH = "test_data"
AGGREGATED_BOOK = f"{DATA_PATH}/aggregated_book.xlsx"

INVOICE_DATA_FILE_NAME = f"{DATA_PATH}/file2.xlsm"
INVOICE_SHEET_NAME = "Sheet1"
AGGREGATED_BOOK_INVOICE_SHEET_NAME = "Invoices"

CUSTOMER_DATA_FILE_NAME = f"{DATA_PATH}/CUST.xlsx"
CUSTOMER_SHEET_NAME = "Sheet1"
AGGREGATED_BOOK_CUSTOMER_SHEET_NAME = "Customers"

PRODUCT_DATA_FILE_NAME = f"{DATA_PATH}/TEST_DATA.xlsx"
PRODUCT_SHEET_NAME = "Sheet1"
AGGREGATED_BOOK_PRODUCT_SHEET_NAME = "Products"

SCHEDULE_CODE = "2C"
TYPE_OF_CUSTOMER = "Retailer"
DOCUMENT_TYPE = "Invoice"

SCHEDULE_CODES = {
    'Retailer' : '2C',
    'Wholesaler' : '2B',
    'Distributor' : '2B'
}

TP_1_IL_STRUCTURE = [
    "Schedule Code",
    "Document Date",
    "Document Type",
    "Document Number",
    "Type of Customer",
    "Name",
    "Street Address",
    "City",
    "State",
    "Country",
    "Zip",
    "Customer FEIN",
    "Customer ID",
    "Fed Description",
    "State Description",
    "MSA Status",
    "Price",
    "Tax Jurisdiction",
    "UPC Number",
    "UPCs Unit of Measure",
    "Product Description",
    "Manufacturer",
    "Brand Family",
    "Unit",
    "Unit Description",
    "Weight/Volume",
    "Value",
    "Quantity"
]