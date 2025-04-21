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
        self.caption_generator = CaptionGenerator()
        self.photo_manager = PhotoManager(self.caption_generator)
        self.ui_manager = UIManager(self.root, self.photo_manager, self.caption_generator)

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
                    with patch.object(self.caption_generator, 'generate_batch_captions') as mock_captions:
                        mock_captions.return_value = ["In the image, a dog in a park."]
                        self.photo_manager.load_photos('/test')
                        self.assertEqual(len(self.photo_manager.photos), 1)
                        self.assertEqual(self.photo_manager.photos[0][0], '/test/test.jpg')
                        self.assertEqual(self.photo_manager.photos[0][2], 1024)
                        self.assertEqual(self.photo_manager.photos[0][3], "Unknown")
                        self.assertEqual(self.photo_manager.photos[0][4], "In the image, a dog in a park.")

    def test_photo_manager_sort_photos(self):
        self.photo_manager.photos = [
            ('img1.jpg', datetime(2023, 1, 2), 1024, "Unknown", "Caption 1"),
            ('img2.jpg', datetime(2023, 1, 1), 2048, "Unknown", "Caption 2")
        ]
        self.photo_manager.set_sort("Date")
        self.assertEqual(self.photo_manager.photos[0][0], 'img1.jpg')
        self.photo_manager.set_sort("Size")
        self.assertEqual(self.photo_manager.photos[0][0], 'img2.jpg')
        self.photo_manager.set_sort("Name")
        self.assertEqual(self.photo_manager.photos[0][0], 'img1.jpg')

    def test_photo_manager_search_photos(self):
        self.photo_manager.photos = [
            ('img1.jpg', datetime.now(), 1024, "Unknown", "In the image, four people at a party."),
            ('img2.jpg', datetime.now(), 2048, "Unknown", "In the image, a dog in a park.")
        ]
        with patch.object(self.photo_manager.nlp_model, 'encode') as mock_encode:
            mock_encode.side_effect = [
                Mock(),  # Query embedding
                [Mock(), Mock()]  # Caption embeddings
            ]
            with patch('sentence_transformers.util.cos_sim') as mock_cos_sim:
                mock_cos_sim.return_value = [[0.8, 0.2]]  # High score for first photo
                results = self.photo_manager.search_photos("four people")
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0][0], 'img1.jpg')

    def test_caption_generator_load_model(self):
        with patch('transformers.AutoProcessor.from_pretrained') as mock_processor, \
             patch('transformers.AutoModelForCausalLM.from_pretrained') as mock_model:
            caption_generator = CaptionGenerator()
            mock_processor.assert_called_once()
            mock_model.assert_called_once()

    def test_caption_generator_generate_caption(self):
        with patch.object(self.caption_generator, 'model', None):
            caption = self.caption_generator.generate_image_caption("test.jpg")
            self.assertEqual(caption, "Caption unavailable: Model not loaded. Ensure all dependencies (transformers, einops, timm) are installed.")
        
        with patch('PIL.Image.open') as mock_open, \
             patch.object(self.caption_generator, 'processor') as mock_processor, \
             patch.object(self.caption_generator, 'model') as mock_model:
            mock_open.return_value.convert.return_value = Mock()
            mock_processor.return_value = {"input_ids": [], "pixel_values": []}
            mock_model.generate.return_value = [0]
            mock_processor.batch_decode.return_value = ["A dog runs in a park."]
            caption = self.caption_generator.generate_image_caption("test.jpg")
            self.assertTrue(caption.startswith("In the image, a dog runs in a park"))
            self.assertTrue(caption.endswith("."))

    def test_caption_generator_batch_captions(self):
        with patch.object(self.caption_generator, 'generate_image_caption') as mock_caption:
            mock_caption.side_effect = [
                "In the image, caption 1.",
                "In the image, caption 2."
            ]
            captions = self.caption_generator.generate_batch_captions(["img1.jpg", "img2.jpg"])
            self.assertEqual(len(captions), 2)
            self.assertEqual(captions[0], "In the image, caption 1.")

    def test_ui_manager_display_photos(self):
        self.photo_manager.photos = [
            ('test.jpg', datetime.now(), 1024, "Unknown", "In the image, a dog.")
        ]
        with patch('PIL.Image.open') as mock_open:
            mock_open.return_value.thumbnail = Mock()
            mock_open.return_value.size = (150, 150)
            self.ui_manager.display_photos()
            self.assertTrue(len(self.ui_manager.scrollable_frame.winfo_children()) > 0)

if __name__ == '__main__':
    unittest.main()