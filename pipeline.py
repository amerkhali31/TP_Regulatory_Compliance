from datetime import datetime
from folder_creator import create_folder
import argparse
from dateutil.relativedelta import relativedelta
from pathlib import Path
from file_utils import fix_filenames_in_folder, move_files
import os
from reader import do_taxes
from report_review import review_report

def get_month_year(month_delta: int):

    '''
    Gets the name of the month and year for the month that is number of month_deltas behind the current month

    Args:
        - month_delta (int) - number of months back to grab. e.g. 1 means get previous month
            - Default 1 because nominal use case is to be doing last month's taxes

    Returns:
        - month_year (str) - All caps {name of month}_{year}
    '''

    today = datetime.today()
    last_month_date = today - relativedelta(months=month_delta)

    month_name = last_month_date.strftime("%B")
    year = last_month_date.year

    month_year = f'{month_name.upper()}_{year}'

    return month_year


if __name__ == '__main__':

    '''
    How to use:

    1: python -m pipeline
    2: if you want to do a different month, add -md <x> where <x> is just the number of months back you want to do taxes for
    '''

    #optional args to pass in cli incase you are not filing for the previous month
    parser = argparse.ArgumentParser(description="Control which month and which files.")
    parser.add_argument(
        "--month_delta",
        "-md",
        type=int,
        nargs='?',
        default=1,
        help="How many months back are you doing taxes for (default: %(default)s)"
    )
    args = parser.parse_args()

    # Get the name of the month and the year to create folder and find files
    month_year = get_month_year(args.month_delta)
    
    file_list = [
        f"{month_year}_CUSTOMERS.xlsx",
        f"{month_year}_INVOICES.xlsx",
        f"{month_year}_PRODUCTS.xlsx",
        f"{month_year}_TAX.xlsx",
        f"{month_year}_PURCHASING.xlsx",
    ]

    create_folder(month_year)

    # # new_file_names = fix_filenames_in_folder(basepath=Path('~/Downloads/').expanduser(),
    #                         file_list=file_list,
    #                         cutoff=0.85,
    #                         rename=True)
    
    move_files(Path('~/Downloads/').expanduser(),f'./Customers/dream/{month_year}/Current_Data',file_list, month_year)

    do_taxes(f'./Customers/dream/{month_year}/Current_Data', f'./Customers/dream/{month_year}/Reports', month_year)

    # Check every report rule, auto-fix known errors, explain any reporting/liability difference
    review_report(f'./Customers/dream/{month_year}/Current_Data', f'./Customers/dream/{month_year}/Reports', month_year)