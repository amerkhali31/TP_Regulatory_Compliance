import constants
import pandas as pd
from utils.excel_utils import mergeBooks, read_sheet, merge_sheets

# Set Up the Columns I want to read from
invoice_columns_to_use = "Name Item Qty Amount Balance Num Memo Date".split() + ["Sales Price"]
prod_cols_to_use = "Item Description Price UPC".split() + ["Sales Tax Code"]
cust_cols_to_use = ["Customer", "Tax item", "Bill to 1", "Bill to 2", "Bill to 3", "Bill to 4", "Bill to 5",
                     "Ship to 1", "Ship to 2", "Ship to 3", "Ship to 4", "Ship to 5"]

# Read The Data
inv = read_sheet(constants.INVOICE_DATA_FILE_NAME, constants.INVOICE_SHEET_NAME, invoice_columns_to_use)
cust = read_sheet(constants.CUSTOMER_DATA_FILE_NAME, constants.CUSTOMER_SHEET_NAME, cust_cols_to_use)
prod = read_sheet(constants.PRODUCT_DATA_FILE_NAME, constants.PRODUCT_SHEET_NAME, prod_cols_to_use)

# Clean The Data
inv.rename(columns={'Name' : 'Customer'}, inplace=True)
inv.rename(columns={'Memo' : 'Description'}, inplace=True)
#print(inv)
# Compile The Data
merge1 = pd.merge(inv, prod, on='Description')
merge2 = pd.merge(merge1, cust, on='Customer')
print(merge2)

#
df = pd.DataFrame(columns=constants.TP_1_IL_STRUCTURE)
print(df.columns)



'''


import pandas as pd
import numpy as np
from numpy.random import randn

Series
similar to numpy array but has labels so it can be indexed by labels
labeled index and data point is the main take away. Wont be using these very much standalone but will use df which is heavy on this

labels = ['a','b','c']
my_data = [1,2,3]
arr = np.array(my_data)
my_dict = {'a': 1, 'b': 2, 'c': 3}

# index is not necassary but it is nice. will replace the index with your labels list so each row is indexed by custom index
a = pd.Series(data = my_data, index = labels)

# can pass in a numpy array instead of a list
b = pd.Series(arr, labels)

# can also pass in a dict. automatically make the keys the index
c = pd.Series(my_dict)

# how to index a series
a['a']

# basic operation. add the values together for each row. where data is missing from one of the two series, it will return null for that row
d = a + b

 Data Frames
dataframe: main tool working with pandas

np.random.seed(101)

# (data, row_labels, col_labels)
df = pd.DataFrame(randn(5,4), ['a','b','c','d','e'], ['w','x','y','z'])

# grab a column. returns a series
df['w']  # can also do df.w but not recommended in case your label has same name as a df method

# get multiple columns
df[['w','x']]

# create a column. can use operations here
df['new_column'] = df['w'] + df['y']

# remove a column. axis 0 is row, 1 is col. 0 is default. (x/0, y/1) axis gotten from df.shape which is a tuple
df.drop('new_column', axis = 1)  # does not happen in place unless you use inplace = True

# grab a row. takes in a label. returns a series
df.loc['a']

# numerical based index
df.iloc[2]

# row,col notation
df.loc['a','y']

df.loc[['a','b'],['w','y']]

# Conditional selection

booldf = df > 0  # returns the dataframe with true in all cells that meet the criteria and false where not
df[booldf] # returns the original dataframe with the normal values where true and NaN where false. would normally just do df[df<0]

# more realistic use case - filter series
df[df['w'] > 0]  # return the rows where the condition was met
df[df['w'] > 0]['x']  # can stack commands since what is returned is a df

# NOTE - Have to use &/| for comparison. do not use and/or

# reset index - resets index to a numerical value
df.reset_index()

states = 'il ab co ca nm'.split()
df['states'] = states

# If you have a column in your df that you want to be the index, you can use setindex.
df.set_index('states')


# index heirarchy
outside = 'g1 g1 g1 g2 g2 g2'.split()
inside = [1,2,3,1,2,3]
heir_index = list(zip(outside,inside))  # [('g1',1), ('g1',2), ...]
heir_index  = pd.MultiIndex.from_tuples(heir_index)

# multi level index
df = pd.DataFrame(randn(6,2), heir_index, ['a','b'])  # basically a dataframe inside of a dataframe
df.index.names = ['Groups','Num']  # add names to the indexes
#print(df)

df.loc['g2'].loc[2]['b']  # call from outside in


# cross section of dataframe
df.xs('g1')  # grab whole g1 group
df.xs(1,level='Num') # grab i ndex 1 from each group

'''

