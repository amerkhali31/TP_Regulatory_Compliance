import os
import argparse
from privateConstants import BASE_PATH as base, DATA_DIRECTORY as data_directory, REPORT_DIRECTORY as report_directory

def create_folder(folder_name:str) -> None :

    """
    Creates a folder in the specified directory.
    
    :param directory: The path where the folder should be created.
    :param folder_name: The name of the folder to create.
    """

    folder_path = os.path.join(base, folder_name.upper())
    data_path = os.path.join(folder_path, data_directory)
    report_path = os.path.join(folder_path, report_directory)

    try:
        os.makedirs(folder_path, exist_ok=True)  # Create folder (does nothing if it exists)
        os.makedirs(data_path, exist_ok=True)
        os.makedirs(report_path, exist_ok=True)
        print(f"Folder '{folder_name}' created at: {folder_path}")

    except Exception as e: print(f"Error creating folder: {e}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Create a folder in the specified directory.")
    parser.add_argument("folder_name", type=str, help="Name of the folder to create")
    args = parser.parse_args()
    
    create_folder(args.folder_name)
