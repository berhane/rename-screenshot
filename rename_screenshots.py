#!/Users/berhanetemelso/MyPythonEnv/bin/python3 

import os
import re
import pytesseract
from PIL import Image
import requests
from datetime import datetime
import argparse

# LLM backends. Override with --provider/--model/--base-url or the LLM_PROVIDER,
# LLM_MODEL, LLM_BASE_URL and LLM_API_KEY environment variables.
PROVIDERS = {
    # Local Ollama server (native API, no key needed)
    'ollama': {'base_url': 'http://localhost:11434', 'model': 'llama3', 'key_env': None},
    # Any OpenAI-compatible /chat/completions endpoint (OpenAI, OpenRouter, Groq, Together, ...)
    'openai': {'base_url': 'https://api.openai.com/v1', 'model': None, 'key_env': 'OPENAI_API_KEY'},
    # Anthropic Messages API
    'anthropic': {'base_url': 'https://api.anthropic.com', 'model': 'claude-haiku-4-5-20251001', 'key_env': 'ANTHROPIC_API_KEY'},
}
REQUEST_TIMEOUT = 60  # seconds
# Output-token cap for the anthropic provider (its API requires one). Reasoning models
# such as Qwen3 spend tokens on hidden thinking first, so this must leave room for that.
DEFAULT_MAX_TOKENS = 1024
MAX_OCR_CHARS = 4000  # cap what is sent to the LLM

# Match any PNG file starting with 'Screen'
#SCREENSHOT_PATTERN = re.compile(r'*screenshot-2025.*\.(png|jpg|jpeg)$', re.IGNORECASE)
SCREENSHOT_PATTERN = re.compile(r'^Screen.*\.(png|jpg|jpeg)$', re.IGNORECASE)

def parse_args():
    parser = argparse.ArgumentParser(description="Rename screenshots using OCR and LLM summarization.")
    parser.add_argument('--dir', type=str, required=True, help='Directory containing screenshots to process')
    parser.add_argument('--provider', choices=sorted(PROVIDERS),
                        default=os.environ.get('LLM_PROVIDER', 'ollama'),
                        help='LLM backend (default: $LLM_PROVIDER or ollama)')
    parser.add_argument('--model', default=os.environ.get('LLM_MODEL'),
                        help='Model name (default: $LLM_MODEL or the provider default)')
    parser.add_argument('--base-url', default=os.environ.get('LLM_BASE_URL'),
                        help='API base URL (default: $LLM_BASE_URL or the provider default)')
    parser.add_argument('--max-tokens', type=int,
                        default=int(os.environ.get('LLM_MAX_TOKENS', DEFAULT_MAX_TOKENS)),
                        help=f'Output token cap for --provider anthropic (default: $LLM_MAX_TOKENS or {DEFAULT_MAX_TOKENS}); '
                             'raise it if a reasoning model runs out before answering')
    return parser.parse_args()

def resolve_llm_config(args):
    """Combine CLI flags, environment and provider defaults; exit early if misconfigured."""
    defaults = PROVIDERS[args.provider]
    model = args.model or defaults['model']
    if not model:
        raise SystemExit(f"No model set for provider '{args.provider}'. Use --model or $LLM_MODEL.")
    api_key = None
    if defaults['key_env']:
        api_key = os.environ.get('LLM_API_KEY') or os.environ.get(defaults['key_env'])
        if not api_key:
            raise SystemExit(f"No API key for provider '{args.provider}'. "
                             f"Set ${defaults['key_env']} (or $LLM_API_KEY).")
    return {
        'provider': args.provider,
        'model': model,
        'base_url': (args.base_url or defaults['base_url']).rstrip('/'),
        'max_tokens': args.max_tokens,
        'api_key': api_key,
    }

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

def _post_json(url, payload, headers=None):
    response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()

def _complete_ollama(cfg, prompt):
    result = _post_json(f"{cfg['base_url']}/api/generate",
                        {"model": cfg['model'], "prompt": prompt, "stream": False})
    return result.get('response', '')

def _complete_openai(cfg, prompt):
    result = _post_json(f"{cfg['base_url']}/chat/completions",
                        {"model": cfg['model'], "messages": [{"role": "user", "content": prompt}]},
                        headers={"Authorization": f"Bearer {cfg['api_key']}"})
    choice = result['choices'][0]
    text = choice['message'].get('content') or ''
    if not text.strip():
        raise ValueError(f"no text in response (finish_reason={choice.get('finish_reason')!r}, "
                         f"message keys={sorted(choice['message'])})")
    return text

def _complete_anthropic(cfg, prompt):
    result = _post_json(f"{cfg['base_url']}/v1/messages",
                        {"model": cfg['model'], "max_tokens": cfg['max_tokens'],
                         "messages": [{"role": "user", "content": prompt}]},
                        headers={"x-api-key": cfg['api_key'], "anthropic-version": "2023-06-01"})
    text = ''.join(b.get('text', '') for b in result['content'] if b.get('type') == 'text')
    if not text.strip():
        raise ValueError(f"no text in response (stop_reason={result.get('stop_reason')!r}, "
                         f"content block types={[b.get('type') for b in result['content']]})")
    return text

COMPLETERS = {'ollama': _complete_ollama, 'openai': _complete_openai, 'anthropic': _complete_anthropic}

def summarize_text(text, cfg):
    """Return a filename-safe summary of the OCR text. Raises on any LLM failure."""
    prompt = (
        "Summarize the following screenshot content in 3-7 words. "
        "Be concise and descriptive. Reply with only the summary.\n\nContent:\n"
        + text[:MAX_OCR_CHARS] + "\nSummary:"
    )
    raw = COMPLETERS[cfg['provider']](cfg, prompt).strip().replace('\n', ' ')
    summary = raw
    # Clean up summary for filename
    summary = re.sub(r'[^a-zA-Z0-9\-_ ]', '', summary)
    summary = summary.replace(' ', '-')[:50]  # Limit length
    if not summary:
        raise ValueError(f"summary empty after removing non-ASCII/punctuation; raw reply: {raw[:100]!r}")
    return summary

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
    cfg = resolve_llm_config(args)
    print(f"Using {cfg['provider']} model '{cfg['model']}' at {cfg['base_url']}")
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
        try:
            summary = summarize_text(text, cfg)
        except Exception as e:
            # Leave the file untouched and unlogged so the next run retries it
            print(f"Skipping {fname}: could not summarize ({e})")
            continue
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
