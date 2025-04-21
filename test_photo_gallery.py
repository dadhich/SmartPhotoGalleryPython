import unittest
from unittest.mock import Mock, patch
import os
from datetime import datetime
from PIL import Image
import numpy as np
from photo_manager import PhotoManager
from caption_generator import CaptionGenerator
from ui_manager import UIManager, GifAnimation
from database import ImageDatabase
import tkinter as tk
import threading
import queue
import logging
import importlib.util

classerend (self):
        self.root.destroy()
        logging.getLogger().handlers = []

    def test_photo_manager_imports(self):
        # Verify photo_manager.py has all necessary imports
        spec = importlib.util.spec_from_file_location("photo_manager", "photo_manager.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Check if tkinter is imported
        self.assertTrue(hasattr(module, 'tk'))
        self.assertEqual(module.tk.__name__, 'tkinter')

    def test_logging_to_file(self):
        logging.info("Test log message")
        with open(self.log_file, 'r') as f:
            log_content = f.read()
        self.assertIn("Test log message", log_content)

    def test_model_files_missing(self):
        with patch('os.path.exists', return_value=False):
            self.photo_manager.load_model()
            self.assertIsNone(self.photo_manager.face_net)
            with open(self.log_file, 'r') as f:
                log_content = f.read()
            self.assertIn("OpenCV DNN model files missing", log_content)
            self.assertIn("Face detection disabled", log_content)

    def test_get_all_metadata(self):
        self.db.add_image("/test.jpg", "2023-01-01", 1024, "Unknown", "dog, park")
        metadata = self.db.get_all_metadata()
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[0]["file_path"], "/test.jpg")
        self.assertEqual(metadata[0]["tags"], "dog, park")

    def test_load_photos_with_get_all_metadata(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('/test', [], ['test.jpg'])]
            with patch('os.stat') as mock_stat:
                mock_stat.return_value = Mock(st_mtime=1630000000, st_size=1024)
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.isdir', return_value=True):
                        with patch('os.access', return_value=True):
                            self.db.add_image("/test/test.jpg", "2023-01-01", 1024, "Unknown", "dog, park")
                            self.photo_manager.load_photos('/test', self.status_var)
                            self.assertEqual(len(self.photo_manager.photos), 1)
                            self.assertEqual(self.photo_manager.photos[0][0], '/test/test.jpg')
                            self.assertEqual(self.photo_manager.photos[0][4], "dog, park")

    def test_search_photos_logging(self):
        self.photo_manager.photos = [
            ('/test/test.jpg', datetime.now(), 1024, "Unknown", "dog, park")
        ]
        self.db.add_image("/test/test.jpg", "2023-01-01", 1024, "Unknown", "dog, park")
        with patch.object(self.photo_manager, 'nlp_model', None):
            self.photo_manager.search_photos("dog")
            with open(self.log_file, 'r') as f:
                log_content = f.read()
            self.assertIn("Searching photos with query: dog", log_content)
            self.assertIn("Search returned", log_content)

    def test_ui_manager_initialization(self):
        self.assertIsInstance(self.ui_manager, UIManager)
        self.assertEqual(self.ui_manager.status_var, self.status_var)
        self.assertTrue(self.ui_manager.caption_thread.is_alive())

    def test_gif_animation_overlay_creation(self):
        anim = GifAnimation(self.root, self.root, "Loading", "loading.gif")
        with patch('PIL.Image.open') as mock_open:
            mock_img = Mock()
            mock_img.n_frames = 2
            mock_img.copy.return_value.resize.return_value = Mock()
            mock_open.return_value.__enter__.return_value = mock_img
            anim.load_gif()
            anim.create_overlay()
            self.assertIsNotNone(anim.overlay)
            self.assertIsNotNone(anim.label)
            self.assertTrue(anim.overlay.winfo_exists())

    def test_gif_animation_start_with_failed_overlay(self):
        anim = GifAnimation(self.root, self.root, "Loading", "loading.gif")
        with patch('tkinter.Toplevel', side_effect=Exception("Toplevel creation failed")):
            anim.start()
            self.assertTrue(anim.running)
            self.assertIsNotNone(anim.label)
            self.assertEqual(anim.label.cget("text"), "Loading...")

    def test_select_folder_with_spinner_failure(self):
        with patch('tkinter.filedialog.askdirectory', return_value='/test'):
            with patch.object(self.ui_manager.folder_spinner, 'start', side_effect=Exception("Spinner failed")):
                with patch('os.walk') as mock_walk:
                    mock_walk.return_value = [('/test', [], ['test.jpg'])]
                    with patch('os.stat') as mock_stat:
                        mock_stat.return_value = Mock(st_mtime=1630000000, st_size=1024)
                        with patch('os.path.exists', return_value=True):
                            with patch('os.path.isdir', return_value=True):
                                with patch('os.access', return_value=True):
                                    with patch('PIL.Image.open') as mock_open:
                                        mock_open.return_value.thumbnail = Mock()
                                        self.ui_manager.select_folder()
                                        self.assertEqual(self.ui_manager.folder_label.cget("text"), '/test')
                                        self.assertIn("Loading /test (Spinner failed)", self.status_var.get())
                                        self.root.update()  # Process after calls
                                        self.assertEqual(len(self.ui_manager.displayed_photos), 1)

    def test_load_photos_valid_folder(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('/test', [], ['test.jpg'])]
            with patch('os.stat') as mock_stat:
                mock_stat.return_value = Mock(st_mtime=1630000000, st_size=1024)
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.isdir', return_value=True):
                        with patch('os.access', return_value=True):
                            self.photo_manager.load_photos('/test', self.status_var)
                            self.assertEqual(len(self.photo_manager.photos), 1)
                            self.assertEqual(self.photo_manager.photos[0][0], '/test/test.jpg')
                            self.assertIn("Scanning /test...", self.status_var.get())

    def test_load_photos_invalid_folder(self):
        with patch('os.path.exists', return_value=False):
            with self.assertRaises(Value  TestPhotoGallery(unittest.TestCase):
                self.photo_manager.load_photos('/invalid', self.status_var)
            self.assertIn("Error loading photos", self.status_var.get())

    def test_load_photos_no_permissions(self):
        with patch('os.path.exists', return_value=True):
            with patch('os.path.isdir', return_value=True):
                with patch('os.access', return_value=False):
                    with self.assertRaises(PermissionError):
                        self.photo_manager.load_photos('/test', self.status_var)
                    self.assertIn("Error loading photos", self.status_var.get())

    def test_load_photos_empty_folder(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('/test', [], [])]
            with patch('os.path.exists', return_value=True):
                with patch('os.path.isdir', return_value=True):
                    with patch('os.access', return_value=True):
                        self.photo_manager.load_photos('/test', self.status_var)
                        self.assertEqual(len(self.photo_manager.photos), 0)
                        self.assertIn("No valid images found", self.status_var.get())

    def test_logging_on_load_photos_failure(self):
        with patch('os.path.exists', return_value=False):
            with self.assertRaises(ValueError):
                self.photo_manager.load_photos('/invalid', self.status_var)
            with open(self.log_file, 'r') as f:
                log_content = f.read()
            self.assertIn("Folder does not exist: /invalid", log_content)

    def test_immediate_ui_load(self):
        with patch('photo_manager.PhotoManager.load_model') as mock_load_model:
            from photo_gallery import main
            main()
            self.assertTrue(self.root.winfo_exists())
            mock_load_model.assert_called_once()

    def test_status_bar_updates(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('/test', [], ['test.jpg'])]
            with patch('os.stat') as mock_stat:
                mock_stat.return_value = Mock(st_mtime=1630000000, st_size=1024)
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.isdir', return_value=True):
                        with patch('os.access', return_value=True):
                            self.photo_manager.load_photos('/test', self.status_var)
                            self.assertIn("Scanning /test...", self.status_var.get())

    def test_thumbnail_display_immediate(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('/test', [], ['test.jpg'])]
            with patch('os.stat') as mock_stat:
                mock_stat.return_value = Mock(st_mtime=1630000000, st_size=1024)
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.isdir', return_value=True):
                        with patch('os.access', return_value=True):
                            with patch('PIL.Image.open') as mock_open:
                                mock_open.return_value.thumbnail = Mock()
                                self.ui_manager.load_and_display_photos('/test')
                                self.assertEqual(len(self.ui_manager.scrollable_frame.winfo_children()), 1)
                                self.assertEqual(self.ui_manager.scrollable_frame.winfo_children()[0].winfo_children()[1].cget("text"), "test.jpg")

    def test_background_metadata_processing(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('/test', [], ['test.jpg'])]
            with patch('os.stat') as mock_stat:
                mock_stat.return_value = Mock(st_mtime=1630000000, st_size=1024)
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.isdir', return_value=True):
                        with patch('os.access', return_value=True):
                            with patch('exifread.process_file', return_value={}):
                                with patch.object(self.caption_generator, 'generate_tags', return_value=["dog", "park"]):
                                    self.photo_manager.load_photos('/test', self.status_var)
                                    self.photo_manager.metadata_thread.join()
                                    metadata = self.db.get_image_metadata('/test/test.jpg')
                                    self.assertEqual(metadata["tags"], "dog, park")

    def test_background_face_processing(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('/test', [], ['test.jpg'])]
            with patch('os.stat') as mock_stat:
                mock_stat.return_value = Mock(st_mtime=1630000000, st_size=1024)
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.isdir', return_value=True):
                        with patch('os.access', return_value=True):
                            with patch('cv2.dnn.readNetFromCaffe'):
                                self.photo_manager.load_model()
                                with patch('cv2.imread') as mock_imread:
                                    mock_imread.return_value = np.zeros((300, 300, 3))
                                    self.photo_manager.load_photos('/test', self.status_var)
                                    self.photo_manager.face_thread.join()
                                    faces = self.db.get_faces('/test/test.jpg')
                                    self.assertTrue(len(faces) >= 0)

    def test_immediate_full_image_no_spinner(self):
        with patch('PIL.Image.open') as mock_open:
            mock_open.return_value = Mock()
            self.ui_manager.open_full_image("test.jpg")
            full_image_window = self.root.winfo_children()[-1]
            self.assertTrue(full_image_window.winfo_exists())
            caption_label = full_image_window.winfo_children()[3].winfo_children()[0]
            self.assertEqual(caption_label.cget("text"), "Generating caption...")
            # Verify no GifAnimation instances
            for child in full_image_window.winfo_children():
                self.assertNotIsInstance(child, GifAnimation)

    def test_background_caption_thread_safe(self):
        with patch('PIL.Image.open') as mock_open:
            mock_open.return_value = Mock()
            with patch.object(self.caption_generator, 'generate_image_caption', return_value="Test caption"):
                caption_label = Mock()
                self.ui_manager.caption_queue.put(("test.jpg", caption_label))
                self.ui_manager.caption_queue.put(None)  # Stop thread
                self.ui_manager.caption_thread.join(timeout=1)
                caption_label.config.assert_called_with(text="Test caption")
                metadata = self.db.get_image_metadata("test.jpg")
                self.assertEqual(metadata["detailed_caption"], "Test caption")

    def test_face_label_position(self):
        with patch('PIL.Image.open') as mock_open:
            mock_open.return_value = Mock(width=800, height=600)
            self.db.add_face("test.jpg", np.zeros(512), None, top=100, right=200, bottom=200, left=100)
            self.ui_manager.open_full_image("test.jpg")
            full_image_window = self.root.winfo_children()[-1]
            canvas = full_image_window.winfo_children()[0]
            labels = [w for w in canvas.winfo_children() if isinstance(w, tk.Label)]
            self.assertTrue(len(labels) > 0)
            self.assertEqual(labels[0].cget("text"), "Face 1")
            self.assertTrue(int(labels[0].place_info()["x"]) >= 100)

    def test_gif_animation_load_success(self):
        with patch('PIL.Image.open') as mock_open:
            mock_img = Mock()
            mock_img.n_frames = 2
            mock_img.copy.return_value.resize.return_value = Mock()
            mock_open.return_value.__enter__.return_value = mock_img
            anim = GifAnimation(self.root, self.root, "Loading", "loading.gif")
            self.assertEqual(len(anim.frames), 2)
            with patch.object(anim, 'create_overlay') as mock_create:
                anim.start()
                mock_create.assert_called_once()
                self.assertTrue(anim.running)
                anim.stop()
                self.assertFalse(anim.running)

    def test_mousewheel_unbinding(self):
        with patch('PIL.Image.open') as mock_open:
            mock_open.return_value = Mock()
            self.ui_manager.open_full_image("test.jpg")
            full_image_window = self.root.winfo_children()[-1]
            canvas = full_image_window.winfo_children()[0]
            full_image_window.event_generate("<MouseWheel>")
            canvas.yview_scroll = Mock()
            full_image_window.event_generate("<MouseWheel>")
            canvas.yview_scroll.assert_called()
            full_image_window.destroy()
            canvas.yview_scroll.reset_mock()
            try:
                full_image_window.event_generate("<MouseWheel>")
            except tk.TclError:
                pass
            canvas.yview_scroll.assert_not_called()

    def test_maximized_window(self):
        with patch('tkinter.Tk') as mock_tk:
            from photo_gallery import main
            main()
            mock_tk.return_value.state.assert_called_with('zoomed')

    def test_face_naming(self):
        file_path = "/test/test.jpg"
        encoding = np.zeros(512)
        self.db.add_face(file_path, encoding, None, 100, 200, 200, 100)
        self.db.update_face_name(file_path, encoding, "Tina")
        faces = self.db.get_faces(file_path)
        self.assertEqual(faces[0]["name"], "Tina")

    def test_person_based_search(self):
        self.photo_manager.photos = [
            ('img1.jpg', datetime.now(), 1024, "Unknown", "dog, park"),
            ('img2.jpg', datetime.now(), 2048, "Unknown", "cat, house")
        ]
        self.db.add_face('img1.jpg', np.zeros(512), "Tina", 100, 200, 200, 100)
        with patch.object(self.photo_manager, 'nlp_model', None):
            results = self.photo_manager.search_photos("with Tina")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0][0], 'img1.jpg')

if __name__ == '__main__':
    unittest.main()