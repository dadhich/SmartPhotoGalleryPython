import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
import os
from PIL import Image, ImageTk
import logging
from typing import Optional
from photo_manager import PhotoManager
from caption_generator import CaptionGenerator
from database import ImageDatabase
import threading
import queue

class GifAnimation:
    def __init__(self, root: tk.Tk, parent: tk.Widget, text: str, gif_path: str):
        self.root = root
        self.parent = parent
        self.text = text
        self.gif_path = gif_path
        self.frames = []
        self.current_frame = 0
        self.running = False
        self.overlay = None
        self.label = None
        self.load_gif()

    def load_gif(self):
        try:
            with Image.open(self.gif_path) as img:
                for i in range(img.n_frames):
                    img.seek(i)
                    frame = img.copy().resize((50, 50), Image.Resampling.LANCZOS)
                    self.frames.append(ImageTk.PhotoImage(frame))
            logging.debug(f"Loaded {len(self.frames)} frames from {self.gif_path}")
        except Exception as e:
            logging.exception(f"Error loading GIF {self.gif_path}: {str(e)}")
            self.frames = []

    def create_overlay(self):
        try:
            self.overlay = tk.Toplevel(self.parent)
            self.overlay.attributes('-alpha', 0.8)
            self.overlay.overrideredirect(True)
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - 100) // 2
            y = (screen_height - 100) // 2
            self.overlay.geometry(f"100x100+{x}+{y}")
            self.label = ttk.Label(self.overlay, text=self.text)
            self.label.pack()
            if self.frames:
                self.label.config(image=self.frames[0])
            logging.debug("Created GIF overlay")
        except Exception as e:
            logging.exception(f"Error creating overlay: {str(e)}")
            self.label = ttk.Label(self.parent, text=f"{self.text}...")
            self.label.pack()

    def animate(self):
        if self.running and self.frames:
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.label.config(image=self.frames[self.current_frame])
            self.root.after(100, self.animate)
        elif not self.frames and self.label:
            self.label.config(text=f"{self.text}...")

    def start(self):
        try:
            self.running = True
            self.create_overlay()
            self.animate()
            logging.debug("Started GIF animation")
        except Exception as e:
            logging.exception(f"Error starting GIF animation: {str(e)}")
            self.label = ttk.Label(self.parent, text=f"{self.text}...")
            self.label.pack()
            self.running = True

    def stop(self):
        self.running = False
        if self.overlay:
            self.overlay.destroy()
        elif self.label:
            self.label.destroy()
        logging.debug("Stopped GIF animation")

