import tkinter as tk
from ttkthemes import ThemedTk
import logging
from photo_manager import PhotoManager
from ui_manager import UIManager
from caption_generator import CaptionGenerator
from database import ImageDatabase
from utils import setup_logging
import sys

def main():
    try:
        setup_logging()
        logging.info("Photo Gallery application started")
        
        root = ThemedTk(theme="arc")
        root.title("Photo Gallery")
        root.geometry("1200x800")
        
        db = ImageDatabase()
        caption_generator = CaptionGenerator()
        photo_manager = PhotoManager(caption_generator, db)
        ui_manager = UIManager(root, photo_manager, caption_generator, db)
        
        root.mainloop()
    except Exception as e:
        logging.critical(f"Application crashed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()