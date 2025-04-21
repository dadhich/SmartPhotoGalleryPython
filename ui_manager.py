import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import logging
import math
from typing import Callable
from photo_manager import PhotoManager
from caption_generator import CaptionGenerator
from database import ImageDatabase

class LoadingSpinner:
    def __init__(self, parent, label: ttk.Label, prefix: str = "Loading"):
        self.parent = parent
        self.label = label
        self.prefix = prefix
        self.frames = ["-", "\\", "|", "/"]
        self.current_frame = 0
        self.running = False

    def start(self):
        if not self.running:
            self.running = True
            self.update()

    def stop(self):
        self.running = False
        self.label.config(text="")

    def update(self):
        if self.running:
            self.label.config(text=f"{self.prefix} {self.frames[self.current_frame]}")
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.parent.after(100, self.update)

class UIManager:
    def __init__(self, root: tk.Tk, photo_manager: PhotoManager, caption_generator: CaptionGenerator, db: ImageDatabase):
        self.root = root
        self.photo_manager = photo_manager
        self.caption_generator = caption_generator
        self.db = db
        self.thumbnail_size = (150, 150)
        self.displayed_photos = []
        
        self.setup_gui()

    def setup_gui(self):
        try:
            self.root.configure(bg="#f0f2f5")
            style = ttk.Style()
            style.configure("TButton", padding=10, font=("Helvetica", 12))
            style.configure("TLabel", font=("Helvetica", 11), background="#f0f2f5")
            style.configure("TCombobox", font=("Helvetica", 11))

            self.main_frame = ttk.Frame(self.root, padding="20", style="TFrame")
            self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            self.folder_frame = ttk.Frame(self.main_frame)
            self.folder_frame.grid(row=0, column=0, sticky=tk.W, pady=10)
            
            self.folder_button = ttk.Button(
                self.folder_frame, 
                text="Select Folder", 
                command=self.select_folder,
                style="TButton"
            )
            self.folder_button.grid(row=0, column=0, padx=10)
            
            self.folder_label = ttk.Label(self.folder_frame, text="No folder selected", style="TLabel")
            self.folder_label.grid(row=0, column=1, padx=10)
            
            self.folder_spinner_label = ttk.Label(self.folder_frame, text="", style="TLabel")
            self.folder_spinner_label.grid(row=0, column=2, padx=10)
            self.folder_spinner = LoadingSpinner(self.root, self.folder_spinner_label, "Loading")
            
            self.search_frame = ttk.Frame(self.main_frame)
            self.search_frame.grid(row=1, column=0, sticky=tk.W, pady=10)
            
            self.search_entry = ttk.Entry(self.search_frame, width=50, font=("Helvetica", 11))
            self.search_entry.grid(row=0, column=0, padx=10)
            self.search_entry.insert(0, "Enter search query (e.g., 'photos with dogs')")
            self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.delete(0, tk.END) if self.search_entry.get() == "Enter search query (e.g., 'photos with dogs')" else None)
            self.search_entry.bind("<Return>", lambda e: self.search_photos())
            
            self.search_button = ttk.Button(
                self.search_frame, 
                text="Search", 
                command=self.search_photos,
                style="TButton"
            )
            self.search_button.grid(row=0, column=1, padx=10)
            
            self.search_spinner_label = ttk.Label(self.search_frame, text="", style="TLabel")
            self.search_spinner_label.grid(row=0, column=2, padx=10)
            self.search_spinner = LoadingSpinner(self.root, self.search_spinner_label, "Searching")
            
            self.sort_frame = ttk.Frame(self.main_frame)
            self.sort_frame.grid(row=2, column=0, sticky=tk.W, pady=10)
            
            ttk.Label(self.sort_frame, text="Sort by:", style="TLabel").grid(row=0, column=0, padx=10)
            self.sort_combo = ttk.Combobox(
                self.sort_frame, 
                values=["Date", "Size", "Name"],
                state="readonly",
                width=10,
                style="TCombobox"
            )
            self.sort_combo.set("Date")
            self.sort_combo.grid(row=0, column=1, padx=10)
            self.sort_combo.bind("<<ComboboxSelected>>", self.on_sort_change)
            
            self.canvas = tk.Canvas(self.main_frame, bg="#ffffff", highlightthickness=0, borderwidth=0)
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
            
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_grid)
            self.canvas.bind_all("<Button-4>", self._on_mousewheel_grid)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel_grid)
            
            self.canvas.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self.scrollbar.grid(row=3, column=1, sticky=(tk.N, tk.S))
            
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            self.main_frame.columnconfigure(0, weight=1)
            self.main_frame.rowconfigure(3, weight=1)
            
            logging.info("GUI setup completed successfully")
            
        except Exception as e:
            logging.error(f"Error setting up GUI: {str(e)}")
            self.show_error("Failed to initialize GUI")

    def _on_mousewheel_grid(self, event):
        try:
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
                self.folder_spinner.start()
                self.root.after(100, lambda: self.load_and_display_photos(folder))
                logging.info(f"Selected folder: {folder}")
        except Exception as e:
            logging.error(f"Error selecting folder: {str(e)}")
            self.show_error("Failed to select folder")

    def load_and_display_photos(self, folder: str):
        try:
            self.photo_manager.load_photos(folder)
            self.displayed_photos = self.photo_manager.photos
            self.display_photos()
        except Exception as e:
            self.show_error("Failed to load photos")
        finally:
            self.folder_spinner.stop()

    def search_photos(self):
        try:
            query = self.search_entry.get().strip()
            if not query:
                self.displayed_photos = self.photo_manager.photos
                self.display_photos()
                return
            
            self.search_spinner.start()
            self.root.after(100, lambda: self.execute_search(query))
        except Exception as e:
            logging.error(f"Error initiating search: {str(e)}")
            self.show_error("Failed to search photos")

    def execute_search(self, query: str):
        try:
            self.displayed_photos = self.photo_manager.search_photos(query)
            self.display_photos()
        except Exception as e:
            logging.error(f"Error executing search: {str(e)}")
            self.show_error("Failed to execute search")
        finally:
            self.search_spinner.stop()

    def display_photos(self):
        try:
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
            if not self.displayed_photos:
                ttk.Label(self.scrollable_frame, text="No photos found", style="TLabel").grid(row=0, column=0)
                return
            
            canvas_width = self.canvas.winfo_width() or 1200
            cols = max(1, canvas_width // (self.thumbnail_size[0] + 20))
            
            for i, (file_path, date, size, location, tags) in enumerate(self.displayed_photos):
                try:
                    img = Image.open(file_path)
                    img.thumbnail(self.thumbnail_size)
                    photo = ImageTk.PhotoImage(img)
                    
                    photo_frame = ttk.Frame(self.scrollable_frame)
                    photo_frame.grid(row=i // cols, column=i % cols, padx=10, pady=10)
                    
                    label = ttk.Label(photo_frame, image=photo)
                    label.image = photo
                    label.grid(row=0, column=0)
                    label.bind("<Double-1>", lambda e, path=file_path: self.open_full_image(path))
                    
                    ttk.Label(
                        photo_frame, 
                        text=f"Date: {date.strftime('%Y-%m-%d')}",
                        style="TLabel"
                    ).grid(row=1, column=0)
                    ttk.Label(
                        photo_frame, 
                        text=f"Size: {size / 1024:.1f} KB",
                        style="TLabel"
                    ).grid(row=2, column=0)
                    ttk.Label(
                        photo_frame, 
                        text=f"Location: {location}",
                        style="TLabel"
                    ).grid(row=3, column=0)
                    ttk.Label(
                        photo_frame, 
                        text=f"Tags: {tags}",
                        style="TLabel"
                    ).grid(row=4, column=0)
                except Exception as e:
                    logging.warning(f"Error displaying photo {file_path}: {str(e)}")
                    continue
            
            logging.info(f"Displayed {len(self.displayed_photos)} photos")
            
        except Exception as e:
            logging.error(f"Error displaying photos: {str(e)}")
            self.show_error("Failed to display photos")

    def on_sort_change(self, event):
        try:
            self.photo_manager.set_sort(self.sort_combo.get())
            self.displayed_photos = self.photo_manager.photos
            self.display_photos()
            logging.info(f"Sort changed to {self.photo_manager.current_sort}")
        except Exception as e:
            logging.error(f"Error changing sort: {str(e)}")
            self.show_error("Failed to change sort order")

    def open_full_image(self, file_path: str):
        try:
            full_image_window = tk.Toplevel(self.root)
            full_image_window.title("Full Image View")
            full_image_window.geometry("800x600")
            full_image_window.configure(bg="#f0f2f5")
            
            original_img = Image.open(file_path)
            
            caption_frame = ttk.Frame(full_image_window)
            caption_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
            caption_spinner_label = ttk.Label(caption_frame, text="", style="TLabel")
            caption_spinner_label.grid(row=0, column=0, padx=10)
            caption_spinner = LoadingSpinner(full_image_window, caption_spinner_label, "Generating")
            
            # Check database for cached caption
            metadata = self.db.get_image_metadata(file_path)
            caption = metadata.get("detailed_caption") if metadata else None
            
            def set_caption():
                nonlocal caption
                if not caption:
                    caption_spinner.start()
                    caption = self.caption_generator.generate_image_caption(file_path)
                    self.db.update_detailed_caption(file_path, caption)
                caption_label.config(text=caption)
                caption_spinner.stop()
            
            full_image_window.after(100, set_caption)
            
            zoom_factor = 1.0
            max_zoom = 3.0
            min_zoom = 0.3
            
            canvas = tk.Canvas(full_image_window, bg="#ffffff", highlightthickness=0)
            v_scrollbar = ttk.Scrollbar(full_image_window, orient=tk.VERTICAL, command=canvas.yview)
            h_scrollbar = ttk.Scrollbar(full_image_window, orient=tk.HORIZONTAL, command=canvas.xview)
            
            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
            h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
            
            full_image_window.columnconfigure(0, weight=1)
            full_image_window.rowconfigure(0, weight=1)
            
            image_frame = ttk.Frame(canvas)
            canvas.create_window((0, 0), window=image_frame, anchor="nw")
            
            image_label = ttk.Label(image_frame)
            image_label.grid(row=0, column=0, padx=10, pady=10)
            
            caption_label = ttk.Label(image_frame, text="Generating caption...", wraplength=780, style="TLabel")
            caption_label.grid(row=1, column=0, pady=5)
            
            def update_image():
                try:
                    new_size = (
                        int(original_img.width * zoom_factor),
                        int(original_img.height * zoom_factor)
                    )
                    resized_img = original_img.resize(new_size, Image.LANCZOS)
                    photo = ImageTk.PhotoImage(resized_img)
                    image_label.configure(image=photo)
                    image_label.image = photo
                    canvas.configure(scrollregion=(0, 0, new_size[0], new_size[1] + 100))
                    logging.info(f"Image zoomed to factor {zoom_factor} for {file_path}")
                except Exception as e:
                    logging.error(f"Error updating zoomed image: {str(e)}")
                    self.show_error("Failed to update zoomed image")
            
            update_image()
            
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
            
            def configure_canvas(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
            
            image_frame.bind("<Configure>", configure_canvas)
            
            control_frame = ttk.Frame(full_image_window)
            control_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
            
            ttk.Button(
                control_frame,
                text="Zoom In",
                command=lambda: adjust_zoom(0.2),
                style="TButton"
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                control_frame,
                text="Zoom Out",
                command=lambda: adjust_zoom(-0.2),
                style="TButton"
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                control_frame,
                text="Reset Zoom",
                command=lambda: adjust_zoom(reset=True),
                style="TButton"
            ).pack(side=tk.LEFT, padx=5)
            
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
        messagebox.showerror("Error", message)
        logging.error(f"Displayed error message: {message}")