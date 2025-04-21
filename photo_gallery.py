import tkinter as tk
from ttkthemes import ThemedTk
import logging
from photo_manager import PhotoManager
from ui_manager import UIManager
from caption_generator import CaptionGenerator
from utils import setup_logging

def main():
    try:
        # Setup logging
        setup_logging()
        logging.info("Photo Gallery application started")
        
        # Initialize dependencies
        root = ThemedTk(theme="arc")  # Modern theme
        root.title("Photo Gallery")
        root.geometry("1200x800")
        
        photo_manager = PhotoManager()
        caption_generator = CaptionGenerator()
        ui_manager = UIManager(root, photo_manager, caption_generator)
        
        root.mainloop()
    except Exception as e:
        logging.critical(f"Application crashed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()