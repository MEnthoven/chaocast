import pygrib
from .logger_config import get_logger

from pathlib import Path
import xarray as xr
import re
from datetime import datetime, timedelta
from tqdm import tqdm
from src.file_tracker import FileTracker
from typing import Tuple, List, Optional
import sqlite3
import sqlite3
import sqlite3

class HarmonieFileHandler:
    def __init__(self, save_path: Path = Path('data')):
        self.parameter_mapping = {
            '11': 'temp',
            '181': 'prec'
        }
        self.save_path = save_path
        self.tracker = FileTracker()
        self.datasets = []
        self.logger = get_logger(__name__)
        self.__init_db()

    def __init_db(self):
        """Initialize SQLite database to track NetCDF files."""
        self.db_path = self.save_path / 'netcdf_tracker.db'
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS netcdf_files
                     (filename TEXT PRIMARY KEY, created_at TIMESTAMP, removed BOOLEAN DEFAULT FALSE)''')
        conn.commit()
        conn.close()

    def save_dataset(self, ds: xr.Dataset) -> None:
        """Save dataset to NetCDF file and update database."""
        filename = f"forecast-{datetime.now().strftime('%Y%m%d_%H%M')}.nc"
        ds.to_netcdf(
            self.save_path / filename,
            encoding={
                'temp': {'zlib': True, 'complevel': 5},
                'prec': {'zlib': True, 'complevel': 5}
            }
        )
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO netcdf_files VALUES (?, ?, ?)", (filename, datetime.now(), False))
        conn.commit()
        
        # Delete old files
        self.cleanup_old_files()
        conn.close()

    def cleanup_old_files(self):
        """Delete all but the most recent NetCDF file."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get all files except the most recent one
        c.execute("SELECT filename FROM netcdf_files WHERE removed = FALSE ORDER BY created_at DESC")
        files = c.fetchall()
        
        # Keep the most recent file, delete others
        for filename, in files[1:]:
            file_path = self.save_path / filename
            if file_path.exists():
                file_path.unlink()
                c.execute("UPDATE netcdf_files SET removed = TRUE WHERE filename = ?", (filename,))
            self.logger.info(f"Deleted file {filename}")
        
        conn.commit()
        conn.close()

    def parse_filename(self, filename: str) -> Optional[Tuple[int, datetime, datetime]]:
        """Parse HARMONIE filename to extract metadata."""
        match = re.match(r"harm43_v1_ned_uwcw_meteo_(\d{3})_(\d{8})(\d{4})_(\d{5})_GB", filename)
        
        if match:
            run_number = int(match.group(1))
            date = match.group(2)
            time = match.group(3)
            forecast_hours = int(match.group(4)) / 100

            date_obj = datetime.strptime(date, "%Y%m%d")
            time_obj = datetime.strptime(time, "%H%M").time()
            run_time = datetime.combine(date_obj, time_obj)
            valid_time = run_time + timedelta(hours=int(forecast_hours))

            return run_number, run_time, valid_time
        return None

    def grib2xr(self, file_path: Path) -> xr.Dataset:
        """Convert GRIB file to xarray Dataset."""
        with pygrib.open(str(file_path)) as grbs:
            prec = grbs.select(indicatorOfParameter=181)[0]
            T = grbs.select(indicatorOfParameter=11)[0]
            lats, lons = T.latlons()

            return xr.Dataset(
                {
                    'temp': (['lat', 'lon'], T.values - 273.15),
                    'prec': (['lat', 'lon'], prec.values)
                },
                coords={
                    'lat': lats[:, 0],
                    'lon': lons[0, :]
                }
            )

    def get_ensemble_numbers(self, directory: Path) -> List[str]:
        """Get unique ensemble numbers from HARMONIE GRIB files."""
        ensemble_numbers = set()
        pattern = r'harm43_v1_ned_uwcw_meteo_(\d{3})_'
        
        for file_path in directory.glob('*GB'):
            match = re.search(pattern, file_path.name)
            if match:
                ensemble_numbers.add(match.group(1))
        
        return sorted(list(ensemble_numbers))

    def load_folder(self, dir_path: Path, run_numbers: List[str], folder_index: int) -> xr.Dataset:
        """Load and process files from a folder."""
        datasets_run = []
        for number in tqdm(run_numbers, 'Ensemble numbers', position=1, leave=False):

            datasets_valid_time = []
            for file in dir_path.glob(f'harm43_v1_ned_uwcw_meteo_{number}_*GB'):
                run_number, run_time, valid_time = self.parse_filename(file.name)
                if valid_time < datetime.now():
                    continue


                if run_number == 0:
                    run_number_mod = 5
                else:
                    run_number_mod = run_number % 5
                
                run_number_mod = run_number_mod + folder_index * 6

                ds = self.grib2xr(file)            
                ds = ds.expand_dims({'valid_time': [valid_time], 'run_number': [run_number_mod]})

                datasets_valid_time.append(ds)


            ds = xr.concat(datasets_valid_time, dim='valid_time')
            datasets_run.append(ds)        

        return  xr.concat(datasets_run, dim='run_number')
    
    def compute_uncertainty(self, ds: xr.Dataset) -> xr.Dataset:
        """Compute uncertainty of the dataset."""
        return ds['temp'].max(dim=['run_number']) - ds['temp'].min(dim=['run_number'])

    def process_all_folders(self) -> xr.Dataset:
        """Process all available folders and combine datasets."""
        data = self.tracker.get_recent_available_files()
        datasets = []
        
        for i, folder in tqdm(enumerate(data), total=6, desc='Folders', position=0):
            path = Path(folder.unpacked_location)
            run_numbers = self.get_ensemble_numbers(path)
            ds = self.load_folder(path, run_numbers, i)
            datasets.append(ds)

        self.logger.info("Finished loading all folders")
        self.logger.info("Combining datasets into a single xarray Dataset")
        combined_ds = xr.concat(datasets, dim='run_number')
        
        self.logger.info("Sorting dataset by run_number")
        # combined_ds = combined_ds.sortby('run_number', ascending=True)

        self.logger.info("Computing precipitation difference")
        combined_ds['prec_diff'] = combined_ds['prec'].diff('valid_time')
        
        self.logger.info("Processed 6 folders into combined dataset")
        self.logger.info("Saving combined dataset to NetCDF format...")
        self.save_dataset(combined_ds)
        self.logger.info(f"Successfully saved dataset to {self.save_path}")
        return combined_ds


if __name__ == "__main__":
    handler = HarmonieFileHandler()
    ds = handler.process_all_folders()