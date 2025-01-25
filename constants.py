DATA_PATH = "test_data"
AGGREGATED_BOOK = f"{DATA_PATH}/aggregated_book.xlsx"

INVOICE_DATA_FILE_NAME = f"{DATA_PATH}/INVOICES.xlsx"
INVOICE_SHEET_NAME = "Sheet1"
AGGREGATED_BOOK_INVOICE_SHEET_NAME = "Invoices"

CUSTOMER_DATA_FILE_NAME = f"{DATA_PATH}/CUSTOMERS.xlsx"
CUSTOMER_SHEET_NAME = "Sheet1"
AGGREGATED_BOOK_CUSTOMER_SHEET_NAME = "Customers"

PRODUCT_DATA_FILE_NAME = f"{DATA_PATH}/PRODUCTS.xlsx"
PRODUCT_SHEET_NAME = "Sheet1"
AGGREGATED_BOOK_PRODUCT_SHEET_NAME = "Products"

MSA_STATUS = "N/A"
SCHEDULE_CODE = "2C"
TYPE_OF_CUSTOMER = "Retailer"
DOCUMENT_TYPE = "Invoice"
COUNTRY = 'USA'
SCHEDULE_CODES = {
    'Retail' : '2C',
    'Wholesale' : '2B',
    'Distributor' : '2B'
}
MS_BRANDS = [
    'Copenhagen',
    'Grizzly',
    'Kodiak',
    'Levi Garrett',
    'Skoal',
    'Hawken',
    'Stokers',
    'Beechnut',
    'Longhorn',
    'Red Man',
    'Souther Pride'
]

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
    "Manufacturer EIN",
    "Brand Family",
    "Unit",
    "Unit Description",
    "Weight/Volume",
    "Value",
    "Quantity"
]

MANUFACTURERS = {
    'Swisher' : 'Swish Manu'
}

MANUFACTURER_EINS = {"Swisher"}