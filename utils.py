import logging

def setup_logging():
    logging.basicConfig(
        filename='photo_gallery.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )