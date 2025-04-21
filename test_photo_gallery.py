import unittest
from unittest.mock import Mock, patch
import os
from datetime import datetime
from PIL import Image
from photo_manager import PhotoManager
from caption_generator import CaptionGenerator
from ui_manager import UIManager
import tkinter as tk

class TestPhotoGallery(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.photo_manager = PhotoManager()
        self.caption_generator = CaptionGenerator()

    def tearDown(self):
        self.root.destroy()

    def test_photo_manager_load_photos(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [
                ('/test', [], ['test.jpg'])
            ]
            with patch('os.stat') as mock_stat:
                mock_stat.return_value = Mock(st_mtime=1630000000, st_size=1024)
                with patch('exifread.process_file') as mock_exif:
                    mock_exif.return_value = {}
                    self.photo_manager.load_photos('/test')
                    self.assertEqual(len(self.photo_manager.photos), 1)
                    self.assertEqual(self.photo_manager.photos[0][0], '/test/test.jpg')
                    self.assertEqual(self.photo_manager.photos[0][2], 1024)
                    self.assertEqual(self.photo_manager.photos[0][3], "Unknown")

    def test_photo_manager_sort_photos(self):
        self.photo_manager.photos = [
            ('img1.jpg', datetime(2023, 1, 2), 1024, "Unknown"),
            ('img2.jpg', datetime(2023, 1, 1), 2048, "Unknown")
        ]
        self.photo_manager.set_sort("Date")
        self.assertEqual(self.photo_manager.photos[0][0], 'img1.jpg')
        self.photo_manager.set_sort("Size")
        self.assertEqual(self.photo_manager.photos[0][0], 'img2.jpg')
        self.photo_manager.set_sort("Name")
        self.assertEqual(self.photo_manager.photos[0][0], 'img1.jpg')

    def test_caption_generator_load_model(self):
        with patch('transformers.AutoProcessor.from_pretrained') as mock_processor, \
             patch('transformers.AutoModelForCausalLM.from_pretrained') as mock_model:
            caption_generator = CaptionGenerator()
            mock_processor.assert_called_once()
            mock_model.assert_called_once()

    def test_caption_generator_generate_caption(self):
        with patch.object(self.caption_generator, 'model', None):
            caption = self.caption_generator.generate_image_caption("test.jpg")
            self.assertEqual(caption, "Caption unavailable: Model not loaded")
        
        with patch('PIL.Image.open') as mock_open, \
             patch.object(self.caption_generator, 'processor') as mock_processor, \
             patch.object(self.caption_generator, 'model') as mock_model:
            mock_open.return_value.convert.return_value = Mock()
            mock_processor.return_value = {"input_ids": [], "pixel_values": []}
            mock_model.generate.return_value = [0]
            mock_processor.batch_decode.return_value = ["A dog runs in a park with trees."]
            caption = self.caption_generator.generate_image_caption("test.jpg")
            self.assertTrue(caption.startswith("In the image, a dog runs in a park with trees"))
            self.assertTrue(caption.endswith("."))

    def test_ui_manager_display_photos(self):
        ui_manager = UIManager(self.root, self.photo_manager, self.caption_generator)
        self.photo_manager.photos = [
            ('test.jpg', datetime.now(), 1024, "Unknown")
        ]
        with patch('PIL.Image.open') as mock_open:
            mock_open.return_value.thumbnail = Mock()
            mock_open.return_value.size = (150, 150)
            ui_manager.display_photos()
            self.assertTrue(len(ui_manager.scrollable_frame.winfo_children()) > 0)

if __name__ == '__main__':
    unittest.main()