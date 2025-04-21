import os
import logging
from datetime import datetime
import exifread
from typing import List, Tuple
from PIL import Image
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from concurrent.futures import ThreadPoolExecutor
from database import ImageDatabase

class PhotoManager:
    def __init__(self, caption_generator, db: ImageDatabase):
        self.photos: List[Tuple[str, datetime, int, str, str]] = []
        self.current_sort = "date"
        self.caption_generator = caption_generator
        self.db = db
        self.nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.caption_embeddings = None

    def load_photos(self, folder: str) -> None:
        try:
            self.photos.clear()
            supported_formats = ('.jpg', '.jpeg', '.png', '.gif')
            photo_paths = []
            
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(supported_formats):
                        photo_paths.append(os.path.join(root, file))
            
            # Process photos in parallel
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.process_photo, path) for path in photo_paths]
                for future in futures:
                    try:
                        photo = future.result()
                        if photo:
                            self.photos.append(photo)
                    except Exception as e:
                        logging.warning(f"Error processing photo: {str(e)}")
            
            # Compute caption embeddings for search
            if self.photos:
                self.caption_embeddings = self.nlp_model.encode(
                    [photo[4] for photo in self.photos], convert_to_tensor=True
                )
            
            self.sort_photos()
            logging.info(f"Loaded {len(self.photos)} photos with tags")
        except Exception as e:
            logging.error(f"Error loading photos: {str(e)}")
            raise

    def process_photo(self, file_path: str) -> Tuple:
        try:
            # Check database for existing metadata
            metadata = self.db.get_image_metadata(file_path)
            stats = os.stat(file_path)
            modified_time = datetime.fromtimestamp(stats.st_mtime)
            
            if metadata and metadata["modified_time"].timestamp() == modified_time.timestamp():
                return (
                    file_path,
                    metadata["modified_time"],
                    metadata["file_size"],
                    metadata["location"],
                    metadata["tags"]
                )
            
            # Generate new metadata
            file_size = stats.st_size
            location = self.get_photo_location(file_path)
            tags = self.caption_generator.generate_tags(file_path)
            
            # Save to database
            self.db.add_image_metadata({
                "file_path": file_path,
                "modified_time": modified_time,
                "file_size": file_size,
                "location": location,
                "tags": tags,
                "detailed_caption": None
            })
            
            return (file_path, modified_time, file_size, location, tags)
        except Exception as e:
            logging.warning(f"Error processing {file_path}: {str(e)}")
            return None

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

    def search_photos(self, query: str, threshold: float = 0.3) -> List[Tuple]:
        try:
            if not self.photos or not query:
                return self.photos
            
            query_embedding = self.nlp_model.encode(query, convert_to_tensor=True)
            cos_scores = util.cos_sim(query_embedding, self.caption_embeddings)[0]
            
            matched_photos = [
                self.photos[i] for i, score in enumerate(cos_scores)
                if score > threshold
            ]
            
            logging.info(f"Search query '{query}' returned {len(matched_photos)} matches")
            return matched_photos
        except Exception as e:
            logging.error(f"Error searching photos: {str(e)}")
            return self.photos