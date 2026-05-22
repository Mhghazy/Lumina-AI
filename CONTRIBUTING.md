# Contributing to Lumina AI

First off, thank you for considering contributing to Lumina AI! It's people like you that make Lumina such a powerful open-source tool.

## 🛠️ Development Setup

1. **Fork & Clone**: Fork the repository and clone your fork locally.
2. **Environment**: We recommend Python 3.11+. Install dependencies using:
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment Variables**: Copy `.env.dev` to `.env` and fill in your API keys for testing.
4. **Running Locally**:
   ```bash
   python main.py
   ```

## 🌿 Branching Strategy

- **`master`**: Stable production code.
- Create a new branch for your feature or bugfix:
  - `feature/your-feature-name`
  - `bugfix/issue-description`

## 📝 Pull Request Process

1. Ensure any new functionality is documented (especially in `lumina_technical_documentation.md`).
2. Run standard linting (if applicable).
3. Open a PR using our Pull Request Template. 
4. A maintainer will review your code. Be prepared to make requested changes!

## 🐛 Reporting Bugs

We use GitHub issues to track public bugs. Report a bug by opening a new issue using the **Bug Report** template. Ensure you provide reproducible steps, logs, and your OS/Python version.