'''
d = {'a':[1,2,np.nan], 'b': [5,np.nan,np.nan], 'c': [3,4,5]}
df = pd.DataFrame(d)
#print(df)

df.dropna()  # will drop any row that has atleast 1 na value in it. can use axis=1 to do col instead of row
df.dropna(thresh=2)  # thresh is how many non na values needed for that series to not be dropped

df.fillna(value=999)  # choose what value to replace na with
df.fillna(value=df['a'].mean())  # standard is replace with mean of that series

Group By
allow you to group to group rows of data together to call aggregate functions like sql
group by allows you to group together rows based off of a column and perform some type of aggregate function on them
aggregate functions are functions that take in many inputs and return a single output


data = {'Company': ['GOOG', 'GOOG', 'MSFT', 'MSFT', 'FB', 'FB'],
        'Person': ['Sam', 'Charlie', 'Amy', 'Vanessa', 'Carl', 'Sarah'],
        'Sales': [200, 120, 340, 124, 243, 350]}

df = pd.DataFrame(data)

by_company = df.groupby('Company')  # returns a groupby object you can perform aggreate operations on
a = by_company.sum(numeric_only=True)  # returns a dataframe
df.groupby('Company').count()  # transpose, describe, max, min and more also availale.


Merging Joining and Concatenating 
pd.concat([df1, df2, df3...], axis=1)  to add glue dataframes to eachother. dimensions should match along axis you are concatenating on
pd.merge(df1, df2, how='inner', on='key')  # perform a join operation like sql. key is the column which you are merging on. can be list of keys.
df1.join(df2) will join df2 to df1 using only the df1 indeces. so i


Operations
df = pd.DataFrame({'col1': [1,2,3,4],
                   'col2': [444,555,666,444],
                   'col3': ['abc','def','ghi','xyz']})

df.head()  # retreive the first few rows. can specify as argument
df['col2'].unique()  # unique values. nunique is count of unique
df['col2'].value_counts()  # number of times each unique value shows up

def times2(x):
    return x*2
df['col1'].apply(times2)  # broadcasts your function to each element in the series
df['col1'].apply(lambda x: x*2)  # rewritten

df.columns  # returns list of column names. can also do index
df.sort_values('col2')  # sort. index stays attached to their row post sort
df.isnull()  # gets all null values


Data Input and Output
how to read data into/out of csv, excel, html, sql
instsall sqlalchemy, lxml, html5lib, BeautifulSoup4

df = pd.read_csv('example.csv')  # read_fileType works for many filetypes
df.to_csv('example.csv', index = False)  # has same options as read. index = false so it doesnt save index as a seperate column

# each sheet is a df
df = pd.read_excel('Exel_Sample.xlsx', sheetname='Sheet1')
df.to_excel('newBook.xlsx', sheet_name = 'new_sheet')

# SQL. pandas not really the best way to read sql. look for a driver for the sql library you want to use
from sqlalchemy import create_engine
engine = create_engine('sqlite:///:memory:')
df.to_sql('my_table', engine)
sqldf = pd.read_sql('my_table',engine)


# html
df = pd.read_html('https://www.fdic.gov/bank-failures/failed-bank-list')[0]
print(df.head())





'''