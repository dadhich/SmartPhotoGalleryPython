# Distributing SmartPhotoGallery

This document describes how to create and use distributable files for the SmartPhotoGallery application, allowing users to install and run it on Windows, macOS, and Linux without manually setting up Python or dependencies.

## Overview

SmartPhotoGallery is a Python-based desktop application for organizing photos with features like automatic caption generation, face detection, and natural language search. To make it accessible, we use **PyInstaller** to create standalone executables that bundle the application, its dependencies, and required OpenCV model files. The distributables are provided as ZIP archives for each platform, containing everything needed to run the app.

## Prerequisites for Building

To create the distributables, you need:
- **Operating System**: Windows, macOS, or Linux (one machine per platform or a single machine with virtualization).
- **Python**: Version 3.13 or higher.
- **PyInstaller**: Install via `pip install pyinstaller`.
- **Project Files**: Ensure the SmartPhotoGallery project is set up as described in `README.md`.
- **Disk Space**: ~10GB per platform (due to large dependencies like `torch` and Florence-2).
- **Internet Access**: To download dependencies and OpenCV model files.

## Project Setup

1. **Clone or Set Up the Repository**:
   ```bash
   git clone https://github.com/<your-username>/SmartPhotoGallery.git
   cd SmartPhotoGallery
   ```

2. **Install Dependencies**:
   Use the provided `requirements.txt` (artifact `e6c0a7ee-b5d8-4069-b669-2a26e53cda65`):
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Download OpenCV Model Files**:
   Place these in the project root:
   ```bash
   curl -o deploy.prototxt https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt
   curl -o res10_300x300_ssd_iter_140000.caffemodel https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel
   ```

4. **Pre-Download Florence-2 Model**:
   To avoid runtime downloads, cache the Florence-2 model locally:
   ```python
   from transformers import AutoModelForCausalLM, AutoProcessor
   model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True)
   processor = AutoProcessor.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True)
   ```
   This stores the model in `~/.cache/huggingface/hub`.

## Building Distributables

Run the following steps on each platform (Windows, macOS, Linux) to create platform-specific executables. If using one machine, consider virtual machines or Docker for cross-platform builds.

### Common Steps

1. **Create a Build Script**:
   Save the following as `build_dist.py` in the project root to handle OpenCV model files and optimize the bundle:

   ```python
   import PyInstaller.__main__
   import os
   import shutil

   def build_executable():
       # Define paths
       project_dir = os.path.dirname(os.path.abspath(__file__))
       dist_dir = os.path.join(project_dir, "dist")
       work_dir = os.path.join(project_dir, "build")
       icon_file = None  # Add .ico (Windows) or .icns (macOS) if desired

       # Clean previous builds
       if os.path.exists(dist_dir):
           shutil.rmtree(dist_dir)
       if os.path.exists(work_dir):
           shutil.rmtree(work_dir)

       # PyInstaller command
       args = [
           "photo_gallery.py",
           "--onefile",  # Single executable (alternative: --onedir)
           "--name=SmartPhotoGallery",
           "--add-data=deploy.prototxt;.",
           "--add-data=res10_300x300_ssd_iter_140000.caffemodel;.",
           "--hidden-import=face_recognition",
           "--hidden-import=transformers",
           "--hidden-import=sentence_transformers",
           "--hidden-import=timm",
           "--hidden-import=einops",
           "--collect-all=torch",
           "--collect-all=transformers",
           "--collect-all=sentence_transformers",
           "--collect-all=timm",
           "--collect-all=einops",
           "--exclude-module=numpy",  # Optimize size (re-added if needed)
           "--exclude-module=matplotlib",  # Not used
           "--exclude-module=pandas",  # Not used
           "--noconfirm"
       ]

       if icon_file:
           args.append(f"--icon={icon_file}")

       # Run PyInstaller
       PyInstaller.__main__.run(args)

       print(f"Executable created in {dist_dir}")

   if __name__ == "__main__":
       build_executable()
   ```

2. **Run the Build**:
   ```bash
   python build_dist.py
   ```

3. **Package the Distributable**:
   After building, the executable (`SmartPhotoGallery` or `SmartPhotoGallery.exe`) is in the `dist/` folder. Package it into a ZIP archive:
   ```bash
   cd dist
   zip -r SmartPhotoGallery-<platform>.zip SmartPhotoGallery*
   ```
   Replace `<platform>` with `Windows`, `macOS`, or `Linux`.

