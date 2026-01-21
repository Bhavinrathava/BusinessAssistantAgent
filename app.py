import streamlit as st
from dotenv import load_dotenv
from utils.chat import get_response
from constants import *

load_dotenv()


st.set_page_config(page_title="Claude Chat", page_icon="💬")
st.title("💬 Claude Chat")

# Initialize state
# api_messages: clean messages for API (only role + content)
# ui_messages: messages with extra UI metadata (show_calendly flag)
if "api_messages" not in st.session_state:
    st.session_state.api_messages = []

if "ui_messages" not in st.session_state:
    st.session_state.ui_messages = []

# Display chat history
for message in st.session_state.ui_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Show calendly embed if this message triggered it
        if message.get("show_calendly"):
            st.components.v1.iframe(
                f"{CALENDLY_URL}?embed_type=Inline",
                height=700,
                scrolling=True,
            )

# Chat input
if prompt := st.chat_input("Message Claude..."):
    # Add user message to both lists
    st.session_state.api_messages.append({"role": "user", "content": prompt})
    st.session_state.ui_messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response from Claude
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = get_response(st.session_state.api_messages)
            assistant_message = response["text"]
            show_calendly = response["show_calendly"]

            st.markdown(assistant_message)

            # Show Calendly widget if Claude triggered it
            if show_calendly:
                st.components.v1.iframe(
                    f"{CALENDLY_URL}?embed_type=Inline",
                    height=700,
                    scrolling=True,
                )

    # Add assistant response to both lists
    st.session_state.api_messages.append(
        {"role": "assistant", "content": assistant_message}
    )
    st.session_state.ui_messages.append(
        {
            "role": "assistant",
            "content": assistant_message,
            "show_calendly": show_calendly,
        }
    )
