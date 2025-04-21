import logging
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM
import warnings

# Suppress timm FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning)

class CaptionGenerator:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.initialized = False
        try:
            logging.info(f"Loading Florence-2 model on {self.device}")
            self.model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Florence-2-large",
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            ).to(self.device)
            self.model.eval()
            self.processor = AutoProcessor.from_pretrained(
                "microsoft/Florence-2-large",
                trust_remote_code=True
            )
            self.initialized = True
            logging.info("Florence-2 model loaded successfully")
        except Exception as e:
            logging.exception(f"Error loading Florence-2 model: {str(e)}")
            self.initialized = False

    def is_initialized(self):
        return self.initialized

    def generate_image_caption(self, image_path: str) -> str:
        if not self.initialized:
            logging.warning(f"Cannot generate caption for {image_path}: Florence-2 model not loaded")
            return "Caption unavailable: Model not loaded"
        
        try:
            logging.debug(f"Generating caption for {image_path}")
            image = Image.open(image_path).convert("RGB")
            
            prompt = "<DETAILED_CAPTION>"
            inputs = self.processor(text=prompt, images=image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    num_beams=3,
                    do_sample=False
                )
            
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            caption = generated_text.strip()
            logging.debug(f"Generated caption: {caption}")
            return caption
            
        except Exception as e:
            logging.exception(f"Error generating caption for {image_path}: {str(e)}")
            return f"Error generating caption: {str(e)}"

    def generate_tags(self, image_path: str) -> list:
        if not self.initialized:
            logging.warning(f"Cannot generate tags for {image_path}: Florence-2 model not loaded")
            return []
        
        try:
            logging.debug(f"Generating tags for {image_path}")
            caption = self.generate_image_caption(image_path)
            tags = [word.lower() for word in caption.split() if len(word) > 3]
            logging.debug(f"Generated tags: {tags}")
            return tags
        except Exception as e:
            logging.exception(f"Error generating tags for {image_path}: {str(e)}")
            return []