### Platform-Specific Steps

#### Windows

1. **Environment**:
   - Use Windows 10/11 with Python 3.13.
   - Install dependencies in a virtual environment:
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     pip install -r requirements.txt
     pip install pyinstaller
     ```

2. **Build**:
   - Run `build_dist.py` as above.
   - Optionally, add an icon (`--icon=app.ico` in `build_dist.py`). Create `app.ico` using an image converter.

3. **Package**:
   ```bash
   cd dist
   zip -r SmartPhotoGallery-Windows.zip SmartPhotoGallery.exe
   ```

4. **Notes**:
   - Ensure `deploy.prototxt` and `res10_300x300_ssd_iter_140000.caffemodel` are bundled (via `--add-data`).
   - The executable is ~5-6GB due to `torch` and Florence-2.

#### macOS

1. **Environment**:
   - Use macOS 12+ (Monterey or later) with Python 3.13.
   - Install dependencies:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     pip install pyinstaller
     ```

2. **Build**:
   - Run `build_dist.py`.
   - For a `.app` bundle (optional), modify `build_dist.py` to use `--onedir` and add:
     ```python
     args.append("--osx-bundle-identifier=com.yourname.SmartPhotoGallery")
     ```
   - Run:
     ```bash
     python build_dist.py
     ```

3. **Package**:
   ```bash
   cd dist
   zip -r SmartPhotoGallery-macOS.zip SmartPhotoGallery
   ```
   Or, for `.app`:
   ```bash
   zip -r SmartPhotoGallery-macOS.zip SmartPhotoGallery.app
   ```

4. **Notes**:
   - macOS may require signing the `.app` bundle:
     ```bash
     codesign --force --deep --sign - dist/SmartPhotoGallery.app
     ```
   - Ensure `dlib` (used by `face_recognition`) compiles correctly (may require `cmake` and `libpng`).

#### Linux

