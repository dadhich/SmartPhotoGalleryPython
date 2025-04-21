import logging
from PIL import Image
import torch

try:
    from transformers import AutoProcessor, AutoModelForCausalLM
except ImportError as e:
    logging.critical(f"Failed to import transformers: {str(e)}")
    AutoProcessor = None
    AutoModelForCausalLM = None

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
        self.processor = None
        self.model = None
        self.load_model()

    def load_model(self):
        try:
            if AutoProcessor is None or AutoModelForCausalLM is None:
                raise ImportError("Transformers library is not properly installed")
            if einops is None:
                raise ImportError("einops is required for Florence-2 but is not installed")
            if timm is None:
                raise ImportError("timm is required for Florence-2 but is not installed")

            # Load Florence-2 model and processor
            self.model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Florence-2-large", trust_remote_code=True
            )
            self.processor = AutoProcessor.from_pretrained(
                "microsoft/Florence-2-large", trust_remote_code=True
            )
            logging.info("Florence-2 model loaded successfully")
        except Exception as e:
            logging.error(f"Error loading Florence-2 model: {str(e)}")
            self.model = None
            self.processor = None
            self.show_error(f"Failed to load image captioning model: {str(e)}. Please ensure einops and timm are installed.")

    def generate_image_caption(self, image_path: str) -> str:
        try:
            if self.model is None or self.processor is None:
                logging.warning("Caption generation failed: Model not loaded")
                return "Caption unavailable: Model not loaded. Ensure all dependencies (transformers, einops, timm) are installed."

            # Load and process image
            img = Image.open(image_path).convert("RGB")
            task_prompt = "<DETAILED_CAPTION>"
            inputs = self.processor(text=task_prompt, images=img, return_tensors="pt")

            # Generate caption
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    num_beams=3,
                )
            caption = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

            # Clean and format caption as a paragraph
            caption = caption.replace("\n", " ").strip()
            if not caption.endswith("."):
                caption += "."
            caption = f"In the image, {caption.lower()}"

            logging.info(f"Generated caption for {image_path}: {caption}")
            return caption
        except Exception as e:
            logging.error(f"Error generating caption for {image_path}: {str(e)}")
            return f"Failed to generate caption: {str(e)}"

    def show_error(self, message: str):
        # This method is called by UIManager to display errors
        logging.error(f"Error message: {message}")