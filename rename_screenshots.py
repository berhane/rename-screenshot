#!/Users/berhanetemelso/MyPythonEnv/bin/python3

import os
import re
import pytesseract
from PIL import Image
import requests
from datetime import datetime
import argparse

# Ollama API endpoint and model
OLLAMA_URL = 'http://localhost:11434/api/generate'
LLM_MODEL = 'llama3'

# Match any PNG file starting with 'Screen'
#SCREENSHOT_PATTERN = re.compile(r'*screenshot-2025.*\.(png|jpg|jpeg)$', re.IGNORECASE)
SCREENSHOT_PATTERN = re.compile(r'^Screen.*\.(png|jpg|jpeg)$', re.IGNORECASE)

def parse_args():
    parser = argparse.ArgumentParser(description="Rename screenshots using OCR and LLM summarization.")
    parser.add_argument('--dir', type=str, required=True, help='Directory containing screenshots to process')
    return parser.parse_args()

def get_processed_files(screenshot_dir):
    processed_log = os.path.join(screenshot_dir, 'processed_files.txt')
    if not os.path.exists(processed_log):
        return set()
    with open(processed_log, 'r') as f:
        # Only consider the old filenames (before ' -> ')
        return set(line.strip().split(' -> ')[0] for line in f if line.strip())

def log_processed_file(screenshot_dir, old_filename, new_filename):
    processed_log = os.path.join(screenshot_dir, 'processed_files.txt')
    with open(processed_log, 'a') as f:
        f.write(f"{old_filename} -> {new_filename}\n")

def extract_text_from_image(image_path):
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from {image_path}: {e}")
        return ''

def summarize_text_with_ollama(text):
    prompt = (
        "Summarize the following screenshot content in 3-7 words. "
        "Be concise and descriptive.\n\nContent:\n" + text + "\nSummary:"
    )
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        summary = result.get('response', '').strip().replace('\n', ' ')
        # Clean up summary for filename
        summary = re.sub(r'[^a-zA-Z0-9\-_ ]', '', summary)
        summary = summary.replace(' ', '-')
        return summary[:50]  # Limit length
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return 'unsummarized'

def get_datetime_from_file(filepath):
    """
    Returns the last modification date and time of the file as (date_str, time_str).
    """
    mtime = os.path.getmtime(filepath)
    dt = datetime.fromtimestamp(mtime)
    date_str = dt.strftime('%Y-%m-%d')
    time_str = dt.strftime('%H-%M-%S')
    return date_str, time_str

def main():
    args = parse_args()
    screenshot_dir = os.path.expanduser(args.dir)
    processed = get_processed_files(screenshot_dir)
    for fname in os.listdir(screenshot_dir):
        if not SCREENSHOT_PATTERN.match(fname):
            continue
        if fname in processed:
            continue
        full_path = os.path.join(screenshot_dir, fname)
        print(f"Processing {fname}...")
        text = extract_text_from_image(full_path)
        summary = summarize_text_with_ollama(text)
        date_str, time_str = get_datetime_from_file(full_path)
        new_fname = f"{summary}-screenshot-{date_str}-{time_str}.png"
        new_path = os.path.join(screenshot_dir, new_fname)
        # Avoid overwriting
        counter = 1
        while os.path.exists(new_path):
            new_fname = f"{summary}-screenshot-{date_str}-{time_str}-{counter}.png"
            new_path = os.path.join(screenshot_dir, new_fname)
            counter += 1
        # Preserve timestamps
        stat = os.stat(full_path)
        os.rename(full_path, new_path)
        os.utime(new_path, (stat.st_atime, stat.st_mtime))
        log_processed_file(screenshot_dir, fname, new_fname)
        print(f"Renamed to {new_fname}")

if __name__ == "__main__":
    main()
