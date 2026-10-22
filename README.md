# rename-screenshots

A Python script to automatically rename Mac screenshots using OCR and LLM summarization (local Ollama, or a hosted OpenAI-compatible / Anthropic model).

## Features

- Scans your Desktop for new screenshots (PNG files starting with "Screen").
- Extracts text from screenshots using Tesseract OCR.
- Summarizes the content using an LLM: local (Ollama + Llama 3, the default) or hosted (see [Choosing an LLM](#choosing-an-llm)).
- Renames screenshots to a concise summary, preserving the original timestamp.
- Logs both old and new filenames for tracking.
- Designed to run automatically (e.g., via cron).

## Requirements

- Python 3.8+
- [Tesseract OCR](https://tesseract-ocr.github.io/tessdoc/Installation.html)
- One LLM backend: [Ollama](https://ollama.com/) with the `llama3` model (default), **or** an API key for a hosted provider
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

### 5. Install and run Ollama (skip if using a hosted model)

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

The directory to process is passed with `--dir` (required). Only files whose names start with `Screen` (png/jpg/jpeg) are renamed. To use a hosted model instead of Ollama, see below.

## Choosing an LLM

| Provider | `--provider` | Default model | API key env var |
|---|---|---|---|
| Local Ollama | `ollama` (default) | `llama3` | none |
| OpenAI-compatible (OpenAI, OpenRouter, Groq, Together, ...) | `openai` | none, set `--model` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `claude-haiku-4-5-20251001` | `ANTHROPIC_API_KEY` |

Settings come from flags or environment variables (flags win):

| Flag | Env var | Meaning |
|---|---|---|
| `--provider` | `LLM_PROVIDER` | Backend, as above |
| `--model` | `LLM_MODEL` | Model name |
| `--base-url` | `LLM_BASE_URL` | API base URL (e.g. `https://openrouter.ai/api/v1`, or an Ollama server on another machine) |
| n/a | `LLM_API_KEY` | API key; overrides the provider-specific variable. Never passed on the command line |

Examples:

```bash
# Anthropic
export ANTHROPIC_API_KEY=...
python rename_screenshots.py --dir ~/Desktop --provider anthropic

# OpenAI-compatible endpoint
export OPENAI_API_KEY=...
python rename_screenshots.py --dir ~/Desktop --provider openai --model gpt-4o-mini

# OpenRouter (or any other OpenAI-compatible host)
export OPENAI_API_KEY=<openrouter key>
python rename_screenshots.py --dir ~/Desktop --provider openai \
    --base-url https://openrouter.ai/api/v1 --model <model-id>
```

**Privacy:** with a hosted provider, the text OCR'd from each screenshot (first 4000 characters) is sent to that provider. Use the default Ollama backend if your screenshots may contain sensitive content.

If the LLM call fails (bad key, rate limit, network error), the file is left unrenamed and unlogged, so the next run retries it.

## Usage

### Run the script manually

Activate your virtual environment if not already active:
```bash
source venv/bin/activate
```

Then run:
```bash
python rename_screenshots.py --dir ~/Desktop
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
   0 * * * * /Users/yourusername/rename-screenshots/venv/bin/python /Users/yourusername/rename-screenshots/rename_screenshots.py --dir /Users/yourusername/Desktop
   ```
   For a hosted provider, cron does not inherit your shell environment: define them as `NAME=value` lines above the schedule line in the crontab (e.g. `ANTHROPIC_API_KEY=...`), or use a wrapper script with restricted permissions.
5. Save and exit the editor. The script will now run every hour.

## Log File

The script creates a `processed_files.txt` file in the screenshot directory, logging both the old and new filenames for each processed screenshot.

## License

MIT License
