import os
import anthropic
import json
from datetime import datetime, timedelta
import re
import streamlit as st

# Initialize Anthropic client
# Try st.secrets first (Streamlit Cloud), fall back to os.getenv (local)
api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)

# Mock data - you'll replace with real integrations later
MOCK_CALENDAR = {
    "therapist_1": {
        "name": "Sarah",
        "specialty": "PT",
        "available_slots": [
            {"date": "2025-01-22", "time": "09:00", "duration_min": 60},
            {"date": "2025-01-22", "time": "10:30", "duration_min": 60},
            {"date": "2025-01-22", "time": "14:00", "duration_min": 60},
            {"date": "2025-01-23", "time": "11:00", "duration_min": 60},
            {"date": "2025-01-23", "time": "15:00", "duration_min": 60},
        ],
    },
    "therapist_2": {
        "name": "Mike",
        "specialty": "OT",
        "available_slots": [
            {"date": "2025-01-22", "time": "13:00", "duration_min": 60},
            {"date": "2025-01-24", "time": "10:00", "duration_min": 60},
            {"date": "2025-01-24", "time": "16:00", "duration_min": 60},
        ],
    },
}

BOOKED_APPOINTMENTS = {}
APPOINTMENT_COUNTER = 1000

# Define tools for Claude to use
TOOLS = [
    {
        "name": "get_available_slots",
        "description": "Retrieve available appointment slots for a specific therapist and date range. Returns a list of available time slots.",
        "input_schema": {
            "type": "object",
            "properties": {
                "therapist_id": {
                    "type": "string",
                    "description": "The ID of the therapist (e.g., 'therapist_1', 'therapist_2')",
                },
                "service_type": {
                    "type": "string",
                    "enum": ["PT", "OT"],
                    "description": "Type of physical therapy service needed",
                },
                "preferred_date": {
                    "type": "string",
                    "description": "Preferred date in YYYY-MM-DD format (optional, if not provided will return upcoming slots)",
                },
                "preferred_time": {
                    "type": "string",
                    "enum": ["morning", "afternoon", "evening"],
                    "description": "Preferred time of day (optional)",
                },
            },
            "required": ["service_type"],
        },
    },
    {
        "name": "book_appointment",
        "description": "Book an appointment for the patient. Requires appointment details including therapist, date, and time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "Full name of the patient",
                },
                "patient_phone": {
                    "type": "string",
                    "description": "Patient's phone number",
                },
                "patient_email": {
                    "type": "string",
                    "description": "Patient's email address",
                },
                "therapist_id": {
                    "type": "string",
                    "description": "The ID of the therapist",
                },
                "appointment_date": {
                    "type": "string",
                    "description": "Appointment date in YYYY-MM-DD format",
                },
                "appointment_time": {
                    "type": "string",
                    "description": "Appointment time in HH:MM format",
                },
                "service_type": {
                    "type": "string",
                    "enum": ["PT", "OT"],
                    "description": "Type of service",
                },
                "reason_for_visit": {
                    "type": "string",
                    "description": "Brief reason for the appointment (e.g., 'knee pain', 'shoulder injury')",
                },
            },
            "required": [
                "patient_name",
                "patient_phone",
                "patient_email",
                "therapist_id",
                "appointment_date",
                "appointment_time",
                "service_type",
            ],
        },
    },
    {
        "name": "get_therapist_list",
        "description": "Get a list of available therapists with their specialties",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_type": {
                    "type": "string",
                    "enum": ["PT", "OT"],
                    "description": "Filter by service type (optional)",
                }
            },
        },
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment using the appointment ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "The unique appointment ID",
                }
            },
            "required": ["appointment_id"],
        },
    },
]


# Tool implementation functions
def get_therapist_list(service_type=None):
    """Get list of available therapists"""
    therapists = []
    for therapist_id, info in MOCK_CALENDAR.items():
        if service_type is None or info["specialty"] == service_type:
            therapists.append(
                {
                    "therapist_id": therapist_id,
                    "name": info["name"],
                    "specialty": info["specialty"],
                }
            )
    return therapists


def get_available_slots(
    service_type, therapist_id=None, preferred_date=None, preferred_time=None
):
    """Get available appointment slots"""
    available = []

    # Filter by therapist if specified
    therapists_to_check = (
        {therapist_id: MOCK_CALENDAR[therapist_id]}
        if therapist_id
        else MOCK_CALENDAR
    )

    for tid, therapist_info in therapists_to_check.items():
        if therapist_info["specialty"] != service_type:
            continue

        for slot in therapist_info["available_slots"]:
            slot_date = slot["date"]
            slot_time = slot["time"]

            # Filter by preferred date if provided
            if preferred_date and slot_date != preferred_date:
                continue

            # Filter by preferred time if provided
            if preferred_time:
                hour = int(slot_time.split(":")[0])
                if preferred_time == "morning" and not (8 <= hour < 12):
                    continue
                elif preferred_time == "afternoon" and not (12 <= hour < 17):
                    continue
                elif preferred_time == "evening" and not (17 <= hour < 21):
                    continue

            available.append(
                {
                    "therapist_id": tid,
                    "therapist_name": therapist_info["name"],
                    "date": slot_date,
                    "time": slot_time,
                    "duration_minutes": slot["duration_min"],
                }
            )

    return (
        available
        if available
        else {
            "message": "No available slots found. Please try different criteria."
        }
    )


