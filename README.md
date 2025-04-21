# SmartPhotoGallery

## About

SmartPhotoGallery is an intelligent desktop application for organizing and exploring photo collections. Built with Python and Tkinter, it leverages advanced computer vision and natural language processing to automatically generate detailed captions, detect and tag faces, and enable natural language search. The application is designed for ease of use, with a responsive UI that supports zooming, scrolling, and interactive face tagging, making it ideal for managing personal or professional photo libraries.

## Features

- **Automatic Caption Generation**: Uses the Florence-2 model to create detailed captions for images, stored in a SQLite database.
- **Face Detection and Tagging**: Detects faces in images using `face_recognition` and allows users to tag faces with names via an interactive hover-and-click interface.
- **Natural Language Search**: Search photos using natural language queries (e.g., "park" or "Tina") with embeddings from SentenceTransformer.
- **Fast Startup**: Loads heavy models (Florence-2, SentenceTransformer) in a background thread to ensure the UI opens in &lt;1 second.
- **Responsive UI**: Supports thumbnail grids, full-size image views with scrollbars, zoom in/out, and hover-based face rectangle display.
- **Metadata Management**: Stores image metadata (date, size, location, tags, captions) and face data (coordinates, names) in a SQLite database.
- **Error Handling and Logging**: Comprehensive logging to `photo_gallery.log` for debugging and monitoring.
- **Customizable Sorting**: Sort photos by date, size, or name.

## Installation

### Prerequisites

- **Operating System**: Windows, macOS, or Linux
- **Python**: Version 3.13 or higher
- **Hardware**: Minimum 8GB RAM (16GB+ recommended for model loading); GPU optional for faster processing

### Dependencies

Install the required Python packages:

```bash
pip install opencv-contrib-python face_recognition Pillow sentence-transformers transformers exifread timm einops torch
```

Verify versions:

```bash
python -c "import transformers; print(transformers.__version__)"  # Expect: >=4.36.0
python -c "import face_recognition; print(face_recognition.__version__)"  # Expect: >=1.3.0
python -c "import torch; print(torch.__version__)"  # Expect: >=2.0.0
```

### OpenCV Model Files

Download the following files for compatibility (place them in the project root):

```bash
curl -o deploy.prototxt https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt
curl -o res10_300x300_ssd_iter_140000.caffemodel https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel
```

### Project Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/<your-username>/SmartPhotoGallery.git
   cd SmartPhotoGallery
   ```

2. Ensure the project structure matches:

   ```
   SmartPhotoGallery/
   ├── photo_gallery.py
   ├── photo_manager.py
   ├── ui_manager.py
   ├── caption_generator.py
   ├── database.py
   ├── utils.py
   ├── deploy.prototxt
   ├── res10_300x300_ssd_iter_140000.caffemodel
   ├── photo_database.db (created on first run)
   ├── photo_gallery.log (created on first run)
   ├── README.md
   ```

3. Verify Python files for syntax errors:

   ```bash
   for file in *.py; do python -m py_compile "$file" && echo "$file: OK"; done
   ```

## Usage

1. **Run the Application**:

   ```bash
   python photo_gallery.py
   ```

   - The UI opens in &lt;1 second, displaying "Initializing..." while models load in the background (5–20 seconds, depending on hardware).
   - Once models are loaded, the status bar shows "Ready," and controls (folder selection, search, sort) are enabled.

2. **Select a Folder**:

   - Click "Select Folder" and choose a directory containing images (JPG or PNG).
   - Thumbnails load in a 4-column grid, with captions generated in the background.

3. **View Full-Size Image**:

   - Double-click a thumbnail to open the image in a full-size window.
   - Features:
     - **Scrollbars**: Navigate large images.
     - **Zoom**: Use "Zoom In" and "Zoom Out" buttons.
     - **Face Tagging**: Hover over faces to show yellow-bordered rectangles; click to tag with a name.
     - **Caption**: Displays at the bottom (e.g., "A person in a park").

4. **Search Photos**:

   - Enter a query (e.g., "park" or "Tina") in the search bar and press Enter.
   - Results update in the thumbnail grid.

5. **Sort Photos**:

   - Use the dropdown to sort by "Date," "Size," or "Name."

6. **Check Logs**:

   - View `photo_gallery.log` for debugging:

     ```bash
     cat photo_gallery.log
     ```

7. **Inspect Database**:

   - Use SQLite to view metadata and faces:

     ```bash
     sqlite3 photo_database.db
     sqlite> SELECT file_path, detailed_caption FROM images;
     sqlite> SELECT file_path, name, top, right, bottom, left FROM faces;
     ```

## Project Structure

- `photo_gallery.py`: Main entry point; initializes UI and loads models in a background thread.
- `ui_manager.py`: Manages the Tkinter UI, including thumbnail grid, full-size image window, and face tagging.
- `photo_manager.py`: Handles photo loading, caption generation, and natural language search.
- `caption_generator.py`: Generates captions using the Florence-2 model.
- `database.py`: Manages SQLite database for images and faces.
- `utils.py`: Utility functions (e.g., image metadata extraction).
- `photo_database.db`: SQLite database for storing image metadata and face data.
- `photo_gallery.log`: Log file for debugging.

## Requirements

- **Python Libraries**:
  - `opencv-contrib-python`
  - `face_recognition`
  - `Pillow`
  - `sentence-transformers`
  - `transformers>=4.36.0`
  - `exifread`
  - `timm`
  - `einops`
  - `torch>=2.0.0`
- **Files**:
  - `deploy.prototxt`
  - `res10_300x300_ssd_iter_140000.caffemodel`
- **Storage**: \~4GB for Florence-2 model; additional space for images and database.

## Troubleshooting

1. **Application Slow to Open**:

   - Ensure models load in the background (UI should open in &lt;1 second).
   - Check logs:

     ```bash
     cat photo_gallery.log | grep "model"
     ```
   - Verify system resources (`free -h`).

2. **No Face Rectangles**:

   - Check logs:

     ```bash
     cat photo_gallery.log | grep -E "face|hover"
     ```
   - Ensure faces are detected and stored:

     ```bash
     sqlite3 photo_database.db "SELECT top, right, bottom, left FROM faces WHERE file_path='/Winners.jpg'"
     ```
   - Test with a clear JPEG image (&gt;500x500px, single face).

3. **Model Loading Errors**:

   - Verify `torch` and GPU support:

     ```bash
     python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
     ```
   - Reinstall dependencies if needed.

4. **Database Issues**:

   - Check integrity:

     ```bash
     sqlite3 photo_database.db "PRAGMA integrity_check"
     ```
   - Delete `photo_database.db` and restart to recreate.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- **Florence-2**: For caption generation (Microsoft).
- **SentenceTransformer**: For natural language search (UKPLab).
- **face_recognition**: For face detection (ageitgey).
- **OpenCV**: For image processing.
- **Tkinter**: For the GUI.
