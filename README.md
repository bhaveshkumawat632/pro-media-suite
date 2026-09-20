# ProMediaSuite - Creative Pro Suite

A PyQt6-based desktop video editor featuring smart AI tools, timeline sequencing, and active media preview.

## Features

- **Media Bin & Timeline**: Import video clips, add them to a timeline sequence, and manage your project flow.
- **Active Preview Viewer**: Play, pause, and preview your media files directly in the application using the integrated video viewer.
- **AI Auto Color Grade**: Automatically enhance saturation and contrast of your clips using Pillow and NumPy processing.
- **Smart AI Trim**: Automatically trims video clips (removes first and last seconds).
- **Generate Subtitles**: Integrates with OpenAI's Whisper model to transcribe video audio and overlay subtitles automatically.
- **Export**: Render your final timeline into a single concatenated MP4 video using `moviepy`.

## Requirements

- Python 3.8+
- PyQt6
- moviepy
- pillow
- numpy
- openai-whisper
- ImageMagick (optional, needed for burning subtitles directly into video via TextClip)

## Installation

1. Clone the repository and navigate to the directory:
   ```bash
   cd ProMediaSuite
   ```
2. Create and activate a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Subtitles and video processing may require `ffmpeg` and `ImageMagick` to be installed on your system).*

## Usage

Start the application by running:
```bash
python main.py
```
You can also use the included `Install_and_Run.bat` if you are on Windows.

## AI Tools
Select clips in the timeline, then click an AI tool to process them. Processed files are automatically saved to disk and replaced in the timeline.

