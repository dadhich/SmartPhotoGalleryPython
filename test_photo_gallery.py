import unittest
from unittest.mock import Mock, patch
import os
from datetime import datetime
from PIL import Image
from photo_manager import PhotoManager
from caption_generator import CaptionGenerator
from ui_manager import UIManager
from database import ImageDatabase
import tkinter as tk
import sqlite3

class TestPhotoGallery(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.db = ImageDatabase(":memory:")  # In-memory database for tests
        self.caption_generator = CaptionGenerator()
        self.photo_manager = PhotoManager(self.caption_generator, self.db)
        self.ui_manager = UIManager(self.root, self.photo_manager, self.caption_generator, self.db)

    def tearDown(self):
        self.root.destroy()

    def test_database_add_and_retrieve_metadata(self):
        metadata = {
            "file_path": "/test/test.jpg",
            "modified_time": datetime(2023, 1, 1),
            "file_size": 1024,
            "location": "Unknown",
            "tags": "dog, park",
            "detailed_caption": None
        }
        self.db.add_image_metadata(metadata)
        retrieved = self.db.get_image_metadata("/test/test.jpg")
        self.assertEqual(retrieved["file_path"], metadata["file_path"])
        self.assertEqual(retrieved["tags"], metadata["tags"])

    def test_photo_manager_load_photos(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [
                ('/test', [], ['test.jpg'])
            ]
            with patch('os.stat') as mock_stat:
                mock_stat.return_value = Mock(st_mtime=1630000000, st_size=1024)
                with patch('exifread.process_file') as mock_exif:
                    mock_exif.return_value = {}
                    with patch.object(self.caption_generator, 'generate_tags') as mock_tags:
                        mock_tags.return_value = "dog, park"
                        self.photo_manager.load_photos('/test')
                        self.assertEqual(len(self.photo_manager.photos), 1)
                        self.assertEqual(self.photo_manager.photos[0][0], '/test/test.jpg')
                        self.assertEqual(self.photo_manager.photos[0][4], "dog, park")
                        # Verify database
                        metadata = self.db.get_image_metadata('/test/test.jpg')
                        self.assertEqual(metadata["tags"], "dog, park")

    def test_photo_manager_load_from_database(self):
        # Pre-populate database
        metadata = {
            "file_path": "/test/test.jpg",
            "modified_time": datetime(2023, 1, 1),
            "file_size": 1024,
            "location": "Unknown",
            "tags": "dog, park",
            "detailed_caption": None
        }
        self.db.add_image_metadata(metadata)
        
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [
                ('/test', [], ['test.jpg'])
            ]
            with patch('os.stat') as mock_stat:
                mock_stat.return_value = Mock(st_mtime=metadata["modified_time"].timestamp(), st_size=1024)
                with patch('exifread.process_file') as mock_exif:
                    mock_exif.return_value = {}
                    self.photo_manager.load_photos('/test')
                    self.assertEqual(len(self.photo_manager.photos), 1)
                    self.assertEqual(self.photo_manager.photos[0][4], "dog, park")

    def test_photo_manager_search_photos(self):
        self.photo_manager.photos = [
            ('img1.jpg', datetime.now(), 1024, "Unknown", "dog, park"),
            ('img2.jpg', datetime.now(), 2048, "Unknown", "cat, house")
        ]
        with patch.object(self.photo_manager.nlp_model, 'encode') as mock_encode:
            mock_encode.side_effect = [
                Mock(),  # Query embedding
                [Mock(), Mock()]  # Tag embeddings
            ]
            with patch('sentence_transformers.util.cos_sim') as mock_cos_sim:
                mock_cos_sim.return_value = [[0.8, 0.2]]  # High score for first photo
                results = self.photo_manager.search_photos("dog")
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0][0], 'img1.jpg')

    def test_caption_generator_load_models(self):
        with patch('transformers.AutoProcessor.from_pretrained') as mock_florence_processor, \
             patch('transformers.AutoModelForCausalLM.from_pretrained') as mock_florence_model, \
             patch('transformers.BlipProcessor.from_pretrained') as mock_blip_processor, \
             patch('transformers.BlipForConditionalGeneration.from_pretrained') as mock_blip_model:
            caption_generator = CaptionGenerator()
            mock_florence_processor.assert_called_once()
            mock_florence_model.assert_called_once()
            mock_blip_processor.assert_called_once()
            mock_blip_model.assert_called_once()

    def test_caption_generator_generate_tags(self):
        with patch.object(self.caption_generator, 'blip_model', None):
            tags = self.caption_generator.generate_tags("test.jpg")
            self.assertEqual(tags, "Tags unavailable: BLIP model not loaded")
        
        with patch('PIL.Image.open') as mock_open, \
             patch.object(self.caption_generator, 'blip_processor') as mock_processor, \
             patch.object(self.caption_generator, 'blip_model') as mock_model:
            mock_open.return_value.convert.return_value = Mock()
            mock_processor.return_value = {"input_ids": []}
            mock_model.generate.return_value = [0]
            mock_processor.decode.return_value = "dog in a park"
            tags = self.caption_generator.generate_tags("test.jpg")
            self.assertEqual(tags, "dog, park")

    def test_caption_generator_generate_caption(self):
        with patch.object(self.caption_generator, 'florence_model', None):
            caption = self.caption_generator.generate_image_caption("test.jpg")
            self.assertEqual(caption, "Caption unavailable: Florence-2 model not loaded. Ensure all dependencies (transformers, einops, timm) are installed.")
        
        with patch('PIL.Image.open') as mock_open, \
             patch.object(self.caption_generator, 'florence_processor') as mock_processor, \
             patch.object(self.caption_generator, 'florence_model') as mock_model:
            mock_open.return_value.convert.return_value = Mock()
            mock_processor.return_value = {"input_ids": [], "pixel_values": []}
            mock_model.generate.return_value = [0]
            mock_processor.batch_decode.return_value = ["A dog runs in a park."]
            caption = self.caption_generator.generate_image_caption("test.jpg")
            self.assertTrue(caption.startswith("In the image, a dog runs in a park"))

    def test_ui_manager_display_photos(self):
        self.photo_manager.photos = [
            ('test.jpg', datetime.now(), 1024, "Unknown", "dog, park")
        ]
        with patch('PIL.Image.open') as mock_open:
            mock_open.return_value.thumbnail = Mock()
            mock_open.return_value.size = (150, 150)
            self.ui_manager.display_photos()
            self.assertTrue(len(self.ui_manager.scrollable_frame.winfo_children()) > 0)

if __name__ == '__main__':
    unittest.main()