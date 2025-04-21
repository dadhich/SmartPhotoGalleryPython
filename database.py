import sqlite3
import numpy as np
import logging
from typing import List, Dict, Any, Optional

class ImageDatabase:
    def __init__(self, db_path: str = ":memory:"):
        try:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            
            # Create tables
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    file_path TEXT PRIMARY KEY,
                    date TEXT,
                    size INTEGER,
                    location TEXT,
                    tags TEXT,
                    detailed_caption TEXT
                )
            ''')
            
            self.cursor.execute('''
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
            
            # Migrate existing faces table to add top, right, bottom, left columns if missing
            try:
                self.cursor.execute("SELECT top FROM faces LIMIT 1")
            except sqlite3.OperationalError:
                logging.info("Migrating faces table to add coordinate columns")
                self.cursor.execute("ALTER TABLE faces ADD COLUMN top INTEGER")
                self.cursor.execute("ALTER TABLE faces ADD COLUMN right INTEGER")
                self.cursor.execute("ALTER TABLE faces ADD COLUMN bottom INTEGER")
                self.cursor.execute("ALTER TABLE faces ADD COLUMN left INTEGER")
                self.conn.commit()
            
            self.conn.commit()
            logging.debug("Database initialized")
            
        except Exception as e:
            logging.exception(f"Error initializing database: {str(e)}")
            raise

    def add_image(self, file_path: str, date: str, size: int, location: str, tags: str, detailed_caption: Optional[str] = None):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO images (file_path, date, size, location, tags, detailed_caption)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (file_path, date, size, location, tags, detailed_caption))
            self.conn.commit()
            logging.debug(f"Added image to database: {file_path}")
        except Exception as e:
            logging.exception(f"Error adding image {file_path}: {str(e)}")

    def get_image_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            self.cursor.execute('SELECT * FROM images WHERE file_path = ?', (file_path,))
            row = self.cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logging.exception(f"Error retrieving metadata for {file_path}: {str(e)}")
            return None

    def get_all_metadata(self) -> List[Dict[str, Any]]:
        try:
            self.cursor.execute('SELECT * FROM images')
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logging.exception(f"Error retrieving all metadata: {str(e)}")
            return []

    def add_face(self, file_path: str, encoding: np.ndarray, name: Optional[str], top: int, right: int, bottom: int, left: int):
        try:
            encoding_blob = encoding.tobytes()
            self.cursor.execute('''
                INSERT INTO faces (file_path, encoding, name, top, right, bottom, left)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (file_path, encoding_blob, name, top, right, bottom, left))
            self.conn.commit()
            logging.debug(f"Added face for {file_path}")
        except Exception as e:
            logging.exception(f"Error adding face for {file_path}: {str(e)}")

    def get_faces(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            self.cursor.execute('''
                SELECT encoding, name, top, right, bottom, left
                FROM faces WHERE file_path = ?
            ''', (file_path,))
            rows = self.cursor.fetchall()
            faces = []
            for row in rows:
                face = dict(row)
                face['encoding'] = np.frombuffer(row['encoding'], dtype=np.float64)
                faces.append(face)
            return faces
        except Exception as e:
            logging.exception(f"Error retrieving faces for {file_path}: {str(e)}")
            return []

    def update_face_name(self, file_path: str, encoding: np.ndarray, name: str):
        try:
            encoding_blob = encoding.tobytes()
            self.cursor.execute('''
                UPDATE faces
                SET name = ?
                WHERE file_path = ? AND encoding = ?
            ''', (name, file_path, encoding_blob))
            self.conn.commit()
            logging.debug(f"Updated face name to {name} for {file_path}")
        except Exception as e:
            logging.exception(f"Error updating face name for {file_path}: {str(e)}")

    def get_images_by_tag(self, tag: str) -> List[str]:
        try:
            self.cursor.execute('''
                SELECT file_path FROM images
                WHERE tags LIKE ?
            ''', (f'%{tag}%',))
            return [row['file_path'] for row in self.cursor.fetchall()]
        except Exception as e:
            logging.exception(f"Error retrieving images by tag {tag}: {str(e)}")
            return []

    def get_images_by_person(self, name: str) -> List[str]:
        try:
            self.cursor.execute('''
                SELECT file_path FROM faces
                WHERE name = ?
            ''', (name,))
            return [row['file_path'] for row in self.cursor.fetchall()]
        except Exception as e:
            logging.exception(f"Error retrieving images by person {name}: {str(e)}")
            return []

    def __del__(self):
        try:
            self.conn.close()
            logging.debug("Database connection closed")
        except Exception as e:
            logging.exception(f"Error closing database: {str(e)}")