1. **Environment**:
   - Use Ubuntu 20.04+ or equivalent with Python 3.13.
   - Install system dependencies:
     ```bash
     sudo apt update
     sudo apt install python3.13 python3.13-venv python3-pip libgl1-mesa-glx libglib2.0-0
     ```
   - Set up virtual environment:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     pip install pyinstaller
     ```

2. **Build**:
   - Run `build_dist.py`.

3. **Package**:
   ```bash
   cd dist
   zip -r SmartPhotoGallery-Linux.zip SmartPhotoGallery
   ```

4. **Notes**:
   - Ensure `libGL` is installed for OpenCV.
   - The executable may not work across Linux distributions due to shared library differences. Recommend building on the target distro (e.g., Ubuntu).

## Distributable Contents

Each ZIP archive (`SmartPhotoGallery-<platform>.zip`) contains:
- **Executable**: `SmartPhotoGallery.exe` (Windows), `SmartPhotoGallery` (macOS/Linux), or `SmartPhotoGallery.app` (macOS).
- **OpenCV Models**:
  - `deploy.prototxt`
  - `res10_300x300_ssd_iter_140000.caffemodel`
- **Cached Models**: Florence-2 model files (bundled in `~/.cache/huggingface/hub` or equivalent).
- **Generated Files** (created on first run):
  - `photo_database.db`: SQLite database for image metadata and faces.
  - `photo_gallery.log`: Log file for debugging.

## Installation Instructions for Users

### Windows

1. **Download**:
   - Download `SmartPhotoGallery-Windows.zip` from the GitHub releases page.

2. **Extract**:
   - Unzip to a folder (e.g., `C:\SmartPhotoGallery`).

3. **Run**:
   - Double-click `SmartPhotoGallery.exe`.
   - Alternatively, open a Command Prompt and run:
     ```cmd
     cd C:\SmartPhotoGallery
     SmartPhotoGallery.exe
     ```

4. **Notes**:
   - Windows Defender may flag the executable. Click "More info" and "Run anyway".
   - Ensure ~6GB free disk space.

### macOS

1. **Download**:
   - Download `SmartPhotoGallery-macOS.zip` from GitHub releases.

2. **Extract**:
   - Unzip to a folder (e.g., `~/Applications/SmartPhotoGallery`).

3. **Run**:
   - Double-click `SmartPhotoGallery` or `SmartPhotoGallery.app`.
   - Alternatively, via Terminal:
     ```bash
     cd ~/Applications/SmartPhotoGallery
     ./SmartPhotoGallery
     ```

4. **Notes**:
   - If macOS blocks the app ("unidentified developer"), allow it in System Settings > Security & Privacy.
   - Or, run:
     ```bash
     xattr -d com.apple.quarantine SmartPhotoGallery
     ```

### Linux

1. **Download**:
   - Download `SmartPhotoGallery-Linux.zip` from GitHub releases.

2. **Extract**:
   - Unzip to a folder (e.g., `~/SmartPhotoGallery`).

3. **Run**:
   - Make executable and run:
     ```bash
     cd ~/SmartPhotoGallery
     chmod +x SmartPhotoGallery
     ./SmartPhotoGallery
     ```

4. **Notes**:
   - Install dependencies if needed:
     ```bash
     sudo apt install libgl1-mesa-glx libglib2.0-0
     ```
   - Ensure ~6GB free disk space.

## Usage

1. **Launch the App**:
   - The UI opens, showing "Initializing..." while models load (5–20 seconds).
   - Status bar shows "Ready" when controls are enabled.

2. **Select a Folder**:
   - Click "Select Folder" to load images (JPG/PNG).
   - Thumbnails appear in a 4-column grid.

3. **View Images**:
   - Double-click a thumbnail to open a full-size window with scrollbars and zoom.
   - Hover over faces to show yellow rectangles; click to tag names.

4. **Search and Sort**:
   - Use the search bar for natural language queries (e.g., "park").
   - Sort by date, size, or name via the dropdown.

5. **Logs and Database**:
   - Check `photo_gallery.log` for debugging.
   - View `photo_database.db` with SQLite tools.

## Troubleshooting

1. **App Fails to Start**:
   - Check `photo_gallery.log` in the executable’s folder.
   - Ensure sufficient disk space (~6GB).
   - Verify OpenCV model files are present.

2. **No Face Rectangles**:
   - Ensure images are clear (JPG, >500x500px).
   - Check logs:
     ```bash
     cat photo_gallery.log | grep -E "face|hover"
     ```

3. **Model Loading Issues**:
   - Verify Florence-2 model is cached (included in bundle).
   - Check for errors:
     ```bash
     cat photo_gallery.log | grep "model"
     ```

4. **Platform-Specific**:
   - **Windows**: Disable antivirus temporarily if blocked.
   - **macOS**: Run `chmod +x` or remove quarantine.
   - **Linux**: Install `libGL` and `libglib2.0`.

## Notes for Developers

- **Bundle Size**: The executable is large (~5-6GB) due to `torch` and Florence-2. Consider `--onedir` for smaller updates.
- **Cross-Platform Builds**: Use virtual machines or Docker for consistent builds across platforms.
- **Custom Icons**: Add `.ico` (Windows) or `.icns` (macOS) in `build_dist.py`.
- **Optimization**: Exclude unused modules (`numpy`, `pandas`) to reduce size.
- **Testing**: Test executables on clean systems to ensure no missing dependencies.

## Distribution

1. **Upload to GitHub**:
   - Create a release on GitHub:
     ```bash
     gh release create v1.0.0 \
       dist/SmartPhotoGallery-Windows.zip \
       dist/SmartPhotoGallery-macOS.zip \
       dist/SmartPhotoGallery-Linux.zip \
       --title "SmartPhotoGallery v1.0.0" \
       --notes "Initial release with Windows, macOS, and Linux executables"
     ```

2. **Update README**:
   - Add a "Download" section to `README.md`:
     ```markdown
     ## Download

     Download the latest release for your platform from the [GitHub Releases](https://github.com/<your-username>/SmartPhotoGallery/releases) page:
     - Windows: `SmartPhotoGallery-Windows.zip`
     - macOS: `SmartPhotoGallery-macOS.zip`
     - Linux: `SmartPhotoGallery-Linux.zip`
     ```

## License

This project is licensed under the MIT License (or your chosen license). See the `LICENSE` file for details.