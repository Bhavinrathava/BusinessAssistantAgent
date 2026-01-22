import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import uuid
import streamlit as st

# Database connection parameters from Streamlit secrets
DB_CONFIG = {
    "host": st.secrets["db_host"],
    "port": st.secrets["db_port"],
    "database": st.secrets["db_name"],
    "user": st.secrets["db_user"],
    "password": st.secrets["db_password"],
}


def get_db_connection():
    """Get a PostgreSQL database connection."""
    return psycopg2.connect(**DB_CONFIG)


def initialize_database():
    """Create the messages table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            message_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            show_calendly BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_session_id (session_id),
            INDEX idx_created_at (created_at)
        );
    """
    )

    conn.commit()
    cursor.close()
    conn.close()


def save_message_to_db(
    role: str, content: str, show_calendly: bool = False, session_id: str = None
):
    """Save a message to the PostgreSQL database.

    Args:
        role: "user" or "assistant"
        content: The message content
        show_calendly: Whether a calendly link was shown (for assistant messages)
        session_id: UUID for the chat dialog session
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    message_id = str(uuid.uuid4())
    session_id = session_id or str(uuid.uuid4())
    timestamp = datetime.now()

    try:
        cursor.execute(
            """
            INSERT INTO messages (message_id, session_id, role, content, show_calendly, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (message_id, session_id, role, content, show_calendly, timestamp),
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error saving message to database: {e}")
    finally:
        cursor.close()
        conn.close()


def get_messages_by_session(session_id: str):
    """Retrieve all messages for a specific session.

    Args:
        session_id: UUID of the chat session

    Returns:
        List of message dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT message_id, session_id, role, content, show_calendly, created_at
        FROM messages
        WHERE session_id = %s
        ORDER BY created_at ASC
    """,
        (session_id,),
    )

    messages = cursor.fetchall()
    cursor.close()
    conn.close()

    return [dict(msg) for msg in messages]


def get_all_messages(limit: int = 1000):
    """Retrieve all messages from the database.

    Args:
        limit: Maximum number of messages to retrieve

    Returns:
        List of message dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT message_id, session_id, role, content, show_calendly, created_at
        FROM messages
        ORDER BY created_at DESC
        LIMIT %s
    """,
        (limit,),
    )

    messages = cursor.fetchall()
    cursor.close()
    conn.close()

    return [dict(msg) for msg in messages]


def get_session_count():
    """Get the total number of unique chat sessions.

    Returns:
        Integer count of sessions
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(DISTINCT session_id) FROM messages")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    return count


def delete_session_messages(session_id: str):
    """Delete all messages from a specific session.

    Args:
        session_id: UUID of the chat session to delete
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM messages WHERE session_id = %s", (session_id,)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error deleting session messages: {e}")
    finally:
        cursor.close()
        conn.close()
