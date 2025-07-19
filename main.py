from pathlib import Path
from src.harmonie_file_handler import HarmonieFileHandler
from src.file_tracker import FileTracker
from src.knmi_api import OpenDataAPI
from src.logger_config import setup_logging, get_logger

import sys
from tqdm import tqdm
from datetime import datetime
import tarfile
import shutil
import os
import sqlite3

setup_logging()
logger = get_logger(__name__)

from dotenv import load_dotenv
load_dotenv()

def main():
    tracker = FileTracker()

    api_key = os.getenv("API_KEY")
    if api_key is None:
        logger.error("API_KEY environment variable not set.")
        sys.exit(1)
    
    dataset_name = "harmonie_arome_cy43_p2a"
    dataset_version = "1.0"
    logger.info(f"Fetching latest file of {dataset_name} version {dataset_version}")

    api = OpenDataAPI(api_token=api_key, dataset_name=dataset_name, dataset_version=dataset_version)

    # sort the files in descending order and only retrieve the first file
    params = {"maxKeys": 6, "orderBy": "created", "sorting": "desc"}
    
    response = api.list_files(params)
    if "error" in response:
        logger.error(f"Unable to retrieve list of files: {response['error']}")
        sys.exit(1)
    
    for file in response["files"]: 
        filename = file.get("filename")        
        last_modified_str = file.get("lastModified")
        last_modified_dt = datetime.strptime(last_modified_str, "%Y-%m-%dT%H:%M:%S%z")
        tracker.add_file_to_track(filename, last_modified_dt)
        

    list_of_files = [file["filename"] for file in response["files"]]
    files_to_download = tracker.filter_not_downloaded(list_of_files)
    if len(files_to_download) > 0:
        if os.environ.get("NON_INTERACTIVE", "0") == "1":
            inp = "y"
        else:
            inp = input(f"Found {len(files_to_download)} new files. Do you want to download and update forecast? (Y/N)")
        if inp.lower() == 'y':
            for file_name in tqdm(files_to_download, desc="Downloading files"):
                response = api.get_file_url(file_name)        
                file_path = api.download_file_from_temporary_download_url(response["temporaryDownloadUrl"], file_name)
                tracker.mark_file_as_downloaded(file_name, str(file_path))
            logger.info(f"Downloaded {len(files_to_download)} files")
            
            files_to_unpack = tracker.filter_not_unpacked(list_of_files)
            for file_name in tqdm(files_to_unpack, desc="Unpacking files"):
                if file_name.endswith(".tar"):   
                    path =  Path('data') / file_name  
                    unapacked_folder = path.with_suffix('')
                    unapacked_folder.mkdir(parents=True, exist_ok=False)              
                    with tarfile.open(path) as tar:
                        tar.extractall(path=unapacked_folder, filter="data")

                    tracker.mark_file_as_unpacked(file_name, str(unapacked_folder))
                    path.unlink()            
            logger.info(f"Unpacked {len(files_to_download)} files")


            # Retrieve older files and delete them
            older_files = tracker.get_older_available_files()
            for file in older_files:
                path = Path(str(file.unpacked_location))
                
                if path.exists():
                    shutil.rmtree(path)
                    
                tracker.mark_file_as_removed(file.filename)

            logger.info(f"Deleted {len(older_files)} files") 
            tracker.close_session()

            handler = HarmonieFileHandler()
            handler.process_all_folders()

        else:
            logger.info("Keeping old files")
    else:
        logger.info("No new files to download")


    conn = sqlite3.connect(Path('data') / 'netcdf_tracker.db')
    c = conn.cursor()
    c.execute("SELECT filename FROM netcdf_files WHERE removed = FALSE ORDER BY created_at DESC LIMIT 1")
    latest_file = c.fetchone()
    conn.close()    
    if latest_file:
        logger.info("Setting environment variable NETCDF_PATH to the latest file")
        name = str(Path('data') / latest_file[0])        
        os.environ['NETCDF_PATH'] = name
    else:
        logger.info("Creating new NetCDF file as no files found in database")
        handler = HarmonieFileHandler()
        handler.process_all_folders()

        c = conn.cursor()
        c.execute("SELECT filename FROM netcdf_files WHERE removed = FALSE ORDER BY created_at DESC LIMIT 1")
        latest_file = c.fetchone()
        conn.close()
        name = str(Path('data') / latest_file[0])        
        os.environ['NETCDF_PATH'] = name
        # logger.warning("No NetCDF files found in database")
        # sys.exit(1)

    from src.dashboard import app
    logger.info("Starting dashboard")
    app.run(debug=False)
    

if __name__ == "__main__":
    main()