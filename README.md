# Lumina AI

Lumina is a brilliant, witty, and charming female AI virtual character. She has a fantastic sense of humor, loves joking around, and proudly uses British spelling, slang, and colloquialisms. Despite her playful nature, she is a genius who excels in math, science, biology, physics, computer science, software development, and medicine. She also loves writing beautiful poems and catchy songs.

This project uses the Groq API (Llama 3.3 70B) for fast, intelligent responses, and Edge TTS for high-quality, auto-playing British female voice generation. The interface is built using Gradio.

## Prerequisites

- Python 3.8+
- A [Groq API Key](https://console.groq.com/)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Lumina-AI.git
   cd Lumina-AI
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   Create a `.env` file in the root directory and add your Groq API key:
   ```env
   GROQ_API_KEY=your_api_key_here
   ```

## Running the Application

Start the application by running:
```bash
python main.py
```

The Gradio interface will be available in your default web browser (typically at `http://127.0.0.1:7861`). You can type your messages to Lumina, and she will respond with text and an auto-playing voice!

## Features
- **High-Speed Streaming:** Utilizes `AsyncGroq` with streaming to provide instant text responses.
- **British Voice Generation:** Uses `edge-tts` to generate a high-quality British accent ("en-GB-SoniaNeural").
- **Interactive UI:** Built on Gradio with a modern chatbot interface.
