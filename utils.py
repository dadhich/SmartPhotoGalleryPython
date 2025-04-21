import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    try:
        # Create logs directory if it doesn't exist
        log_dir = os.path.expanduser("~/Desktop/photo_gallery/logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "photo_gallery.log")

        # Configure logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # Clear any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler for terminal output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        logging.info("Logging initialized with file and console output")
    except Exception as e:
        # Fallback to console if logging setup fails
        print(f"Failed to initialize logging: {str(e)}")
        logging.basicConfig(level=logging.DEBUG)
        logging.error(f"Logging setup failed: {str(e)}")