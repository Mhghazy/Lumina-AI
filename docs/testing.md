# 🧪 Testing & CI/CD

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):
- Triggered on push/PR to `master`
- Runs on `ubuntu-latest` with Python 3.11
- Installs dependencies from `requirements.txt`
- Validates imports: `gradio`, `groq`, `edge_tts`, `requests`, `bs4`, `googlesearch`, `duckduckgo_search`, `wikipedia`

