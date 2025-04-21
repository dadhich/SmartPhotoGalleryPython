import sqlite3
import logging
import pickle
from typing import List, Dict, Optional, Any

class ImageDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._create_tables()
        logging.debug(f"ImageDatabase initialized with path {db_path}")

    def _create_tables(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Images table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS images (
                        file_path TEXT PRIMARY KEY,
                        date TEXT,
                        size INTEGER,
                        location TEXT,
                        tags TEXT,
                        detailed_caption TEXT
                    )
                ''')
                
                # Faces table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS faces (
                        file_path TEXT,
                        encoding BLOB,
                        name TEXT,
                        top INTEGER,
                        right INTEGER,
                        bottom INTEGER,
                        left INTEGER
                    )
                ''')
                
                conn.commit()
                logging.debug("Database tables created or verified")
        except sqlite3.Error as e:
            logging.exception(f"Error creating tables: {str(e)}")
            raise

    def add_image(self, file_path: str, date: str, size: int, location: str, tags: str, detailed_caption: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO images (file_path, date, size, location, tags, detailed_caption)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (file_path, date, size, location, tags, detailed_caption))
                conn.commit()
                logging.debug(f"Added/updated image metadata for {file_path}")
        except sqlite3.Error as e:
            logging.exception(f"Error adding image {file_path}: {str(e)}")
            raise

    def get_image_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT file_path, date, size, location, tags, detailed_caption
                    FROM images WHERE file_path = ?
                ''', (file_path,))
                result = cursor.fetchone()
                if result:
                    return {
                        'file_path': result[0],
                        'date': result[1],
                        'size': result[2],
                        'location': result[3],
                        'tags': result[4],
                        'detailed_caption': result[5]
                    }
                logging.debug(f"No metadata found for {file_path}")
                return None
        except sqlite3.Error as e:
            logging.exception(f"Error retrieving metadata for {file_path}: {str(e)}")
            return None

    def get_all_metadata(self) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT file_path, date, size, location, tags, detailed_caption
                    FROM images
                ''')
                results = cursor.fetchall()
                metadata = [
                    {
                        'file_path': row[0],
                        'date': row[1],
                        'size': row[2],
                        'location': row[3],
                        'tags': row[4],
                        'detailed_caption': row[5]
                    }
                    for row in results
                ]
                logging.debug(f"Retrieved metadata for {len(metadata)} images")
                return metadata
        except sqlite3.Error as e:
            logging.exception(f"Error retrieving all metadata: {str(e)}")
            return []

    def add_face(self, file_path: str, encoding: Any, name: Optional[str], top: int, right: int, bottom: int, left: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                encoding_blob = pickle.dumps(encoding)
                cursor.execute('''
                    INSERT INTO faces (file_path, encoding, name, top, right, bottom, left)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (file_path, encoding_blob, name, top, right, bottom, left))
                conn.commit()
                logging.debug(f"Added face for {file_path} at ({left}, {top}, {right}, {bottom})")
        except sqlite3.Error as e:
            logging.exception(f"Error adding face for {file_path}: {str(e)}")
            raise

    def get_faces(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT file_path, encoding, name, top, right, bottom, left
                    FROM faces WHERE file_path = ?
                ''', (file_path,))
                results = cursor.fetchall()
                faces = [
                    {
                        'file_path': row[0],
                        'encoding': pickle.loads(row[1]),
                        'name': row[2],
                        'top': row[3],
                        'right': row[4],
                        'bottom': row[5],
                        'left': row[6]
                    }
                    for row in results
                ]
                logging.debug(f"Retrieved {len(faces)} faces for {file_path}")
                return faces
        except sqlite3.Error as e:
            logging.exception(f"Error retrieving faces for {file_path}: {str(e)}")
            return []

    def update_face_name(self, file_path: str, encoding: Any, name: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                encoding_blob = pickle.dumps(encoding)
                cursor.execute('''
                    UPDATE faces SET name = ?
                    WHERE file_path = ? AND encoding = ?
                ''', (name, file_path, encoding_blob))
                conn.commit()
                logging.debug(f"Updated face name to {name} for {file_path}")
        except sqlite3.Error as e:
            logging.exception(f"Error updating face name for {file_path}: {str(e)}")
            raise

    def clear_faces(self, file_path: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM faces WHERE file_path = ?
                ''', (file_path,))
                conn.commit()
                logging.debug(f"Cleared {cursor.rowcount} faces for {file_path}")
        except sqlite3.Error as e:
            logging.exception(f"Error clearing faces for {file_path}: {str(e)}")
            raise