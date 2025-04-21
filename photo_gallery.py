import tkinter as tk
from tkinter import ttk, filedialog
import logging
import os
from photo_manager import PhotoManager
from caption_generator import CaptionGenerator
from ui_manager import UIManager
from database import ImageDatabase

def main():
    # Setup logging
    log_file = os.path.join(os.path.dirname(__file__), "photo_gallery.log")
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w'),
            logging.StreamHandler()
        ]
    )
    logging.info("Starting SmartPhotoGallery application")
    
    root = tk.Tk()
    root.title("Smart Photo Gallery")
    root.state('zoomed')
    
    db = ImageDatabase()
    caption_generator = CaptionGenerator()
    photo_manager = PhotoManager(caption_generator, db)
    status_var = tk.StringVar(value="Initializing...")
    
    ui_manager = UIManager(root, photo_manager, caption_generator, db, status_var)
    
    try:
        photo_manager.load_model()
        logging.info("Application initialized successfully")
    except Exception as e:
        logging.exception(f"Error initializing application: {str(e)}")
        status_var.set(f"Error initializing: {str(e)}")
    
    root.mainloop()

if __name__ == "__main__":
    main()