import tkinter as tk
from tkinter import ttk, filedialog
import os
from PIL import Image, ImageTk
import logging
from typing import Optional
from photo_manager import PhotoManager
from caption_generator import CaptionGenerator
from database import ImageDatabase
import threading
import queue
import cv2
import face_recognition
import numpy as np

class UIManager:
    def __init__(self, root: tk.Tk, photo_manager: Optional[PhotoManager], caption_generator: Optional[CaptionGenerator], db: ImageDatabase, status_var: tk.StringVar):
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
        
        logging.debug("UI setup completed")

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def select_folder(self):
        try:
            if not self.photo_manager or not self.caption_generator:
                self.status_var.set("Please wait for models to load")
                return
            folder = filedialog.askdirectory()
            if folder:
                self.folder_label.config(text=folder)
                self.status_var.set(f"Loading {folder}...")
                try:
                    self.load_and_display_photos(folder)
                except Exception as e:
                    self.status_var.set(f"Error loading folder: {str(e)}")
                    logging.exception(f"Error loading folder {folder}: {str(e)}")
                finally:
                    self.status_var.set(f"Loaded {folder}")
        except Exception as e:
            self.status_var.set(f"Error selecting folder: {str(e)}")
            logging.exception(f"Error selecting folder: {str(e)}")

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
            
            # Create canvas with scrollbars
            canvas_frame = ttk.Frame(full_window)
            canvas_frame.pack(fill=tk.BOTH, expand=True)
            
            canvas = tk.Canvas(canvas_frame, highlightthickness=0)
            v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
            h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=canvas.xview)
            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Load image
            img = Image.open(file_path)
            original_img = img.copy()
            orig_width, orig_height = img.size
            
            # Initial scale to fit screen
            screen_width = self.root.winfo_screenwidth() - 50
            screen_height = self.root.winfo_screenheight() - 150
            img.thumbnail((screen_width, screen_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            img_width, img_height = img.size
            canvas.create_image(0, 0, image=photo, anchor="nw", tags="image")
            canvas.image = photo
            
            canvas.config(scrollregion=(0, 0, orig_width, orig_height))
            
            # Zoom state
            self.zoom_factor = 1.0
            self.base_img = original_img
            self.face_rects = []
            
            # Zoom buttons
            control_frame = ttk.Frame(full_window)
            control_frame.pack(fill=tk.X, side=tk.BOTTOM)
            
            zoom_in_button = ttk.Button(control_frame, text="Zoom In", command=lambda: self._zoom_image(canvas, 1.2, file_path))
            zoom_in_button.pack(side=tk.LEFT, padx=5, pady=5)
            
            zoom_out_button = ttk.Button(control_frame, text="Zoom Out", command=lambda: self._zoom_image(canvas, 0.833, file_path))
            zoom_out_button.pack(side=tk.LEFT, padx=5, pady=5)
            
            # Caption frame
            caption_frame = ttk.Frame(control_frame)
            caption_frame.pack(fill=tk.X, side=tk.LEFT)
            
            caption_label = ttk.Label(caption_frame, text="Generating caption...")
            caption_label.pack(pady=5)
            
            self.caption_queue.put((file_path, caption_label))
            
            # Clear existing faces for this image to avoid stale data
            self.db.clear_faces(file_path)
            logging.debug(f"Cleared existing faces for {file_path}")
            
            # Face detection
            img_cv = cv2.imread(file_path)
            if img_cv is None:
                logging.warning(f"Failed to read image for face detection: {file_path}")
                # Fallback: Try PIL and convert to OpenCV
                try:
                    pil_img = Image.open(file_path).convert('RGB')
                    img_cv = np.array(pil_img)
                    img_cv = img_cv[:, :, ::-1]  # RGB to BGR
                    logging.debug(f"Fallback image load successful for {file_path}")
                except Exception as e:
                    logging.exception(f"Fallback image load failed for {file_path}: {str(e)}")
            
            if img_cv is not None:
                try:
                    rgb_img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
                    face_locations = face_recognition.face_locations(rgb_img, model='hog')
                    encodings = face_recognition.face_encodings(rgb_img, face_locations)
                    
                    for (top, right, bottom, left), encoding in zip(face_locations, encodings):
                        if encoding is not None:
                            self.db.add_face(
                                file_path,
                                encoding,
                                None,
                                int(top),
                                int(right),
                                int(bottom),
                                int(left)
                            )
                            logging.debug(f"Stored face for {file_path} at ({left}, {top}, {right}, {bottom})")
                        else:
                            logging.warning(f"No encoding for face at ({left}, {top}, {right}, {bottom}) in {file_path}")
                except Exception as e:
                    logging.exception(f"Error during face detection for {file_path}: {str(e)}")
            
            # Draw clickable rectangles for faces
            faces = self.db.get_faces(file_path)
            logging.debug(f"Retrieved {len(faces)} faces for {file_path}")
            if not faces:
                logging.warning(f"No faces found for {file_path}")
                canvas.create_text(
                    img_width // 2, img_height // 2,
                    text="No faces detected. Try another image.",
                    fill="yellow", font=('Arial', 14, 'bold'), tags="no_faces"
                )
            
            for i, face in enumerate(faces):
                try:
                    top = face.get('top', 0) or 0
                    right = face.get('right', 0) or 0
                    bottom = face.get('bottom', 0) or 0
                    left = face.get('left', 0) or 0
                    encoding = face['encoding']
                    name = face.get('name') or f"Face {i + 1}"
                    
                    logging.debug(f"Processing face {i+1} for {file_path}: ({left}, {top}, {right}, {bottom})")
                    
                    if top <= 0 or right <= 0 or bottom <= 0 or left <= 0:
                        logging.warning(f"Skipping invalid face coordinates for {file_path}: {top}, {right}, {bottom}, {left}")
                        continue
                    
                    # Scale coordinates
                    scale_x = img_width / orig_width
                    scale_y = img_height / orig_height
                    scaled_top = top * scale_y
                    scaled_right = right * scale_x
                    scaled_bottom = bottom * scale_y
                    scaled_left = left * scale_x
                    
                    logging.debug(f"Scaled coordinates for {file_path}: ({scaled_left}, {scaled_top}, {scaled_right}, {scaled_bottom})")
                    
                    # Create rectangle
                    rect_id = canvas.create_rectangle(
                        scaled_left, scaled_top, scaled_right, scaled_bottom,
                        outline='yellow', width=3, fill='', tags="face_rect"
                    )
                    
                    # Create label
                    label_id = canvas.create_text(
                        scaled_left + 5, scaled_top - 10,
                        text=name, anchor='sw', fill='yellow',
                        font=('Arial', 12, 'bold'), tags=f"label_{rect_id}"
                    )
                    
                    # Store for zoom
                    self.face_rects.append((rect_id, label_id, top, right, bottom, left))
                    
                    logging.debug(f"Created face rectangle {rect_id} for {file_path}")
                    
                except Exception as e:
                    logging.exception(f"Error drawing face rectangle for {file_path}: {str(e)}")
                    continue
            
            # Configure hover events
            def on_rect_enter(event, r_id, l_id):
                try:
                    canvas.itemconfig(r_id, state='normal')
                    canvas.itemconfig(l_id, state='normal')
                    logging.debug(f"Hover enter on rectangle {r_id}")
                except Exception as e:
                    logging.exception(f"Error in hover enter: {str(e)}")
            
            def on_rect_leave(event, r_id, l_id):
                try:
                    canvas.itemconfig(r_id, state='hidden')
                    canvas.itemconfig(l_id, state='hidden')
                    logging.debug(f"Hover leave on rectangle {r_id}")
                except Exception as e:
                    logging.exception(f"Error in hover leave: {str(e)}")
            
            # Apply bindings to all rectangles
            for rect_id, label_id, _, _, _, _ in self.face_rects:
                canvas.tag_bind(rect_id, '<Enter>', lambda e, r=rect_id, l=label_id: on_rect_enter(e, r, l))
                canvas.tag_bind(rect_id, '<Leave>', lambda e, r=rect_id, l=label_id: on_rect_leave(e, r, l))
                
                # Click event for naming
                def tag_face(event, f_path=file_path, enc=encoding, r_id=rect_id):
                    try:
                        dialog = tk.Toplevel(full_window)
                        dialog.title("Tag Face")
                        dialog.geometry("300x150")
                        dialog.transient(full_window)
                        dialog.grab_set()
                        
                        ttk.Label(dialog, text="Enter name for this face:").pack(pady=10)
                        name_var = tk.StringVar()
                        entry = ttk.Entry(dialog, textvariable=name_var)
                        entry.pack(pady=5)
                        entry.focus()
                        
                        def on_ok():
                            name = name_var.get().strip()
                            if name:
                                self.db.update_face_name(f_path, enc, name)
                                # Update caption
                                metadata = self.db.get_image_metadata(f_path) or {}
                                caption = metadata.get('detailed_caption', '')
                                new_caption = f"{caption} Person named {name}." if caption else f"Person named {name}."
                                self.db.add_image(
                                    f_path,
                                    metadata.get('date', ''),
                                    metadata.get('size', 0),
                                    metadata.get('location', ''),
                                    metadata.get('tags', ''),
                                    new_caption
                                )
                                canvas.itemconfig(f"label_{r_id}", text=name)
                                logging.info(f"Tagged face in {f_path} as {name}")
                            dialog.destroy()
                        
                        def on_cancel():
                            dialog.destroy()
                        
                        button_frame = ttk.Frame(dialog)
                        button_frame.pack(pady=10)
                        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
                        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
                        
                        logging.debug(f"Opened naming dialog for {f_path}")
                    except Exception as e:
                        logging.exception(f"Error in tag_face for {f_path}: {str(e)}")
                
                canvas.tag_bind(rect_id, '<Button-1>', tag_face)
            
            # Raise rectangles above image
            canvas.tag_raise("face_rect", "image")
            canvas.tag_raise("label", "face_rect")
            
            # Ensure canvas can receive events
            canvas.focus_set()
            
            # Mouse wheel scrolling
            def on_mouse_wheel(event):
                if event.delta > 0:
                    canvas.yview_scroll(-1, "units")
                elif event.delta < 0:
                    canvas.yview_scroll(1, "units")
            
            canvas.bind_all("<MouseWheel>", on_mouse_wheel)
            
            # Zoom function
            def _zoom_image(self, canvas, factor, file_path):
                try:
                    self.zoom_factor *= factor
                    if self.zoom_factor < 0.2:
                        self.zoom_factor = 0.2
                    elif self.zoom_factor > 5.0:
                        self.zoom_factor = 5.0
                    
                    # Resize image
                    new_width = int(orig_width * self.zoom_factor)
                    new_height = int(orig_height * self.zoom_factor)
                    resized_img = self.base_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    new_photo = ImageTk.PhotoImage(resized_img)
                    
                    canvas.delete("image")
                    canvas.create_image(0, 0, image=new_photo, anchor="nw", tags="image")
                    canvas.image = new_photo
                    
                    canvas.config(scrollregion=(0, 0, new_width, new_height))
                    
                    # Update face rectangles
                    canvas.delete("no_faces")
                    canvas.delete("face_rect")
                    for rect_id, label_id, _, _, _, _ in self.face_rects:
                        canvas.delete(rect_id)
                        canvas.delete(label_id)
                    
                    self.face_rects = []
                    faces = self.db.get_faces(file_path)
                    for i, face in enumerate(faces):
                        try:
                            top = face.get('top', 0) or 0
                            right = face.get('right', 0) or 0
                            bottom = face.get('bottom', 0) or 0
                            left = face.get('left', 0) or 0
                            encoding = face['encoding']
                            name = face.get('name') or f"Face {i + 1}"
                            
                            if top <= 0 or right <= 0 or bottom <= 0 or left <= 0:
                                logging.warning(f"Skipping invalid face coordinates for {file_path}: {top}, {right}, {bottom}, {left}")
                                continue
                            
                            # Scale coordinates
                            scale_x = new_width / orig_width
                            scale_y = new_height / orig_height
                            scaled_top = top * scale_y
                            scaled_right = right * scale_x
                            scaled_bottom = bottom * scale_y
                            scaled_left = left * scale_x
                            
                            rect_id = canvas.create_rectangle(
                                scaled_left, scaled_top, scaled_right, scaled_bottom,
                                outline='yellow', width=3, fill='', tags="face_rect"
                            )
                            
                            label_id = canvas.create_text(
                                scaled_left + 5, scaled_top - 10,
                                text=name, anchor='sw', fill='yellow',
                                font=('Arial', 12, 'bold'), tags=f"label_{rect_id}"
                            )
                            
                            canvas.tag_bind(rect_id, '<Enter>', lambda e, r=rect_id, l=label_id: on_rect_enter(e, r, l))
                            canvas.tag_bind(rect_id, '<Leave>', lambda e, r=rect_id, l=label_id: on_rect_leave(e, r, l))
                            
                            def tag_face(event, f_path=file_path, enc=encoding, r_id=rect_id):
                                dialog = tk.Toplevel(full_window)
                                dialog.title("Tag Face")
                                dialog.geometry("300x150")
                                dialog.transient(full_window)
                                dialog.grab_set()
                                
                                ttk.Label(dialog, text="Enter name for this face:").pack(pady=10)
                                name_var = tk.StringVar()
                                entry = ttk.Entry(dialog, textvariable=name_var)
                                entry.pack(pady=5)
                                entry.focus()
                                
                                def on_ok():
                                    name = name_var.get().strip()
                                    if name:
                                        self.db.update_face_name(f_path, enc, name)
                                        metadata = self.db.get_image_metadata(f_path) or {}
                                        caption = metadata.get('detailed_caption', '')
                                        new_caption = f"{caption} Person named {name}." if caption else f"Person named {name}."
                                        self.db.add_image(
                                            f_path,
                                            metadata.get('date', ''),
                                            metadata.get('size', 0),
                                            metadata.get('location', ''),
                                            metadata.get('tags', ''),
                                            new_caption
                                        )
                                        canvas.itemconfig(f"label_{r_id}", text=name)
                                        logging.info(f"Tagged face in {f_path} as {name}")
                                    dialog.destroy()
                                
                                def on_cancel():
                                    dialog.destroy()
                                
                                button_frame = ttk.Frame(dialog)
                                button_frame.pack(pady=10)
                                ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
                                ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
                            
                            canvas.tag_bind(rect_id, '<Button-1>', tag_face)
                            
                            self.face_rects.append((rect_id, label_id, top, right, bottom, left))
                            
                            logging.debug(f"Created zoomed face rectangle {rect_id} for {file_path}")
                        except Exception as e:
                            logging.exception(f"Error updating face rectangle for {file_path}: {str(e)}")
                    
                    # Raise rectangles
                    canvas.tag_raise("face_rect", "image")
                    canvas.tag_raise("label", "face_rect")
                    
                    if not faces:
                        canvas.create_text(
                            new_width // 2, new_height // 2,
                            text="No faces detected. Try another image.",
                            fill="yellow", font=('Arial', 14, 'bold'), tags="no_faces"
                        )
                
                except Exception as e:
                    logging.exception(f"Error zooming image {file_path}: {str(e)}")
            
            self._zoom_image = _zoom_image
            
            def on_closing():
                full_window.destroy()
                canvas.unbind_all("<MouseWheel>")
                canvas.yview_scroll = lambda *args, **kwargs: None
                canvas.xview_scroll = lambda *args, **kwargs: None
                logging.debug(f"Closed full image window for {file_path}")
            
            full_window.protocol("WM_DELETE_WINDOW", on_closing)
            
            logging.info(f"Opened full image window for {file_path}")
            
        except Exception as e:
            logging.exception(f"Error opening full image {file_path}: {str(e)}")
            self.status_var.set(f"Error opening image: {str(e)}")

    def search_photos(self, event=None):
        try:
            if not self.photo_manager:
                self.status_var.set("Please wait for models to load")
                return
            query = self.search_var.get()
            self.status_var.set(f"Searching for '{query}'...")
            photos = self.photo_manager.search_photos(query)
            self.display_photos(photos)
            self.status_var.set(f"Found {len(photos)} photos")
            logging.info(f"Search completed for query: {query}")
        except Exception as e:
            self.status_var.set(f"Error searching: {str(e)}")
            logging.exception(f"Error searching with query '{query}': {str(e)}")

    def sort_photos(self, sort_by: str):
        try:
            if not self.photo_manager:
                self.status_var.set("Please wait for models to load")
                return
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
                    # Check if caption exists in database
                    metadata = self.db.get_image_metadata(file_path)
                    if metadata and metadata.get('detailed_caption'):
                        caption = metadata['detailed_caption']
                        self.root.after(0, lambda: caption_label.config(text=caption))
                        logging.debug(f"Loaded existing caption for {file_path}")
                    elif not self.caption_generator or not self.caption_generator.is_initialized():
                        self.root.after(0, lambda: caption_label.config(text="Caption unavailable: Florence-2 model not loaded"))
                        logging.warning(f"Florence-2 model not loaded for {file_path}")
                    else:
                        caption = self.caption_generator.generate_image_caption(file_path)
                        self.root.after(0, lambda: caption_label.config(text=caption))
                        
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