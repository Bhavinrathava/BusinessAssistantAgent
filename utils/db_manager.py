import uuid
import logging
from datetime import datetime
import streamlit as st
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.info(f"Inserting message - role: {role}, session_id: {session_id}, message_id: {message_id}")
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
        logger.info(f"Successfully saved message - message_id: {message_id}")
    except Exception as e:
        logger.error(f"Error saving message to database: {e}")


def get_messages_by_session(session_id: str):
    """Retrieve all messages for a specific session.

    Args:
        session_id: UUID of the chat session

    Returns:
        List of message dictionaries
    """
    client = get_db_connection()

    try:
        logger.info(f"Fetching messages for session: {session_id}")
        response = (
            client.table("messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )

        message_count = len(response.data) if response.data else 0
        logger.info(f"Retrieved {message_count} messages for session: {session_id}")
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error retrieving messages for session {session_id}: {e}")
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
        logger.info(f"Fetching all messages with limit: {limit}")
        response = (
            client.table("messages")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        message_count = len(response.data) if response.data else 0
        logger.info(f"Retrieved {message_count} total messages")
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error retrieving all messages: {e}")
        return []


def get_session_count():
    """Get the total number of unique chat sessions.

    Returns:
        Integer count of sessions
    """
    client = get_db_connection()

    try:
        logger.info("Fetching session count")
        response = client.table("messages").select("*").execute()

        # Count unique session IDs
        unique_sessions = set(msg["session_id"] for msg in response.data)
        session_count = len(unique_sessions)
        logger.info(f"Found {session_count} unique chat sessions")
        return session_count
    except Exception as e:
        logger.error(f"Error getting session count: {e}")
        return 0


def delete_session_messages(session_id: str):
    """Delete all messages from a specific session.

    Args:
        session_id: UUID of the chat session to delete
    """
    client = get_db_connection()

    try:
        logger.info(f"Deleting all messages for session: {session_id}")
        client.table("messages").delete().eq("session_id", session_id).execute()
        logger.info(f"Successfully deleted messages for session: {session_id}")
    except Exception as e:
        logger.error(f"Error deleting session messages for {session_id}: {e}")


def save_api_call(
    input_tokens: int,
    output_tokens: int,
    tool_used: str = None,
    session_id: str = None,
):
    """Log a Claude API call to the Supabase database.

    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        tool_used: Name of tool used (if any)
        session_id: UUID for the chat dialog session
    """
    client = get_db_connection()
    timestamp = datetime.now().isoformat()

    try:
        logger.info(f"Logging API call - input: {input_tokens}, output: {output_tokens}, tool: {tool_used}, session: {session_id}")
        client.table("api_calls").insert(
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "tool_used": tool_used,
                "session_id": session_id,
                "timestamp": timestamp,
            }
        ).execute()
        logger.info("Successfully logged API call")
    except Exception as e:
        logger.error(f"Error logging API call: {e}")


def get_all_sessions():
    """Get all unique sessions with metadata.

    Returns:
        List of dictionaries with session_id, message_count, first_message_time, last_message_time
    """
    client = get_db_connection()

    try:
        logger.info("Fetching all sessions")
        response = client.table("messages").select("*").order("created_at", desc=False).execute()

        if not response.data:
            return []

        # Group messages by session
        sessions = {}
        for msg in response.data:
            sid = msg["session_id"]
            if sid not in sessions:
                sessions[sid] = {
                    "session_id": sid,
                    "messages": [],
                    "first_message_time": msg["created_at"],
                    "last_message_time": msg["created_at"],
                }
            sessions[sid]["messages"].append(msg)
            sessions[sid]["last_message_time"] = msg["created_at"]

        # Convert to list with metadata
        result = []
        for sid, data in sessions.items():
            result.append({
                "session_id": sid,
                "message_count": len(data["messages"]),
                "first_message_time": data["first_message_time"],
                "last_message_time": data["last_message_time"],
                "messages": data["messages"],
            })

        # Sort by last message time (most recent first)
        result.sort(key=lambda x: x["last_message_time"], reverse=True)
        logger.info(f"Found {len(result)} sessions")
        return result
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        return []


def get_all_api_calls():
    """Get all API call records for metrics.

    Returns:
        List of API call dictionaries
    """
    client = get_db_connection()

    try:
        logger.info("Fetching all API calls")
        response = client.table("api_calls").select("*").order("timestamp", desc=True).execute()

        call_count = len(response.data) if response.data else 0
        logger.info(f"Retrieved {call_count} API calls")
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching API calls: {e}")
        return []


def get_api_calls_by_session(session_id: str):
    """Get API calls for a specific session.

    Args:
        session_id: UUID of the chat session

    Returns:
        List of API call dictionaries
    """
    client = get_db_connection()

    try:
        logger.info(f"Fetching API calls for session: {session_id}")
        response = (
            client.table("api_calls")
            .select("*")
            .eq("session_id", session_id)
            .order("timestamp", desc=False)
            .execute()
        )

        call_count = len(response.data) if response.data else 0
        logger.info(f"Retrieved {call_count} API calls for session: {session_id}")
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching API calls for session {session_id}: {e}")
        return []
