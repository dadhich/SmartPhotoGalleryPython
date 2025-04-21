import sqlite3
import os
import logging
from datetime import datetime

class ImageDatabase:
    def __init__(self, db_path: str = "photo_gallery.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS images (
                        file_path TEXT PRIMARY KEY,
                        modified_time REAL,
                        file_size INTEGER,
                        location TEXT,
                        tags TEXT,
                        detailed_caption TEXT
                    )
                """)
                conn.commit()
                logging.info("Database initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
            raise

    def get_image_metadata(self, file_path: str) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM images WHERE file_path = ?",
                    (file_path,)
                )
                result = cursor.fetchone()
                if result:
                    return {
                        "file_path": result[0],
                        "modified_time": datetime.fromtimestamp(result[1]),
                        "file_size": result[2],
                        "location": result[3],
                        "tags": result[4],
                        "detailed_caption": result[5]
                    }
                return None
        except Exception as e:
            logging.error(f"Error retrieving metadata for {file_path}: {str(e)}")
            return None

    def add_image_metadata(self, metadata: dict) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO images
                    (file_path, modified_time, file_size, location, tags, detailed_caption)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metadata["file_path"],
                        metadata["modified_time"].timestamp(),
                        metadata["file_size"],
                        metadata["location"],
                        metadata["tags"],
                        metadata.get("detailed_caption")
                    )
                )
                conn.commit()
                logging.info(f"Added/Updated metadata for {metadata['file_path']}")
                return True
        except Exception as e:
            logging.error(f"Error adding metadata for {metadata['file_path']}: {str(e)}")
            return False

    def update_detailed_caption(self, file_path: str, caption: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE images SET detailed_caption = ? WHERE file_path = ?",
                    (caption, file_path)
                )
                conn.commit()
                logging.info(f"Updated detailed caption for {file_path}")
                return True
        except Exception as e:
            logging.error(f"Error updating caption for {file_path}: {str(e)}")
            return False

    def get_all_metadata(self, folder: str) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM images WHERE file_path LIKE ?",
                    (f"{folder}%",)
                )
                results = cursor.fetchall()
                return [
                    {
                        "file_path": r[0],
                        "modified_time": datetime.fromtimestamp(r[1]),
                        "file_size": r[2],
                        "location": r[3],
                        "tags": r[4],
                        "detailed_caption": r[5]
                    } for r in results
                ]
        except Exception as e:
            logging.error(f"Error retrieving metadata for folder {folder}: {str(e)}")
            return []