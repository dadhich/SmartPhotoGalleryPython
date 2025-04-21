import os
import logging
from datetime import datetime
import exifread
from typing import List, Tuple
from PIL import Image
from pathlib import Path
from sentence_transformers import SentenceTransformer, util

class PhotoManager:
    def __init__(self, caption_generator):
        self.photos: List[Tuple[str, datetime, int, str, str]] = []  # Added caption field
        self.current_sort = "date"
        self.caption_generator = caption_generator
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
            
            # Generate captions in batch
            captions = self.caption_generator.generate_batch_captions(photo_paths)
            
            for file_path, caption in zip(photo_paths, captions):
                try:
                    stats = os.stat(file_path)
                    modified_time = datetime.fromtimestamp(stats.st_mtime)
                    file_size = stats.st_size
                    location = self.get_photo_location(file_path)
                    self.photos.append((file_path, modified_time, file_size, location, caption))
                except Exception as e:
                    logging.warning(f"Error processing file {file_path}: {str(e)}")
                    continue
            
            # Compute caption embeddings for search
            self.caption_embeddings = self.nlp_model.encode(
                [photo[4] for photo in self.photos], convert_to_tensor=True
            )
            
            self.sort_photos()
            logging.info(f"Loaded {len(self.photos)} photos with captions")
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

    def search_photos(self, query: str, threshold: float = 0.3) -> List[Tuple]:
        try:
            if not self.photos or not query:
                return self.photos
            
            # Encode query
            query_embedding = self.nlp_model.encode(query, convert_to_tensor=True)
            
            # Compute cosine similarities
            cos_scores = util.cos_sim(query_embedding, self.caption_embeddings)[0]
            
            # Filter photos with scores above threshold
            matched_photos = [
                self.photos[i] for i, score in enumerate(cos_scores)
                if score > threshold
            ]
            
            logging.info(f"Search query '{query}' returned {len(matched_photos)} matches")
            return matched_photos
        except Exception as e:
            logging.error(f"Error searching photos: {str(e)}")
            return self.photos