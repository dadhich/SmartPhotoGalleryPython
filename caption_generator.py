import logging
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch

class CaptionGenerator:
    def __init__(self):
        self.processor = None
        self.model = None
        self.load_model()

    def load_model(self):
        try:
            self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
            logging.info("BLIP model loaded successfully")
        except Exception as e:
            logging.error(f"Error loading BLIP model: {str(e)}")
            self.model = None

    def generate_image_caption(self, image_path: str) -> str:
        try:
            if self.model is None or self.processor is None:
                return "Caption unavailable: Model not loaded"
            
            img = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=img, return_tensors="pt")
            
            with torch.no_grad():
                outputs = self.model.generate(**inputs)
            caption = self.processor.decode(outputs[0], skip_special_tokens=True)
            
            logging.info(f"Generated caption for {image_path}: {caption}")
            return caption
        except Exception as e:
            logging.error(f"Error generating caption for {image_path}: {str(e)}")
            return "Failed to generate caption"