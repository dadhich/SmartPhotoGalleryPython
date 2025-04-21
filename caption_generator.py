import logging
from PIL import Image
import torch
from typing import List

try:
    from transformers import AutoProcessor, AutoModelForCausalLM, BlipProcessor, BlipForConditionalGeneration
except ImportError as e:
    logging.critical(f"Failed to import transformers: {str(e)}")
    AutoProcessor = None
    AutoModelForCausalLM = None
    BlipProcessor = None
    BlipForConditionalGeneration = None

try:
    import einops
except ImportError as e:
    logging.critical(f"Encountered exception while importing einops: {str(e)}")
    einops = None

try:
    import timm
except ImportError as e:
    logging.critical(f"Encountered exception while importing timm: {str(e)}")
    timm = None

class CaptionGenerator:
    def __init__(self):
        self.florence_processor = None
        self.florence_model = None
        self.blip_processor = None
        self.blip_model = None
        self.load_models()

    def load_models(self):
        try:
            if AutoProcessor is None or AutoModelForCausalLM is None:
                raise ImportError("Transformers library is not properly installed")
            if einops is None:
                raise ImportError("einops is required for Florence-2 but is not installed")
            if timm is None:
                raise ImportError("timm is required for Florence-2 but is not installed")
            if BlipProcessor is None or BlipForConditionalGeneration is None:
                raise ImportError("Transformers BLIP components are not properly installed")

            # Load Florence-2 for detailed captions
            self.florence_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Florence-2-large", trust_remote_code=True
            )
            self.florence_processor = AutoProcessor.from_pretrained(
                "microsoft/Florence-2-large", trust_remote_code=True
            )
            logging.info("Florence-2 model loaded successfully")

            # Load BLIP for tags
            self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
            self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            logging.info("BLIP model loaded successfully")
        except Exception as e:
            logging.error(f"Error loading models: {str(e)}")
            self.florence_model = None
            self.florence_processor = None
            self.blip_model = None
            self.blip_processor = None
            self.show_error(f"Failed to load image captioning models: {str(e)}. Please ensure einops and timm are installed.")

    def generate_image_caption(self, image_path: str) -> str:
        try:
            if self.florence_model is None or self.florence_processor is None:
                logging.warning("Detailed caption generation failed: Florence-2 model not loaded")
                return "Caption unavailable: Florence-2 model not loaded. Ensure all dependencies (transformers, einops, timm) are installed."

            img = Image.open(image_path).convert("RGB")
            task_prompt = "<DETAILED_CAPTION>"
            inputs = self.florence_processor(text=task_prompt, images=img, return_tensors="pt")

            with torch.no_grad():
                generated_ids = self.florence_model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    num_beams=3,
                )
            caption = self.florence_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

            caption = caption.replace("\n", " ").strip()
            if not caption.endswith("."):
                caption += "."
            caption = f"In the image, {caption.lower()}"

            logging.info(f"Generated detailed caption for {image_path}: {caption}")
            return caption
        except Exception as e:
            logging.error(f"Error generating detailed caption for {image_path}: {str(e)}")
            return f"Failed to generate caption: {str(e)}"

    def generate_tags(self, image_path: str) -> str:
        try:
            if self.blip_model is None or self.blip_processor is None:
                logging.warning("Tag generation failed: BLIP model not loaded")
                return "Tags unavailable: BLIP model not loaded"

            img = Image.open(image_path).convert("RGB")
            inputs = self.blip_processor(images=img, return_tensors="pt")

            with torch.no_grad():
                outputs = self.blip_model.generate(**inputs)
            caption = self.blip_processor.decode(outputs[0], skip_special_tokens=True)
            
            # Extract key objects as tags
            tags = ", ".join(word.strip() for word in caption.split() if word.strip().isalpha())
            if not tags:
                tags = "unknown"
            
            logging.info(f"Generated tags for {image_path}: {tags}")
            return tags
        except Exception as e:
            logging.error(f"Error generating tags for {image_path}: {str(e)}")
            return "unknown"

    def generate_batch_tags(self, image_paths: List[str]) -> List[str]:
        try:
            if self.blip_model is None or self.blip_processor is None:
                logging.warning("Batch tag generation failed: BLIP model not loaded")
                return ["Tags unavailable: BLIP model not loaded"] * len(image_paths)

            tags = []
            for image_path in image_paths:
                tag = self.generate_tags(image_path)
                tags.append(tag)
                logging.debug(f"Batch tag generated for {image_path}")
            
            logging.info(f"Generated {len(tags)} batch tags")
            return tags
        except Exception as e:
            logging.error(f"Error generating batch tags: {str(e)}")
            return ["unknown"] * len(image_paths)

    def show_error(self, message: str):
        logging.error(f"Error message: {message}")