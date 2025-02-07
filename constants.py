DATA_PATH = "test_data"
AGGREGATED_BOOK = f"{DATA_PATH}/aggregated_book.xlsx"

INVOICE_DATA_FILE_NAME = f"{DATA_PATH}/JANUARY_INVOICES.xlsx"
INVOICE_SHEET_NAME = "Sheet1"
AGGREGATED_BOOK_INVOICE_SHEET_NAME = "Invoices"

CUSTOMER_DATA_FILE_NAME = f"{DATA_PATH}/JANUARY_CUSTOMERS.xlsx"
CUSTOMER_SHEET_NAME = "Sheet1"
AGGREGATED_BOOK_CUSTOMER_SHEET_NAME = "Customers"

PRODUCT_DATA_FILE_NAME = f"{DATA_PATH}/JANUARY_PRODUCTS.xlsx"
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
    'Swisher' : 'Swish Manu',
    '4KING' : 'GOOD TIMES USA LLC',
    'ALCAPONE' : 'ICC INTER-CONTINENTAL CIGAR CORP',
    'THROWBACK' : 'AYADE CIGARS LLC',
    'AYADE CIGARS' : 'AYADE CIGARS LLC',
    'BACKWOOD' : 'ITG BRANDS LLC',
    'BLACK JACK' : 'J.C. NEWMAN CIGAR CO',
    'BLACK& MIL' : 'JOHN MIDDLETON COMPANY',
    'BLACK& MILD' : 'JOHN MIDDLETON COMPANY',
    'BLACK&MILD' : 'JOHN MIDDLETON COMPANY',
    'BUGLER' : 'SCANDINAVIAN TOBACCO GROUP LANE LTD',
    'DUTCH' : 'ITG BRANDS LLC',
    'GAME' : 'SMCI HOLDING INC',
    'GARCIA VEGA' : 'SMCI HOLDING INC',
    'GOLDEN HARVEST' : 'ROUSECO',
    'GOOD STUFF' : 'PRIVATEER TOBACCO COMAPNY INC',
    'GOOD TIME' : 'GOOD TIMES USA LLC',
    'GOOD TIME CITY LIFE' : 'GOOD TIMES USA LLC',
    'KING' : 'GOOD TIMES USA LLC',
    'KITE' : 'SCANDINAVIAN TOBACCO GROUP LANE LTD',
    'KODIAK' : 'AMERICAN SNUFF CO LLC',
    'LOOSE LEAF' : 'LOOSELEAF INTERNATIONAL',
    'MR FOG' : 'DONGGUAN HT TECHNOLOGY CO LTD',
    'POSH' : 'SHENZEN HIYUE TECHNOLOGY',
    'SHOW' : 'SHOW CIGARS INC',
    'SWISHER' : 'SWISHER SWEETS CIGAR COMPANY',
    'WHITE OWL' : 'SMCI HOLDING INC',
}

MANUFACTURER_EINS = {"Swisher"}