import json
import os
from datetime import datetime
from pathlib import Path

# History file path
HISTORY_FILE = Path("data/message_history.json")


def _ensure_history_file():
    """Ensure the history file and directory exist."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(json.dumps([]))


def save_message(role: str, content: str, show_calendly: bool = False):
    """Save a message to the history file.

    Args:
        role: "user" or "assistant"
        content: The message content
        show_calendly: Whether a calendly link was shown (for assistant messages)
    """
    _ensure_history_file()

    # Load existing history
    history = json.loads(HISTORY_FILE.read_text())

    # Create message entry with timestamp
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    }

    # Add show_calendly flag only for assistant messages
    if role == "assistant":
        message["show_calendly"] = show_calendly

    # Append and save
    history.append(message)
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def load_message_history():
    """Load all messages from history file.

    Returns:
        List of message dictionaries
    """
    _ensure_history_file()
    return json.loads(HISTORY_FILE.read_text())


def get_api_messages_from_history():
    """Get messages in the format needed for Claude API (role + content only).

    Returns:
        List of {'role': ..., 'content': ...} dictionaries
    """
    history = load_message_history()
    return [{"role": msg["role"], "content": msg["content"]} for msg in history]


def get_ui_messages_from_history():
    """Get messages in the format needed for UI display.

    Returns:
        List of message dictionaries with UI metadata
    """
    history = load_message_history()
    ui_messages = []
    for msg in history:
        ui_msg = {
            "role": msg["role"],
            "content": msg["content"],
        }
        if msg["role"] == "assistant" and msg.get("show_calendly"):
            ui_msg["show_calendly"] = True
        ui_messages.append(ui_msg)
    return ui_messages


def clear_history():
    """Clear all message history."""
    _ensure_history_file()
    HISTORY_FILE.write_text(json.dumps([]))


def get_message_count():
    """Get the total number of messages in history.

    Returns:
        Integer count of messages
    """
    history = load_message_history()
    return len(history)
