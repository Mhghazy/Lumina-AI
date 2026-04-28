# Create Lumina AI Chatbot

This plan outlines the creation of Lumina, your female AI virtual character powered by the Groq API.

## User Review Required

- **Tech Stack Choice**: I am proposing **Gradio** as the web interface framework. It is a highly popular Python library for building AI chat applications quickly and provides a sleek UI. If you prefer a simple terminal (CLI) chat or another framework like Streamlit or Chainlit, please let me know!
- **Model Choice**: I plan to use `llama3-70b-8192` via the Groq API because it provides excellent reasoning (for math/science) and creative writing (for poems/songs) while being incredibly fast.
- **API Key Security**: I will store your Groq API key in a `.env` file so it is not hardcoded in the Python script.

## Open Questions

- Do you have a preferred UI theme (e.g., dark mode, specific colors) for the chat interface?
- Would you like to use a specific Groq model (e.g., `llama3-70b-8192`, `llama3-8b-8192`, `mixtral-8x7b-32768`), or should I use `llama3-70b-8192` as the default for its high intelligence and creativity?

## Proposed Changes

### Configuration
#### [NEW] .env
Will contain your `GROQ_API_KEY`.

#### [NEW] requirements.txt
Will include the required Python libraries:
- `groq`
- `gradio`
- `python-dotenv`

### Application Code
#### [NEW] main.py
Will contain:
- The Groq API integration.
- The system prompt defining Lumina's personality (British, humorous, scientific/medical/CS expert, artist).
- The Gradio `ChatInterface` to run the web application locally.

## Verification Plan

### Manual Verification
1. Run `pip install -r requirements.txt`.
2. Run `python main.py`.
3. Open the provided localhost URL in a web browser.
4. Chat with Lumina to verify she acts like a humorous, British female expert in the requested fields and can write poems/songs.
