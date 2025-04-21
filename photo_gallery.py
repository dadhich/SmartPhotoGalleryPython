import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import os
import logging
from datetime import datetime
import exifread
from pathlib import Path
import sys
from typing import List, Tuple
import math
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch

# Configure logging
logging.basicConfig(
    filename='photo_gallery.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PhotoGalleryApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Photo Gallery")
        self.root.geometry("1200x800")
        
        # Initialize variables
        self.photos: List[Tuple[str, datetime, int, str]] = []
        self.thumbnail_size = (150, 150)
        self.current_sort = "date"
        
        # Initialize BLIP model for image captioning
        self.blip_processor = None
        self.blip_model = None
        self.load_blip_model()
        
        # Setup GUI
        self.setup_gui()
        
        # Log application start
        logging.info("Photo Gallery application started")
    
    def load_blip_model(self):
        try:
            # Load BLIP processor and model
            self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
            logging.info("BLIP model loaded successfully")
        except Exception as e:
            logging.error(f"Error loading BLIP model: {str(e)}")
            self.blip_model = None
            self.show_error("Failed to load image captioning model. Captions will not be available.")
    
    def generate_image_caption(self, image_path: str) -> str:
        try:
            if self.blip_model is None or self.blip_processor is None:
                return "Caption unavailable: Model not loaded"
            
            # Load and process image
            img = Image.open(image_path).convert("RGB")
            inputs = self.blip_processor(images=img, return_tensors="pt")
            
            # Generate caption
            with torch.no_grad():
                outputs = self.blip_model.generate(**inputs)
            caption = self.blip_processor.decode(outputs[0], skip_special_tokens=True)
            
            logging.info(f"Generated caption for {image_path}: {caption}")
            return caption
        except Exception as e:
            logging.error(f"Error generating caption for {image_path}: {str(e)}")
            return "Failed to generate caption"
    
    def setup_gui(self):
        try:
            # Create main container
            self.main_frame = ttk.Frame(self.root, padding="10")
            self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Folder selection
            self.folder_frame = ttk.Frame(self.main_frame)
            self.folder_frame.grid(row=0, column=0, sticky=tk.W, pady=5)
            
            self.folder_button = ttk.Button(
                self.folder_frame, 
                text="Select Folder", 
                command=self.select_folder
            )
            self.folder_button.grid(row=0, column=0, padx=5)
            
            self.folder_label = ttk.Label(self.folder_frame, text="No folder selected")
            self.folder_label.grid(row=0, column=1, padx=5)
            
            # Sorting options
            self.sort_frame = ttk.Frame(self.main_frame)
            self.sort_frame.grid(row=1, column=0, sticky=tk.W, pady=5)
            
            ttk.Label(self.sort_frame, text="Sort by:").grid(row=0, column=0, padx=5)
            self.sort_combo = ttk.Combobox(
                self.sort_frame, 
                values=["Date", "Size", "Name"],
                state="readonly",
                width=10
            )
            self.sort_combo.set("Date")
            self.sort_combo.grid(row=0, column=1, padx=5)
            self.sort_combo.bind("<<ComboboxSelected>>", self.on_sort_change)
            
            # Photo grid
            self.canvas = tk.Canvas(self.main_frame, bg="white")
            self.scrollbar = ttk.Scrollbar(
                self.main_frame, 
                orient=tk.VERTICAL, 
                command=self.canvas.yview
            )
            self.scrollable_frame = ttk.Frame(self.canvas)
            
            self.scrollable_frame.bind(
                "<Configure>",
                lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            )
            
            self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
            self.canvas.configure(yscrollcommand=self.scrollbar.set)
            
            # Enable mouse wheel scrolling for grid view
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_grid)
            self.canvas.bind_all("<Button-4>", self._on_mousewheel_grid)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel_grid)
            
            self.canvas.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self.scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
            
            # Configure weights
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            self.main_frame.columnconfigure(0, weight=1)
            self.main_frame.rowconfigure(2, weight=1)
            
            logging.info("GUI setup completed successfully")
            
        except Exception as e:
            logging.error(f"Error setting up GUI: {str(e)}")
            self.show_error("Failed to initialize GUI")
    
    def _on_mousewheel_grid(self, event):
        try:
            # Handle mouse wheel for grid view (Magic Mouse compatible)
            delta = event.delta if event.delta else (-1 if event.num == 5 else 1) * 120
            self.canvas.yview_scroll(-1 * (delta // 120), "units")
            logging.debug(f"Grid view scrolled with mouse wheel: delta={delta}")
        except Exception as e:
            logging.error(f"Error handling mouse wheel in grid view: {str(e)}")
    
    def select_folder(self):
        try:
            folder = filedialog.askdirectory()
            if folder:
                self.folder_label.config(text=folder)
                self.load_photos(folder)
                logging.info(f"Selected folder: {folder}")
        except Exception as e:
            logging.error(f"Error selecting folder: {str(e)}")
            self.show_error("Failed to select folder")
    
    def load_photos(self, folder: str):
        try:
            self.photos.clear()
            supported_formats = ('.jpg', '.jpeg', '.png', '.gif')
            
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(supported_formats):
                        try:
                            file_path = os.path.join(root, file)
                            # Get file stats
                            stats = os.stat(file_path)
                            modified_time = datetime.fromtimestamp(stats.st_mtime)
                            file_size = stats.st_size
                            
                            # Try to get location from EXIF (optional)
                            location = self.get_photo_location(file_path)
                            
                            self.photos.append((file_path, modified_time, file_size, location))
                        except Exception as e:
                            logging.warning(f"Error processing file {file}: {str(e)}")
                            continue
            
            self.sort_photos()
            self.display_photos()
            logging.info(f"Loaded {len(self.photos)} photos")
            
        except Exception as e:
            logging.error(f"Error loading photos: {str(e)}")
            self.show_error("Failed to load photos")
    
    def get_photo_location(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f)
                if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
                    return f"{tags['GPS GPSLatitude']}, {tags['GPS GPSLongitude']}"
        except Exception as e:
            logging.debug(f"No GPS data for {file_path}: {str(e)}")
        return "Unknown"
    
    def sort_photos(self):
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
            self.show_error("Failed to sort photos")
    
    def on_sort_change(self, event):
        try:
            sort_map = {"Date": "date", "Size": "size", "Name": "name"}
            self.current_sort = sort_map[self.sort_combo.get()]
            self.sort_photos()
            self.display_photos()
            logging.info(f"Sort changed to {self.current_sort}")
        except Exception as e:
            logging.error(f"Error changing sort: {str(e)}")
            self.show_error("Failed to change sort order")
    
    def display_photos(self):
        try:
            # Clear existing photos
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
            if not self.photos:
                ttk.Label(self.scrollable_frame, text="No photos found").grid(row=0, column=0)
                return
            
            # Calculate columns based on window width
            canvas_width = self.canvas.winfo_width()
            cols = max(1, canvas_width // (self.thumbnail_size[0] + 20))
            
            for i, (file_path, date, size, location) in enumerate(self.photos):
                try:
                    # Create thumbnail
                    img = Image.open(file_path)
                    img.thumbnail(self.thumbnail_size)
                    photo = ImageTk.PhotoImage(img)
                    
                    # Create frame for each photo
                    photo_frame = ttk.Frame(self.scrollable_frame)
                    photo_frame.grid(
                        row=i // cols, 
                        column=i % cols, 
                        padx=10, 
                        pady=10
                    )
                    
                    # Display image with double-click binding
                    label = ttk.Label(photo_frame, image=photo)
                    label.image = photo  # Keep reference
                    label.grid(row=0, column=0)
                    label.bind("<Double-1>", lambda e, path=file_path: self.open_full_image(path))
                    
                    # Display metadata
                    ttk.Label(
                        photo_frame, 
                        text=f"Date: {date.strftime('%Y-%m-%d')}"
                    ).grid(row=1, column=0)
                    ttk.Label(
                        photo_frame, 
                        text=f"Size: {size / 1024:.1f} KB"
                    ).grid(row=2, column=0)
                    ttk.Label(
                        photo_frame, 
                        text=f"Location: {location}"
                    ).grid(row=3, column=0)
                except Exception as e:
                    logging.warning(f"Error displaying photo {file_path}: {str(e)}")
                    continue
            
            logging.info(f"Displayed {len(self.photos)} photos")
            
        except Exception as e:
            logging.error(f"Error displaying photos: {str(e)}")
            self.show_error("Failed to display photos")
    
    def open_full_image(self, file_path: str):
        try:
            # Create new window
            full_image_window = tk.Toplevel(self.root)
            full_image_window.title("Full Image View")
            full_image_window.geometry("800x600")
            
            # Load original image
            original_img = Image.open(file_path)
            
            # Generate caption
            caption = self.generate_image_caption(file_path)
            
            # Initialize zoom state
            zoom_factor = 1.0
            max_zoom = 3.0
            min_zoom = 0.3
            
            # Create canvas for image with scrollbars
            canvas = tk.Canvas(full_image_window, bg="white")
            v_scrollbar = ttk.Scrollbar(full_image_window, orient=tk.VERTICAL, command=canvas.yview)
            h_scrollbar = ttk.Scrollbar(full_image_window, orient=tk.HORIZONTAL, command=canvas.xview)
            
            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            # Layout canvas and scrollbars
            canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
            h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
            
            # Configure weights for resizing
            full_image_window.columnconfigure(0, weight=1)
            full_image_window.rowconfigure(0, weight=1)
            
            # Create frame inside canvas for image and caption
            image_frame = ttk.Frame(canvas)
            canvas.create_window((0, 0), window=image_frame, anchor="nw")
            
            # Create image label
            image_label = ttk.Label(image_frame)
            image_label.grid(row=0, column=0, padx=10, pady=10)
            
            # Create caption label
            caption_label = ttk.Label(image_frame, text=caption, wraplength=750)
            caption_label.grid(row=1, column=0, pady=5)
            
            # Function to update displayed image and scroll region
            def update_image():
                try:
                    # Calculate new size
                    new_size = (
                        int(original_img.width * zoom_factor),
                        int(original_img.height * zoom_factor)
                    )
                    # Resize image
                    resized_img = original_img.resize(new_size, Image.LANCZOS)
                    photo = ImageTk.PhotoImage(resized_img)
                    image_label.configure(image=photo)
                    image_label.image = photo  # Keep reference
                    
                    # Update canvas scroll region
                    canvas.configure(scrollregion=(0, 0, new_size[0], new_size[1] + 50))  # +50 for caption
                    logging.info(f"Image zoomed to factor {zoom_factor} for {file_path}")
                except Exception as e:
                    logging.error(f"Error updating zoomed image: {str(e)}")
                    self.show_error("Failed to update zoomed image")
            
            # Initial display
            update_image()
            
            # Bind mouse wheel for full-size image window
            def _on_mousewheel_full(event):
                try:
                    delta = event.delta if event.delta else (-1 if event.num == 5 else 1) * 120
                    canvas.yview_scroll(-1 * (delta // 120), "units")
                    logging.debug(f"Full image window scrolled with mouse wheel: delta={delta}")
                except Exception as e:
                    logging.error(f"Error handling mouse wheel in full image window: {str(e)}")
            
            canvas.bind_all("<MouseWheel>", _on_mousewheel_full)
            canvas.bind_all("<Button-4>", _on_mousewheel_full)
            canvas.bind_all("<Button-5>", _on_mousewheel_full)
            
            # Update scroll region when canvas size changes
            def configure_canvas(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
            
            image_frame.bind("<Configure>", configure_canvas)
            
            # Control frame for zoom buttons
            control_frame = ttk.Frame(full_image_window)
            control_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
            
            # Zoom in button
            ttk.Button(
                control_frame,
                text="Zoom In",
                command=lambda: adjust_zoom(0.2)
            ).pack(side=tk.LEFT, padx=5)
            
            # Zoom out button
            ttk.Button(
                control_frame,
                text="Zoom Out",
                command=lambda: adjust_zoom(-0.2)
            ).pack(side=tk.LEFT, padx=5)
            
            # Reset zoom button
            ttk.Button(
                control_frame,
                text="Reset Zoom",
                command=lambda: adjust_zoom(reset=True)
            ).pack(side=tk.LEFT, padx=5)
            
            # Function to adjust zoom
            def adjust_zoom(delta=0, reset=False):
                nonlocal zoom_factor
                try:
                    if reset:
                        zoom_factor = 1.0
                    else:
                        new_zoom = zoom_factor + delta
                        if min_zoom <= new_zoom <= max_zoom:
                            zoom_factor = new_zoom
                        else:
                            logging.info(f"Zoom limit reached: {zoom_factor}")
                            return
                    update_image()
                except Exception as e:
                    logging.error(f"Error adjusting zoom: {str(e)}")
                    self.show_error("Failed to adjust zoom")
            
            logging.info(f"Opened full-size image: {file_path} with caption: {caption}")
            
        except Exception as e:
            logging.error(f"Error opening full-size image {file_path}: {str(e)}")
            self.show_error("Failed to open full-size image")
    
    def show_error(self, message: str):
        tk.messagebox.showerror("Error", message)
        logging.error(f"Displayed error message: {message}")

def main():
    try:
        root = tk.Tk()
        app = PhotoGalleryApp(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Application crashed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()