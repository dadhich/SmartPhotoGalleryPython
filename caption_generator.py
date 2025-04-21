from transformers import AutoProcessor, AutoModelForCausalLM, BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import logging
import torch
import warnings
import os

# Suppress FutureWarning for timm imports
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import timm.layers

# Suppress Hugging Face custom code prompt
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

class CaptionGenerator:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.florence_processor = None
        self.florence_model = None
        self.blip_processor = None
        self.blip_model = None

    def load_models(self):
        try:
            # Load Florence-2 model with explicit trust_remote_code
            logging.info("Loading Florence-2 model with trust_remote_code=True")
            self.florence_processor = AutoProcessor.from_pretrained(
                "microsoft/Florence-2-large",
                trust_remote_code=True
            )
            self.florence_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Florence-2-large",
                trust_remote_code=True
            ).to(self.device)
            logging.info("Florence-2 model loaded successfully with custom code")
        except Exception as e:
            logging.error(f"Error loading Florence-2 model: {str(e)}")
            self.florence_processor = None
            self.florence_model = None

        try:
            # Load BLIP model
            self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
            logging.info("BLIP model loaded successfully")
        except Exception as e:
            logging.error(f"Error loading BLIP model: {str(e)}")
            self.blip_processor = None
            self.blip_model = None

    def generate_image_caption(self, image_path: str) -> str:
        if not self.florence_model or not self.florence_processor:
            return "Caption unavailable: Florence-2 model not loaded"
        
        try:
            image = Image.open(image_path).convert("RGB")
            task_prompt = "<DETAILED_CAPTION>"
            inputs = self.florence_processor(text=task_prompt, images=image, return_tensors="pt").to(self.device)
            generated_ids = self.florence_model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024,
                num_beams=3
            )
            generated_text = self.florence_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            caption = f"In the image, {generated_text.lower()}"
            logging.info(f"Generated caption for {image_path}: {caption}")
            return caption
        except Exception as e:
            logging.error(f"Error generating caption for {image_path}: {str(e)}")
            return "Failed to generate caption"

    def generate_tags(self, image_path: str) -> str:
        if not self.blip_model or not self.blip_processor:
            return "Tags unavailable: BLIP model not loaded"
        
        try:
            image = Image.open(image_path).convert("RGB")
            inputs = self.blip_processor(images=image, return_tensors="pt").to(self.device)
            generated_ids = self.blip_model.generate(**inputs)
            caption = self.blip_processor.decode(generated_ids[0], skip_special_tokens=True)
            tags = ", ".join([word.strip() for word in caption.split() if len(word.strip()) > 2])
            logging.info(f"Generated tags for {image_path}: {tags}")
            return tags if tags else "No tags generated"
        except Exception as e:
            logging.error(f"Error generating tags for {image_path}: {str(e)}")
            return "Failed to generate tags"