def book_appointment(
    patient_name,
    patient_phone,
    patient_email,
    therapist_id,
    appointment_date,
    appointment_time,
    service_type,
    reason_for_visit=None,
):
    """Book an appointment"""
    global APPOINTMENT_COUNTER

    # Validate therapist exists
    if therapist_id not in MOCK_CALENDAR:
        return {"success": False, "message": "Invalid therapist ID"}

    # Validate slot is available
    therapist = MOCK_CALENDAR[therapist_id]
    slot_exists = any(
        slot["date"] == appointment_date and slot["time"] == appointment_time
        for slot in therapist["available_slots"]
    )

    if not slot_exists:
        return {
            "success": False,
            "message": "This time slot is no longer available",
        }

    # Create appointment
    appointment_id = f"APT{APPOINTMENT_COUNTER}"
    APPOINTMENT_COUNTER += 1

    appointment = {
        "appointment_id": appointment_id,
        "patient_name": patient_name,
        "patient_phone": patient_phone,
        "patient_email": patient_email,
        "therapist_id": therapist_id,
        "therapist_name": therapist["name"],
        "date": appointment_date,
        "time": appointment_time,
        "service_type": service_type,
        "reason_for_visit": reason_for_visit or "Not specified",
        "booked_at": datetime.now().isoformat(),
    }

    BOOKED_APPOINTMENTS[appointment_id] = appointment

    # Remove from available slots (in production, would update database)
    therapist["available_slots"] = [
        slot
        for slot in therapist["available_slots"]
        if not (
            slot["date"] == appointment_date
            and slot["time"] == appointment_time
        )
    ]

    return {
        "success": True,
        "message": f"Appointment successfully booked!",
        "appointment": appointment,
    }


def cancel_appointment(appointment_id):
    """Cancel an existing appointment"""
    if appointment_id not in BOOKED_APPOINTMENTS:
        return {
            "success": False,
            "message": f"Appointment {appointment_id} not found",
        }

    appointment = BOOKED_APPOINTMENTS[appointment_id]

    # Add slot back to available
    therapist_id = appointment["therapist_id"]
    MOCK_CALENDAR[therapist_id]["available_slots"].append(
        {
            "date": appointment["date"],
            "time": appointment["time"],
            "duration_min": 60,
        }
    )

    del BOOKED_APPOINTMENTS[appointment_id]

    return {
        "success": True,
        "message": f"Appointment {appointment_id} has been cancelled",
    }


def process_tool_call(tool_name, tool_input):
    """Process tool calls from Claude"""
    if tool_name == "get_therapist_list":
        return get_therapist_list(tool_input.get("service_type"))
    elif tool_name == "get_available_slots":
        return get_available_slots(
            service_type=tool_input.get("service_type"),
            therapist_id=tool_input.get("therapist_id"),
            preferred_date=tool_input.get("preferred_date"),
            preferred_time=tool_input.get("preferred_time"),
        )
    elif tool_name == "book_appointment":
        return book_appointment(
            patient_name=tool_input.get("patient_name"),
            patient_phone=tool_input.get("patient_phone"),
            patient_email=tool_input.get("patient_email"),
            therapist_id=tool_input.get("therapist_id"),
            appointment_date=tool_input.get("appointment_date"),
            appointment_time=tool_input.get("appointment_time"),
            service_type=tool_input.get("service_type"),
            reason_for_visit=tool_input.get("reason_for_visit"),
        )
    elif tool_name == "cancel_appointment":
        return cancel_appointment(
            appointment_id=tool_input.get("appointment_id")
        )
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def run_appointment_agent(user_message):
    """Run the appointment scheduling agent"""

    system_prompt = """You are a helpful physical therapy clinic appointment scheduling assistant. 
Your role is to help patients schedule, reschedule, or cancel appointments.

When a patient wants to book an appointment:
1. First, determine what type of service they need (PT or OT)
2. Check available therapists and slots
3. Ask clarifying questions if needed (preferred date/time, reason for visit, contact info)
4. Book the appointment once you have all required information

Be friendly, professional, and ask for clarification if the user's request is ambiguous.
Always confirm appointment details before finalizing the booking.

Current date: 2025-01-21"""

    messages = [{"role": "user", "content": user_message}]

    print(f"\n{'='*60}")
    print(f"User: {user_message}")
    print(f"{'='*60}")

    # Agentic loop
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Process tool calls
            tool_calls = [
                block for block in response.content if block.type == "tool_use"
            ]

            # Add assistant's response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Process each tool call
            tool_results = []
            for tool_call in tool_calls:
                print(f"\n[Tool Call] {tool_call.name}")
                print(f"Input: {json.dumps(tool_call.input, indent=2)}")

                result = process_tool_call(tool_call.name, tool_call.input)
                print(f"Result: {json.dumps(result, indent=2)}")

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )

            # Add tool results to messages
            messages.append({"role": "user", "content": tool_results})

        else:
            # Claude has finished - extract the final response
            final_response = next(
                (
                    block.text
                    for block in response.content
                    if hasattr(block, "text")
                ),
                None,
            )
            print(f"\nAssistant: {final_response}")
            print(f"{'='*60}\n")
            return final_response


if __name__ == "__main__":
    # Test examples
    test_queries = [
        "I'd like to schedule a PT appointment for next Wednesday afternoon. My name is John Smith, phone is 555-0123, and email is john@example.com",
        "Do you have any OT appointments available? I'm looking for something early next week.",
        "I need to cancel appointment APT1000",
    ]

    for query in test_queries:
        run_appointment_agent(query)
