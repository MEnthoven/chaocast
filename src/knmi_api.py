import requests
from pathlib import Path

class OpenDataAPI:
    def __init__(self, api_token: str, dataset_name: str, dataset_version: str):
        url = "https://api.dataplatform.knmi.nl/open-data/v1"
        self.headers = {"Authorization": api_token}
        self.dataset_name = dataset_name
        self.dataset_version = dataset_version
        self.base_url = (
            f"{url}/datasets/{self.dataset_name}/versions/{self.dataset_version}/files"
        )
    def __get_data(self, url, params=None):        
        return requests.get(url, headers=self.headers, params=params).json()

    def list_files(self, params: dict):
        return self.__get_data(self.base_url,  params=params)

    def get_file_url(self, file_name: str):
        return self.__get_data(
            f"{self.base_url}/{file_name}/url"
        )

    def download_file_from_temporary_download_url(self, download_url, filename):
        try:
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()

                data_folder = Path("data")
                data_folder.mkdir(parents=True, exist_ok=True)
                file_path = data_folder / filename
                
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                return file_path
        except Exception:
            pass
