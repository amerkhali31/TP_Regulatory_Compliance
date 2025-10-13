import os
import argparse
from privateConstants import BASE_PATH as base, DATA_DIRECTORY as data_directory, REPORT_DIRECTORY as report_directory, MONTH_YEAR

def create_folder(folder_name: str) -> None:
    """
    Creates a folder in the specified directory.

    :param folder_name: The name of the folder to create.
    """
    folder_path = os.path.join(base, folder_name.upper())
    data_path = os.path.join(folder_path, data_directory)
    report_path = os.path.join(folder_path, report_directory)

    try:
        os.makedirs(folder_path, exist_ok=True)
        os.makedirs(data_path, exist_ok=True)
        os.makedirs(report_path, exist_ok=True)
        print(f"Folder '{folder_name}' created at: {folder_path}")
    except Exception as e:
        print(f"Error creating folder: {e}")

if __name__ == "__main__":

    '''
    To run this file, just enter python3 foldercreator.py into terminal when tp_1_il is working directory.
    Can add argument for the name to the command but leave blank to default to month year
    make sure to update month year in constants if you want to use that.
    '''
    parser = argparse.ArgumentParser(description="Create a folder in the specified directory.")
    parser.add_argument(
        "folder_name",
        type=str,
        nargs='?',
        default=MONTH_YEAR,
        help="Name of the folder to create (default: %(default)s)"
    )
    args = parser.parse_args()

    create_folder(args.folder_name)
