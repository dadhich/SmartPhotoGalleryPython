import tkinter as tk
from ui_manager import UIManager
from photo_manager import PhotoManager
from caption_generator import CaptionGenerator
from database import ImageDatabase
import logging
import threading
import queue

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('photo_gallery.log', mode='w'),
            logging.StreamHandler()
        ]
    )
    logging.debug("Logging setup complete")

def main():
    setup_logging()
    logging.info("Starting SmartPhotoGallery")
    
    root = tk.Tk()
    root.title("SmartPhotoGallery")
    root.geometry("800x600")
    root.state('zoomed')
    
    status_var = tk.StringVar(value="Initializing...")
    
    db = ImageDatabase("photo_database.db")
    
    # Initialize UI with disabled controls
    ui_manager = UIManager(root, None, None, db, status_var)
    ui_manager.folder_button.config(state='disabled')
    ui_manager.search_entry.config(state='disabled')
    ui_manager.sort_menu.config(state='disabled')
    
    # Queue for model loading status
    model_queue = queue.Queue()
    
    def load_models():
        try:
            logging.info("Starting background model loading")
            caption_generator = CaptionGenerator()
            photo_manager = PhotoManager(caption_generator, db)
            photo_manager.load_model()
            model_queue.put((photo_manager, caption_generator))
            logging.info("Background model loading completed")
        except Exception as e:
            logging.exception(f"Error loading models: {str(e)}")
            model_queue.put(None)
    
    # Start model loading in background
    threading.Thread(target=load_models, daemon=True).start()
    
    def check_model_loading():
        try:
            result = model_queue.get_nowait()
            if result:
                photo_manager, caption_generator = result
                ui_manager.photo_manager = photo_manager
                ui_manager.caption_generator = caption_generator
                ui_manager.folder_button.config(state='normal')
                ui_manager.search_entry.config(state='normal')
                ui_manager.sort_menu.config(state='normal')
                status_var.set("Ready")
                logging.info("Models loaded, UI enabled")
            else:
                status_var.set("Error loading models")
                logging.error("Model loading failed")
        except queue.Empty:
            root.after(100, check_model_loading)
    
    root.after(100, check_model_loading)
    
    root.mainloop()
    logging.info("SmartPhotoGallery closed")

if __name__ == "__main__":
    main()