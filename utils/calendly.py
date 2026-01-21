from calendly_integration import CalendlyIntegration
import streamlit as st
import os


class Calendly:
    def __init__(self):
        # Try st.secrets first (Streamlit Cloud), fall back to os.getenv (local)
        api_token = st.secrets.get("CALENDLY_API_TOKEN") or os.getenv(
            "CALENDLY_API_TOKEN"
        )
        self.calendly = CalendlyIntegration(api_token)
        pass

    def get_available_slots(self):
        """Get available appointment slots"""
        # Get available slots
        event_type = st.secrets.get("CALENDLY_EVENT_TYPE") or os.getenv(
            "CALENDLY_EVENT_TYPE"
        )
        slots = self.calendly.get_available_times(
            event_type, timezone="America/Los_Angeles"
        )

        return slots

    def book_appointment(self):
        """Book an appointment"""
        pass