class UIManager:
    def __init__(self, root: tk.Tk, photo_manager: PhotoManager, caption_generator: CaptionGenerator, db: ImageDatabase, status_var: tk.StringVar):
        self.root = root
        self.photo_manager = photo_manager
        self.caption_generator = caption_generator
        self.db = db
        self.status_var = status_var
        self.displayed_photos = []
        self.caption_queue = queue.Queue()
        self.caption_thread = threading.Thread(target=self._process_captions, daemon=True)
        self.caption_thread.start()
        
        self.setup_ui()
        logging.debug("UIManager initialized")

    def setup_ui(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top controls
        self.top_frame = ttk.Frame(self.main_frame)
        self.top_frame.pack(fill=tk.X)
        
        self.folder_button = ttk.Button(self.top_frame, text="Select Folder", command=self.select_folder)
        self.folder_button.pack(side=tk.LEFT, padx=5)
        
        self.folder_label = ttk.Label(self.top_frame, text="No folder selected")
        self.folder_label.pack(side=tk.LEFT, padx=5)
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.top_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_entry.bind('<Return>', self.search_photos)
        
        self.sort_var = tk.StringVar(value="Date")
        self.sort_menu = ttk.OptionMenu(self.top_frame, self.sort_var, "Date", "Date", "Size", "Name", command=self.sort_photos)
        self.sort_menu.pack(side=tk.LEFT, padx=5)
        
        # Scrollable photo grid
        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Status bar
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.folder_spinner = GifAnimation(self.root, self.main_frame, "Loading", "loading.gif")
        self.search_spinner = GifAnimation(self.root, self.main_frame, "Searching", "loading.gif")
        
        logging.debug("UI setup completed")

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def select_folder(self):
        try:
            folder = filedialog.askdirectory()
            if folder:
                self.folder_label.config(text=folder)
                self.status_var.set(f"Loading {folder}...")
                self.folder_spinner.start()
                try:
                    self.load_and_display_photos(folder)
                except Exception as e:
                    self.status_var.set(f"Error loading folder: {str(e)}")
                    logging.exception(f"Error loading folder {folder}: {str(e)}")
                finally:
                    self.folder_spinner.stop()
        except Exception as e:
            self.status_var.set(f"Error selecting folder: {str(e)}")
            logging.exception(f"Error selecting folder: {str(e)}")
            self.folder_spinner.stop()

    def load_and_display_photos(self, folder: str):
        try:
            self.photo_manager.load_photos(folder, self.status_var)
            self.display_photos(self.photo_manager.photos)
            logging.info(f"Displayed photos from {folder}")
        except Exception as e:
            self.status_var.set(f"Error loading photos: {str(e)}")
            logging.exception(f"Error loading photos from {folder}: {str(e)}")

    def display_photos(self, photos: list):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.displayed_photos = photos
        if not photos:
            self.status_var.set("No photos found")
            return
        
        max_cols = 4
        thumbnail_size = (200, 200)
        
        for i, (file_path, date, size, location, tags) in enumerate(photos):
            try:
                img = Image.open(file_path)
                img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                frame = ttk.Frame(self.scrollable_frame)
                row = i // max_cols
                col = i % max_cols
                frame.grid(row=row, column=col, padx=5, pady=5)
                
                label = ttk.Label(frame, image=photo)
                label.image = photo
                label.pack()
                label.bind("<Double-1>", lambda e, path=file_path: self.open_full_image(path))
                
                name_label = ttk.Label(frame, text=os.path.basename(file_path))
                name_label.pack()
                
                logging.debug(f"Displayed thumbnail for {file_path}")
                
            except Exception as e:
                logging.exception(f"Error displaying thumbnail for {file_path}: {str(e)}")
                continue
        
        self.status_var.set(f"Displaying {len(photos)} photos")

    def open_full_image(self, file_path: str):
        try:
            full_window = tk.Toplevel(self.root)
            full_window.title(os.path.basename(file_path))
            full_window.state('zoomed')
            
            canvas = tk.Canvas(full_window, highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            img = Image.open(file_path)
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight() - 100
            img.thumbnail((screen_width, screen_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            img_width, img_height = img.size
            canvas.create_image(0, 0, image=photo, anchor="nw")
            canvas.image = photo
            
            canvas.config(scrollregion=(0, 0, img_width, img_height))
            
            caption_frame = ttk.Frame(full_window)
            caption_frame.pack(fill=tk.X, side=tk.BOTTOM)
            
            caption_label = ttk.Label(caption_frame, text="Generating caption...")
            caption_label.pack(pady=5)
            
            self.caption_queue.put((file_path, caption_label))
            
            # Draw clickable rectangles for faces
            faces = self.db.get_faces(file_path)
            if not faces:
                logging.warning(f"No faces found for {file_path}")
                canvas.create_text(
                    img_width // 2, img_height // 2,
                    text="No faces detected. Try another image.",
                    fill="yellow", font=('Arial', 14, 'bold')
                )
            
            original_img = Image.open(file_path)
            orig_width, orig_height = original_img.size
            
            for i, face in enumerate(faces):
                try:
                    top = face.get('top', 0) or 0
                    right = face.get('right', 0) or 0
                    bottom = face.get('bottom', 0) or 0
                    left = face.get('left', 0) or 0
                    encoding = face['encoding']
                    name = face.get('name') or f"Face {i + 1}"
                    
                    if top == 0 and right == 0 and bottom == 0 and left == 0:
                        logging.warning(f"Invalid face coordinates for {file_path}: {top}, {right}, {bottom}, {left}")
                        continue
                    
                    # Scale coordinates to match resized image
                    scale_x = img_width / orig_width
                    scale_y = img_height / orig_height
                    scaled_top = top * scale_y
                    scaled_right = right * scale_x
                    scaled_bottom = bottom * scale_y
                    scaled_left = left * scale_x
                    
                    # Create transparent rectangle with yellow border
                    rect_id = canvas.create_rectangle(
                        scaled_left, scaled_top, scaled_right, scaled_bottom,
                        outline='yellow', width=3, fill=''
                    )
                    
                    # Bind click event to open naming dialog
                    def tag_face(event, f_path=file_path, enc=encoding, rect_id=rect_id):
                        name = simpledialog.askstring("Tag Face", "Enter name for this face:", parent=full_window)
                        if name:
                            self.db.update_face_name(f_path, enc, name)
                            logging.info(f"Tagged face in {f_path} as {name}")
                            # Update label
                            for widget in canvas.find_withtag(f"label_{rect_id}"):
                                canvas.itemconfig(widget, text=name)
                    
                    canvas.tag_bind(rect_id, '<Button-1>', tag_face)
                    
                    # Add label for face name
                    label_id = canvas.create_text(
                        scaled_left + 5, scaled_top - 10,
                        text=name, anchor='sw', fill='yellow',
                        font=('Arial', 12, 'bold'), tags=f"label_{rect_id}"
                    )
                    
                    logging.debug(f"Drew face rectangle for {file_path} at scaled ({scaled_left}, {scaled_top}, {scaled_right}, {scaled_bottom})")
                    
                except Exception as e:
                    logging.exception(f"Error drawing face rectangle for {file_path}: {str(e)}")
                    continue
            
            def on_closing():
                full_window.destroy()
                canvas.yview_scroll = lambda *args, **kwargs: None
                logging.debug(f"Closed full image window for {file_path}")
            
            full_window.protocol("WM_DELETE_WINDOW", on_closing)
            
            logging.info(f"Opened full image window for {file_path}")
            
        except Exception as e:
            logging.exception(f"Error opening full image {file_path}: {str(e)}")
            self.status_var.set(f"Error opening image: {str(e)}")

    def search_photos(self, event=None):
        try:
            query = self.search_var.get()
            self.status_var.set(f"Searching for '{query}'...")
            self.search_spinner.start()
            photos = self.photo_manager.search_photos(query)
            self.display_photos(photos)
            self.status_var.set(f"Found {len(photos)} photos")
            logging.info(f"Search completed for query: {query}")
        except Exception as e:
            self.status_var.set(f"Error searching: {str(e)}")
            logging.exception(f"Error searching with query '{query}': {str(e)}")
        finally:
            self.search_spinner.stop()

    def sort_photos(self, sort_by: str):
        try:
            self.photo_manager.set_sort(sort_by)
            self.display_photos(self.photo_manager.photos)
            self.status_var.set(f"Sorted by {sort_by}")
            logging.info(f"Sorted photos by {sort_by}")
        except Exception as e:
            self.status_var.set(f"Error sorting: {str(e)}")
            logging.exception(f"Error sorting by {sort_by}: {str(e)}")

    def _process_captions(self):
        while True:
            try:
                item = self.caption_queue.get()
                if item is None:
                    break
                file_path, caption_label = item
                try:
                    caption = self.caption_generator.generate_image_caption(file_path)
                    self.root.after(0, lambda: caption_label.config(text=caption))
                    
                    # Get metadata, use defaults if None
                    metadata = self.db.get_image_metadata(file_path)
                    if metadata is None:
                        logging.warning(f"No metadata found for {file_path}, using defaults")
                        metadata = {
                            'date': '',
                            'size': 0,
                            'location': '',
                            'tags': ''
                        }
                    
                    self.db.add_image(
                        file_path,
                        metadata.get('date', ''),
                        metadata.get('size', 0),
                        metadata.get('location', ''),
                        metadata.get('tags', ''),
                        caption
                    )
                    logging.debug(f"Generated caption for {file_path}")
                except Exception as e:
                    self.root.after(0, lambda: caption_label.config(text=f"Error: {str(e)}"))
                    logging.exception(f"Error generating caption for {file_path}: {str(e)}")
                finally:
                    self.caption_queue.task_done()
            except Exception as e:
                logging.exception(f"Error in caption thread: {str(e)}")