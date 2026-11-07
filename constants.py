MSA_STATUS = "N/A"
SCHEDULE_CODE = "2C"
TYPE_OF_CUSTOMER = "Retailer"
DOCUMENT_TYPE = "Invoice"
COUNTRY = 'USA'
SCHEDULE_CODES = {
    'Retail' : '2C',
    'Retailer': '2C',
    'Wholesale': '2B',
    'Wholesaler' : '2B',
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
    '4KING' : 'GOOD TIMES USA LLC',
    'ALCAPONE' : 'ICC INTER-CONTINENTAL CIGAR CORP',
    'AYADE CIGARS' : 'AYADE CIGARS LLC',
    'BACKWOOD' : 'ITG BRANDS LLC',
    'BACKWOODS': 'ITG BRANDS LLC',
    'BLACK JACK' : 'J.C. NEWMAN CIGAR CO',
    'BLACK& MIL' : 'JOHN MIDDLETON COMPANY',
    'BLACK & MILD' : 'JOHN MIDDLETON COMPANY',
    'BLACK& MILD' : 'JOHN MIDDLETON COMPANY',
    'BLACK&MILD' : 'JOHN MIDDLETON COMPANY',
    'BUGLER' : 'SCANDINAVIAN TOBACCO GROUP LANE LTD',
    'DUTCH' : 'ITG BRANDS LLC',
    'GAME' : 'SMCI HOLDING INC',
    'GARCIA VEGA' : 'SMCI HOLDING INC',
    'GOLDEN HARVEST' : 'ROUSECO',
    'GOOD STUFF' : 'PRIVATEER TOBACCO COMAPNY INC',
    'GOOD TIMES' : 'GOOD TIMES USA LLC',
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
    'SWISHER SWEET': 'SWISHER SWEETS CIGAR COMPANY',
    'WHITE OWL' : 'SMCI HOLDING INC',
    'BREEZE' : 'BREEZE SMOKE LLC',
    'FRONTO LEAF' : 'THE ORIGINAL FRONTO LEAF LLC',
    'GEEK' : 'SHENZHEN GEEKVAPE TECHNOLOGY CO LTD',
    'GEEK BAR': 'SHENZHEN GEEKVAPE TECHNOLOGY CO LTD',
    'GRABBA LEAF' : 'GRABBALEAF LLC',
    'GRABA' : 'GRABBALEAF LLC',
    'HAVANA' : 'HAVANA LEAF LLC',
    'GAMBLER': 'REPUBLIC BRANDS',
    'AMERICAN SNUFF CO' : 'AMERICAN SNUFF CO',
    'TOP' : 'REPUBLIC BRANDS',
    'SNOOP DOGG': 'SWED',
    'RED MAN': 'PINKERTON TOBACCO CO LP',
    'THROWBACK': 'ROOTS LEAF CIGARS CO.',
    'TROWBACK': 'ROOTS LEAF CIGARS CO.',
    'BLACK SMOOTH': 'GOOD TIMES LLC',
}

MANUFACTURER_EINS = {"Swisher"}

# ================================================================
# Report review rules (see report_rules.md / report_common_errors.md)
# ================================================================

# Rule 3
VALID_FED_DESCRIPTIONS = {
    'ROLL YOUR OWN', 'LARGE CIGAR', 'OTHER', 'VAPOR PRODUCT', 'CHEWING TOBACCO', 'PIPE TOBACCO',
    'SMALL CIGAR', 'SNUFF', 'ALTERNATIVE NICOTINE PRODUCT', 'E-LIQUID PRODUCT',
}
# Rule 4
VALID_UPC_UNITS_OF_MEASURE = {
    'PAK', 'STK', 'BOX', 'ECH', 'BAG', 'TIN', 'FOI', 'CAN', 'BUL', 'TUB', 'PCH', 'BUN', 'PLG', 'CUT', 'BOT', 'JAR', 'OTH',
}
# Rule 5
VALID_UNIT_DESCRIPTIONS = {
    'PAK', 'STK', 'BOX', 'ECH', 'BAG', 'TIN', 'FOI', 'CAN', 'BUL', 'TUB', 'PCH', 'BUN', 'PLG', 'CUT', 'BOT', 'JAR', 'OTH',
}
VALID_STATE_DESCRIPTIONS = {'IL-OTP', 'IL-MS', 'IL-ECIG'}
VALID_MSA_STATUSES = {'OPM', 'NPM', 'SPM', 'N/A', 'PM', 'NPM1', 'NPM2', 'NSM'}

# Rule 1 - columns allowed to be blank
OPTIONAL_COLUMNS = {'Price', 'Weight/Volume'}

# Rule 6
UPC_MIN_LEN = 12
UPC_MAX_LEN = 20

# Rule 8 - filler values that are never legitimate (compared after stripping punctuation)
FILLER_FEINS = {'999999999', '000000000', '123456789', '111111111'}
FILLER_CUSTOMER_IDS = {'CT99999', 'TP99999', 'CT00000', 'TP00000', 'NA', 'NONE'}
CUSTOMER_ID_PATTERN = r'^(CT|TP)\d{5}$'

# Tax Jurisdiction: codes that are rewritten automatically, and codes accepted without a warning.
# CKC is always translated to IL; CHC is a legitimate jurisdiction and is left as-is.
TAX_JURISDICTION_FIXES = {'CKC': 'IL', 'Tax': 'IL'}
VALID_TAX_JURISDICTIONS = {'IL', 'CHC'}

# Schedule code <-> type of customer (IDOR instructions)
SCHEDULE_CUSTOMER_TYPES = {
    '2B': {'DISTRIBUTOR', 'SUBJOBBER', 'WHOLESALER', 'NATIVE AMERICAN', 'MILITARY', 'GOVERNMENT',
           'INTERBRANCH TRANSFER', 'DISTRIBUTION CENTER'},
    '2C': {'RETAILER', 'EMPLOYEE', 'CUSTOMER', 'DELIVERY SELLER', 'NATIVE AMERICAN', 'MILITARY', 'GOVERNMENT'},
}

# Manufacturer auto-assignment: brand-name fuzzy matches below this score are only suggested, never applied.
# Kept high on purpose - e.g. 'BASS LEAF' vs 'GRABBA LEAF' scores 0.70 and is the wrong company.
MANUFACTURER_FUZZY_CUTOFF = 0.85
