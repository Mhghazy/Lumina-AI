import os
import json
from datetime import datetime
from lumina.core.config import CHATS_DIR

def get_chat_list():
    """Returns a list of tuples for the dropdown: (Chat Title, chat_id)"""
    chats = []
    for filename in os.listdir(CHATS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(CHATS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    chat_id = data.get("id", filename.replace(".json", ""))
                    title = data.get("title", "Untitled Chat")
                    updated_at = data.get("updated_at", "")
                    display_name = f"{title} ({updated_at})" if updated_at else title
                    chats.append((display_name, chat_id))
            except Exception:
                pass
    
    # Sort by modified time (newest first)
    chats.sort(key=lambda x: os.path.getmtime(os.path.join(CHATS_DIR, f"{x[1]}.json")) if os.path.exists(os.path.join(CHATS_DIR, f"{x[1]}.json")) else 0, reverse=True)
    return chats

def load_chat(chat_id):
    """Loads a specific chat history by ID."""
    if not chat_id:
        return []
    filepath = os.path.join(CHATS_DIR, f"{chat_id}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                history = data.get("history", [])
                messages_history = []
                for item in history:
                    if isinstance(item, dict):
                        messages_history.append(item)
                    elif isinstance(item, (list, tuple)) and len(item) == 2:
                        if item[0]:
                            messages_history.append({"role": "user", "content": item[0]})
                        if item[1]:
                            messages_history.append({"role": "assistant", "content": item[1]})
                return messages_history
        except Exception:
            return []
    return []

def save_chat(chat_id, history):
    """Saves the chat history to a JSON file."""
    filepath = os.path.join(CHATS_DIR, f"{chat_id}.json")
    title = "New Chat"
    
    # Try to derive a title from the very first user message
    if history and len(history) > 0:
        for msg in history:
            if isinstance(msg, dict) and msg.get("role") == "user":
                first_msg = msg.get("content", "")
                if not isinstance(first_msg, str):
                    first_msg = str(first_msg)
                title = first_msg[:30] + ("..." if len(first_msg) > 30 else "")
                break
            elif isinstance(msg, (list, tuple)) and len(msg) > 0:
                first_msg = msg[0]
                if not isinstance(first_msg, str):
                    first_msg = str(first_msg)
                title = first_msg[:30] + ("..." if len(first_msg) > 30 else "")
                break
                
    data = {
        "id": chat_id,
        "title": title,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "history": history
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
