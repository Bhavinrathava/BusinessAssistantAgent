from calendly_integration import CalendlyIntegration
import os


class Calendly:
    def __init__(self):
        self.calendly = CalendlyIntegration(os.getenv("CALENDLY_API_TOKEN"))
        pass

    def get_available_slots(self):
        """Get available appointment slots"""
        # Get available slots
        slots = self.calendly.get_available_times(
            os.getenv("CALENDLY_EVENT_TYPE"), timezone="America/Los_Angeles"
        )

        return slots

    def book_appointment(self):
        """Book an appointment"""
        pass
