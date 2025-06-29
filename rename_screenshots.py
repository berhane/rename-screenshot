#!/Users/berhanetemelso/MyPythonEnv/bin/python3

import os
import re
import pytesseract
from PIL import Image
import requests
from datetime import datetime

# Directory containing screenshots
SCREENSHOT_DIR = os.path.expanduser('~/Desktop')
# Log file to keep track of processed files
PROCESSED_LOG = os.path.join(SCREENSHOT_DIR, 'processed_files.txt')
# Ollama API endpoint
OLLAMA_URL = 'http://localhost:11434/api/generate'
# LLM model name
LLM_MODEL = 'llama3'

# Regex to match screenshot files
SCREENSHOT_PATTERN = re.compile(r'^Screen.*\.png$', re.IGNORECASE)

def get_processed_files():
    if not os.path.exists(PROCESSED_LOG):
        return set()
    with open(PROCESSED_LOG, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def log_processed_file(old_filename, new_filename):
    with open(PROCESSED_LOG, 'a') as f:
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

def get_datetime_from_filename(filename):
    # Example: Screenshot 2024-06-08 at 10.23.45.png
    match = re.search(r'Screenshot ([0-9\-]+) at ([0-9\.]+)', filename)
    if match:
        date_part = match.group(1)
        time_part = match.group(2).replace('.', '-')
        return date_part, time_part
    else:
        now = datetime.now()
        return now.strftime('%Y-%m-%d'), now.strftime('%H-%M-%S')

def main():
    processed = get_processed_files()
    for fname in os.listdir(SCREENSHOT_DIR):
        if not SCREENSHOT_PATTERN.match(fname):
            continue
        if fname in processed:
            continue
        full_path = os.path.join(SCREENSHOT_DIR, fname)
        print(f"Processing {fname}...")
        text = extract_text_from_image(full_path)
        summary = summarize_text_with_ollama(text)
        date_str, time_str = get_datetime_from_filename(fname)
        new_fname = f"{summary}-screenshot-{date_str}-{time_str}.png"
        new_path = os.path.join(SCREENSHOT_DIR, new_fname)
        # Avoid overwriting
        counter = 1
        while os.path.exists(new_path):
            new_fname = f"{summary}-screenshot-{date_str}-{time_str}-{counter}.png"
            new_path = os.path.join(SCREENSHOT_DIR, new_fname)
            counter += 1
        # Preserve timestamps
        stat = os.stat(full_path)
        os.rename(full_path, new_path)
        os.utime(new_path, (stat.st_atime, stat.st_mtime))
        log_processed_file(fname, new_fname)
        print(f"Renamed to {new_fname}")

if __name__ == "__main__":
    main()
