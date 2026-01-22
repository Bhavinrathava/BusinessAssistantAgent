import uuid
from datetime import datetime
import streamlit as st
from supabase import create_client, Client

# Database connection parameters from Streamlit secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]


def get_db_connection() -> Client:
    """Get a Supabase client connection."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def initialize_database():
    """Initialize database - Supabase manages schema automatically."""
    pass


def save_message_to_db(
    role: str, content: str, show_calendly: bool = False, session_id: str = None
):
    """Save a message to the Supabase database.

    Args:
        role: "user" or "assistant"
        content: The message content
        show_calendly: Whether a calendly link was shown (for assistant messages)
        session_id: UUID for the chat dialog session
    """
    client = get_db_connection()

    message_id = str(uuid.uuid4())
    session_id = session_id or str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    try:
        client.table("messages").insert(
            {
                "message_id": message_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "show_calendly": show_calendly,
                "created_at": timestamp,
            }
        ).execute()
    except Exception as e:
        print(f"Error saving message to database: {e}")


def get_messages_by_session(session_id: str):
    """Retrieve all messages for a specific session.

    Args:
        session_id: UUID of the chat session

    Returns:
        List of message dictionaries
    """
    client = get_db_connection()

    try:
        response = (
            client.table("messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )

        return response.data if response.data else []
    except Exception as e:
        print(f"Error retrieving messages: {e}")
        return []


def get_all_messages(limit: int = 1000):
    """Retrieve all messages from the database.

    Args:
        limit: Maximum number of messages to retrieve

    Returns:
        List of message dictionaries
    """
    client = get_db_connection()

    try:
        response = (
            client.table("messages")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data if response.data else []
    except Exception as e:
        print(f"Error retrieving all messages: {e}")
        return []


def get_session_count():
    """Get the total number of unique chat sessions.

    Returns:
        Integer count of sessions
    """
    client = get_db_connection()

    try:
        response = client.table("messages").select("*").execute()

        # Count unique session IDs
        unique_sessions = set(msg["session_id"] for msg in response.data)
        return len(unique_sessions)
    except Exception as e:
        print(f"Error getting session count: {e}")
        return 0


def delete_session_messages(session_id: str):
    """Delete all messages from a specific session.

    Args:
        session_id: UUID of the chat session to delete
    """
    client = get_db_connection()

    try:
        client.table("messages").delete().eq("session_id", session_id).execute()
    except Exception as e:
        print(f"Error deleting session messages: {e}")
