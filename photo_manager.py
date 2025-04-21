import os
import logging
from datetime import datetime
import exifread
from typing import List, Tuple
from PIL import Image
from pathlib import Path

class PhotoManager:
    def __init__(self):
        self.photos: List[Tuple[str, datetime, int, str]] = []
        self.current_sort = "date"

    def load_photos(self, folder: str) -> None:
        try:
            self.photos.clear()
            supported_formats = ('.jpg', '.jpeg', '.png', '.gif')
            
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(supported_formats):
                        try:
                            file_path = os.path.join(root, file)
                            stats = os.stat(file_path)
                            modified_time = datetime.fromtimestamp(stats.st_mtime)
                            file_size = stats.st_size
                            location = self.get_photo_location(file_path)
                            self.photos.append((file_path, modified_time, file_size, location))
                        except Exception as e:
                            logging.warning(f"Error processing file {file}: {str(e)}")
                            continue
            
            self.sort_photos()
            logging.info(f"Loaded {len(self.photos)} photos")
        except Exception as e:
            logging.error(f"Error loading photos: {str(e)}")
            raise

    def get_photo_location(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f)
                if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
                    return f"{tags['GPS GPSLatitude']}, {tags['GPS GPSLongitude']}"
        except Exception as e:
            logging.debug(f"No GPS data for {file_path}: {str(e)}")
        return "Unknown"

    def sort_photos(self) -> None:
        try:
            if self.current_sort == "date":
                self.photos.sort(key=lambda x: x[1], reverse=True)
            elif self.current_sort == "size":
                self.photos.sort(key=lambda x: x[2], reverse=True)
            elif self.current_sort == "name":
                self.photos.sort(key=lambda x: x[0].lower())
            logging.info(f"Photos sorted by {self.current_sort}")
        except Exception as e:
            logging.error(f"Error sorting photos: {str(e)}")
            raise

    def set_sort(self, sort_type: str) -> None:
        sort_map = {"Date": "date", "Size": "size", "Name": "name"}
        self.current_sort = sort_map.get(sort_type, "date")
        self.sort_photos()