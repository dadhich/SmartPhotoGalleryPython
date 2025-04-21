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
import face_recognition
import tkinter as tk

class PhotoManager:
    def __init__(self, caption_generator: CaptionGenerator, db: ImageDatabase):
        self.photos: List[Tuple[str, datetime, int, str, str]] = []
        self.caption_generator = caption_generator
        self.db = db
        self.current_sort = "Date"
        self.face_net = None
        self.nlp_model = None
        self.metadata_thread = None
        self.face_thread = None
        logging.debug("PhotoManager initialized")

    def load_model(self):
        try:
            model_dir = os.path.dirname(os.path.abspath(__file__))
            prototxt_path = os.path.join(model_dir, "deploy.prototxt")
            caffemodel_path = os.path.join(model_dir, "res10_300x300_ssd_iter_140000.caffemodel")
            
            logging.debug(f"Checking for OpenCV DNN model files: {prototxt_path}, {caffemodel_path}")
            if not (os.path.exists(prototxt_path) and os.path.exists(caffemodel_path)):
                logging.warning(f"OpenCV DNN model files missing: {prototxt_path}, {caffemodel_path}. Face detection disabled.")
                self.face_net = None
                return
            
            self.face_net = cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)
            logging.info("Loaded OpenCV DNN face detection model")
            
            from sentence_transformers import SentenceTransformer
            self.nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
            logging.info("Loaded SentenceTransformer model")
            
        except Exception as e:
            logging.exception(f"Error loading models: {str(e)}")
            self.face_net = None

    def load_photos(self, folder: str, status_var: Optional[tk.StringVar] = None):
        try:
            logging.info(f"Loading photos from {folder}")
            if not os.path.exists(folder):
                raise ValueError(f"Folder does not exist: {folder}")
            if not os.path.isdir(folder):
                raise ValueError(f"Path is not a directory: {folder}")
            if not os.access(folder, os.R_OK):
                raise PermissionError(f"No read permissions for folder: {folder}")
            
            # Try to get all metadata; fall back to individual queries if method is missing
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
                status_var.set(f"Scanning {folder}...")
            
            self.metadata_thread = threading.Thread(
                target=self._process_metadata,
                args=(self.photos, status_var),
                daemon=True
            )
            self.metadata_thread.start()
            
            if self.face_net:
                self.face_thread = threading.Thread(
                    target=self._process_faces,
                    args=(self.photos, status_var),
                    daemon=True
                )
                self.face_thread.start()
            else:
                logging.info("Skipping face detection due to missing or failed model")
            
            logging.info(f"Loaded {len(self.photos)} photos from {folder}")
            
        except Exception as e:
            logging.exception(f"Error loading photos from {folder}: {str(e)}")
            if status_var:
                status_var.set(f"Error loading photos: {str(e)}")
            raise

    def _process_metadata(self, photos: List[Tuple[str, datetime, int, str, str]], status_var: Optional[tk.StringVar] = None):
        try:
            logging.info("Starting metadata processing")
            total = len(photos)
            for i, (file_path, date, size, location, _) in enumerate(photos):
                try:
                    with open(file_path, 'rb') as f:
                        tags = exifread.process_file(f)
                        location = tags.get('GPS GPSLatitude', 'Unknown').values
                        if isinstance(location, list):
                            location = ','.join(str(x) for x in location)
                    
                    image_tags = self.caption_generator.generate_tags(file_path)
                    tags_str = ', '.join(image_tags) if image_tags else ""
                    
                    self.db.add_image(file_path, date.isoformat(), size, str(location), tags_str)
                    
                    if status_var:
                        status_var.set(f"Processing metadata: {i + 1}/{total}")
                    
                    logging.debug(f"Processed metadata for {file_path}")
                
                except Exception as e:
                    logging.exception(f"Error processing metadata for {file_path}: {str(e)}")
                    continue
            
            if status_var:
                status_var.set(f"Processed metadata for {total} photos")
            logging.info("Completed metadata processing")
            
        except Exception as e:
            logging.exception(f"Error in metadata processing thread: {str(e)}")

    def _process_faces(self, photos: List[Tuple[str, datetime, int, str, str]], status_var: Optional[tk.StringVar] = None):
        try:
            logging.info("Starting face detection processing")
            total = len(photos)
            for i, (file_path, _, _, _, _) in enumerate(photos):
                try:
                    # Load image with OpenCV
                    img = cv2.imread(file_path)
                    if img is None:
                        logging.warning(f"Failed to read image {file_path}")
                        continue
                    
                    # Convert BGR to RGB for face_recognition
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    
                    # Detect faces using face_recognition
                    face_locations = face_recognition.face_locations(rgb_img, model='hog')
                    encodings = face_recognition.face_encodings(rgb_img, face_locations)
                    
                    for (top, right, bottom, left), encoding in zip(face_locations, encodings):
                        if encoding is not None:
                            self.db.add_face(
                                file_path,
                                encoding,
                                None,
                                int(top) if top is not None else 0,
                                int(right) if right is not None else 0,
                                int(bottom) if bottom is not None else 0,
                                int(left) if left is not None else 0
                            )
                            logging.debug(f"Stored face for {file_path} at ({left}, {top}, {right}, {bottom})")
                    
                    if status_var:
                        status_var.set(f"Processing faces: {i + 1}/{total}")
                    
                    logging.debug(f"Processed faces for {file_path}: {len(face_locations)} faces found")
                
                except Exception as e:
                    logging.exception(f"Error processing faces for {file_path}: {str(e)}")
                    continue
            
            if status_var:
                status_var.set(f"Processed faces for {total} photos")
            logging.info("Completed face detection processing")
            
        except Exception as e:
            logging.exception(f"Error in face detection thread: {str(e)}")

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
            
            results = []
            query_lower = query.lower()
            
            # Parse query for person names
            person_names = []
            if "with" in query_lower:
                parts = query_lower.split("with")
                if len(parts) > 1:
                    person_names = [name.strip() for name in parts[1].split("and")]
            
            # Search by tags
            tags = query_lower.split()
            tag_results = set()
            for tag in tags:
                if tag not in person_names:
                    images = self.db.get_images_by_tag(tag)
                    tag_results.update(images)
            
            # Search by person
            person_results = set()
            for name in person_names:
                images = self.db.get_images_by_person(name)
                person_results.update(images)
            
            # Combine results
            if tag_results or person_results:
                combined_results = tag_results | person_results
                results = [photo for photo in self.photos if photo[0] in combined_results]
            else:
                # Fallback to NLP-based search if no tags or persons
                if self.nlp_model:
                    photo_captions = [(photo[0], photo[4]) for photo in self.photos]
                    caption_texts = [caption for _, caption in photo_captions]
                    caption_embeddings = self.nlp_model.encode(caption_texts)
                    query_embedding = self.nlp_model.encode([query])[0]
                    similarities = np.dot(caption_embeddings, query_embedding) / (
                        np.linalg.norm(caption_embeddings, axis=1) * np.linalg.norm(query_embedding)
                    )
                    top_k = min(10, len(self.photos))
                    top_indices = np.argsort(similarities)[::-1][:top_k]
                    results = [self.photos[i] for i in top_indices if similarities[i] > 0.3]
                else:
                    results = self.photos
            
            logging.info(f"Search returned {len(results)} photos for query: {query}")
            return results
            
        except Exception as e:
            logging.exception(f"Error searching photos with query '{query}': {str(e)}")
            return []