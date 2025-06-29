# rename-screenshots

A Python script to automatically rename Mac screenshots using OCR and local LLM summarization.

## Features

- Scans your Desktop for new screenshots (PNG files starting with "Screen").
- Extracts text from screenshots using Tesseract OCR.
- Summarizes the content using a local LLM (Ollama + Llama 3).
- Renames screenshots to a concise summary, preserving the original timestamp.
- Logs both old and new filenames for tracking.
- Designed to run automatically (e.g., via cron).

## Requirements

- Python 3.8+
- [Tesseract OCR](https://tesseract-ocr.github.io/tessdoc/Installation.html)
- [Ollama](https://ollama.com/) with the `llama3` model
- Python packages: `pillow`, `pytesseract`, `requests`

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/rename-screenshots.git
cd rename-screenshots
```

### 2. Set up a Python virtual environment

Create a new virtual environment (replace `venv` with your preferred name):

```bash
python3 -m venv venv
```

Activate the virtual environment:

- On macOS/Linux:
  ```bash
  source venv/bin/activate
  ```
- On Windows:
  ```cmd
  venv\Scripts\activate
  ```

### 3. Install required Python packages

With your virtual environment activated, run:

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR

On macOS (using Homebrew):
```bash
brew install tesseract
```

On Ubuntu/Debian:
```bash
sudo apt-get install tesseract-ocr
```

### 5. Install and run Ollama

- Download and install from [Ollama](https://ollama.com/).
- Pull the Llama 3 model:
  ```bash
  ollama pull llama3
  ```
- Start Ollama (if not already running):
  ```bash
  ollama serve
  ```

### 6. Configure the script (if needed)

By default, the script processes PNG files on your Desktop. If you want to change the directory, edit the `SCREENSHOT_DIR` variable in `screenshot_renamer.py`.

## Usage

### Run the script manually

Activate your virtual environment if not already active:
```bash
source venv/bin/activate
```

Then run:
```bash
python screenshot_renamer.py
```

### Run the script automatically every hour (using cron)

1. Find the full path to your Python executable in the virtual environment:
   ```bash
   which python
   # Example output: /Users/yourusername/rename-screenshots/venv/bin/python
   ```
2. Find the full path to your script:
   ```bash
   pwd
   # Example output: /Users/yourusername/rename-screenshots
   ```
3. Edit your crontab:
   ```bash
   crontab -e
   ```
4. Add the following line to run the script every hour (replace paths as needed):
   ```
   0 * * * * /Users/yourusername/rename-screenshots/venv/bin/python /Users/yourusername/rename-screenshots/screenshot_renamer.py
   ```
5. Save and exit the editor. The script will now run every hour.

## Log File

The script creates a `processed_files.txt` file in the same directory, logging both the old and new filenames for each processed screenshot.

## License

MIT License
