import streamlit as st
from dotenv import load_dotenv
from utils.chat import get_response
from constants import *

load_dotenv()

# Configure page with PT branding
st.set_page_config(
    page_title="Bridgeport Physical Wellness",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom theme styling
st.markdown("""
    <style>
    .main-title {
        color: #1e40af;
        text-align: center;
        margin-bottom: 10px;
    }
    .subtitle {
        color: #64748b;
        text-align: center;
        font-size: 16px;
        margin-bottom: 30px;
    }
    .footer {
        text-align: center;
        padding: 20px;
        margin-top: 50px;
        border-top: 2px solid #e2e8f0;
        color: #64748b;
        font-size: 14px;
    }
    .footer-link {
        color: #1e40af;
        text-decoration: none;
        font-weight: 500;
    }
    .footer-link:hover {
        text-decoration: underline;
    }
    </style>
""", unsafe_allow_html=True)

# Header with PT branding
st.markdown('<h1 class="main-title">💪 Bridgeport Physical Wellness</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Your Personal Physical Therapy Assistant</p>', unsafe_allow_html=True)
st.divider()

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
        # Show booking link if this message triggered it
        if message.get("show_calendly"):
            st.markdown(
                f"[📅 Book an Appointment]({CALENDLY_URL})",
                unsafe_allow_html=False,
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

            # Show booking link if Claude triggered it
            if show_calendly:
                st.markdown(
                    f"[📅 Book an Appointment]({CALENDLY_URL})",
                    unsafe_allow_html=False,
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

# Sidebar with clinic information
with st.sidebar:
    st.header("📋 Clinic Info")
    
    with st.expander("📍 Location", expanded=False):
        st.markdown(
            '[View on Google Maps](https://maps.app.goo.gl/Hi9anpbAxdsNt3ej9)',
            unsafe_allow_html=False
        )
        st.caption("Bridgeport Physical Wellness")
    
    with st.expander("📞 Contact", expanded=False):
        st.markdown("[+1 (312) 298-9867](tel:+13122989867)")
        st.caption("Call us for more information")
    
    with st.expander("🔗 Book Appointment", expanded=False):
        st.markdown(
            f'[Schedule Now]({CALENDLY_URL})',
            unsafe_allow_html=False
        )
        st.caption("Book your session online")
