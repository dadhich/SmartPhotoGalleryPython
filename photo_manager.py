import os
import cv2
import numpy as np
import logging
from datetime import datetime
from PIL import Image
import exifread
from typing import List, Tuple, Optional
from caption_generator import CaptionGenerator
from database import ImageDatabase
import threading
import tkinter as tk

class PhotoManager:
    def __init__(self, caption_generator: CaptionGenerator, db: ImageDatabase):
        self.photos: List[Tuple[str, datetime, int, str, str]] = []
        self.caption_generator = caption_generator
        self.db = db
        self.current_sort = "Date"
        self.nlp_model = None
        self.caption_thread = None
        logging.debug("PhotoManager initialized")

    def load_model(self):
        try:
            logging.info("Loading SentenceTransformer model")
            from sentence_transformers import SentenceTransformer
            self.nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
            logging.info("SentenceTransformer model loaded successfully")
        except Exception as e:
            logging.exception(f"Error loading NLP model: {str(e)}")
            self.nlp_model = None

    def load_photos(self, folder: str, status_var: Optional[tk.StringVar] = None):
        try:
            logging.info(f"Loading photos from {folder}")
            if not os.path.exists(folder):
                raise ValueError(f"Folder does not exist: {folder}")
            if not os.path.isdir(folder):
                raise ValueError(f"Path is not a directory: {folder}")
            if not os.access(folder, os.R_OK):
                raise PermissionError(f"No read permissions for folder: {folder}")
            
            # Get existing metadata
            try:
                existing_metadata = {m["file_path"]: m for m in self.db.get_all_metadata()}
            except AttributeError:
                logging.warning("Database does not support get_all_metadata; querying individually")
                existing_metadata = {}
                for root, _, files in os.walk(folder):
                    for file in files:
                        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                            file_path = os.path.join(root, file)
                            metadata = self.db.get_image_metadata(file_path)
                            if metadata:
                                existing_metadata[file_path] = metadata
            
            photos = []
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        file_path = os.path.join(root, file)
                        try:
                            stat = os.stat(file_path)
                            date = datetime.fromtimestamp(stat.st_mtime)
                            size = stat.st_size
                            
                            if file_path in existing_metadata:
                                metadata = existing_metadata[file_path]
                                location = metadata.get("location", "Unknown")
                                tags = metadata.get("tags", "")
                            else:
                                location = "Unknown"
                                tags = ""
                            
                            photos.append((file_path, date, size, location, tags))
                        except Exception as e:
                            logging.exception(f"Error processing file {file_path}: {str(e)}")
                            continue
            
            if not photos:
                if status_var:
                    status_var.set("No valid images found in folder")
                raise ValueError("No valid images found in folder")
            
            self.photos = photos
            self.set_sort(self.current_sort)
            
            if status_var:
                status_var.set(f"Generating captions for {len(photos)} photos...")
            
            self.caption_thread = threading.Thread(
                target=self._process_captions,
                args=(self.photos, status_var),
                daemon=True
            )
            self.caption_thread.start()
            
            logging.info(f"Loaded {len(self.photos)} photos from {folder}")
            
        except Exception as e:
            logging.exception(f"Error loading photos from {folder}: {str(e)}")
            if status_var:
                status_var.set(f"Error loading photos: {str(e)}")
            raise

    def _process_captions(self, photos: List[Tuple[str, datetime, int, str, str]], status_var: Optional[tk.StringVar] = None):
        try:
            logging.info("Starting caption processing")
            total = len(photos)
            for i, (file_path, date, size, location, tags) in enumerate(photos):
                try:
                    # Skip if caption already exists
                    metadata = self.db.get_image_metadata(file_path)
                    if metadata and metadata.get('detailed_caption'):
                        logging.debug(f"Skipping caption for {file_path}: already exists")
                        continue
                    
                    caption = self.caption_generator.generate_image_caption(file_path)
                    self.db.add_image(file_path, date.isoformat(), size, location, tags, caption)
                    
                    if status_var:
                        status_var.set(f"Processing captions: {i + 1}/{total}")
                    
                    logging.debug(f"Generated caption for {file_path}")
                
                except Exception as e:
                    logging.exception(f"Error processing caption for {file_path}: {str(e)}")
                    continue
            
            if status_var:
                status_var.set(f"Processed captions for {total} photos")
            logging.info("Completed caption processing")
            
        except Exception as e:
            logging.exception(f"Error in caption processing thread: {str(e)}")

    def set_sort(self, sort_by: str):
        try:
            logging.info(f"Setting sort to {sort_by}")
            self.current_sort = sort_by
            if sort_by == "Date":
                self.photos.sort(key=lambda x: x[1], reverse=True)
            elif sort_by == "Size":
                self.photos.sort(key=lambda x: x[2], reverse=True)
            elif sort_by == "Name":
                self.photos.sort(key=lambda x: x[0].lower())
            logging.debug(f"Photos sorted by {sort_by}")
        except Exception as e:
            logging.exception(f"Error setting sort to {sort_by}: {str(e)}")

    def search_photos(self, query: str) -> List[Tuple[str, datetime, int, str, str]]:
        try:
            logging.info(f"Searching photos with query: {query}")
            if not query:
                return self.photos
            
            if not self.nlp_model:
                logging.warning("NLP model not loaded; returning all photos")
                return self.photos
            
            # Get all captions from database
            metadata = self.db.get_all_metadata()
            photo_captions = [(m['file_path'], m.get('detailed_caption', '')) for m in metadata]
            caption_texts = [caption for _, caption in photo_captions if caption]
            file_paths = [file_path for file_path, caption in photo_captions if caption]
            
            if not caption_texts:
                logging.warning("No captions found in database")
                return []
            
            # Encode captions and query
            caption_embeddings = self.nlp_model.encode(caption_texts)
            query_embedding = self.nlp_model.encode([query])[0]
            
            # Compute similarities
            similarities = np.dot(caption_embeddings, query_embedding) / (
                np.linalg.norm(caption_embeddings, axis=1) * np.linalg.norm(query_embedding)
            )
            
            # Get top results
            top_k = min(10, len(file_paths))
            top_indices = np.argsort(similarities)[::-1][:top_k]
            results = [
                photo for photo in self.photos
                if photo[0] in [file_paths[i] for i in top_indices if similarities[i] > 0.3]
            ]
            
            logging.info(f"Search returned {len(results)} photos for query: {query}")
            return results
            
        except Exception as e:
            logging.exception(f"Error searching photos with query '{query}': {str(e)}")
            return []