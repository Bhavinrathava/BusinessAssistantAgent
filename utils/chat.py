import anthropic
import streamlit as st
import os
from utils.db_manager import save_api_call

# Try st.secrets first (Streamlit Cloud), fall back to os.getenv (local)
api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)

TOOLS = [
    {
        "name": "show_calendly",
        "description": "Display the booking link to allow the user to schedule an appointment. Use this when the user wants to book, schedule, or set up a meeting/appointment/call.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_information_about_me",
        "description": "Get information about the business. Use this when the user wants to learn about insurance or general information about the business. Specially when the query is not about booking appointment. Use this to get information about the business.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant information from the knowledge base",
                }
            },
            "required": ["query"],
        },
    },
]

SYSTEM_PROMPT = """You are a helpful Physical Therapy Assistant for Bridgeport Physical Wellness.

You help physical therapy patients with:
- Information about physical therapy treatments and exercises
- General questions about our clinic services
- Appointment booking and scheduling
- Recovery tips and rehabilitation guidance
- Insurance and billing questions

When users ask about topics OUTSIDE physical therapy (cooking, sports, politics, tech support, etc.), 
politely decline and redirect them back to physical therapy topics.

Example: User asks "How do I cook pasta?" → Respond: "I'm a Physical Therapy Assistant and can only help with physical therapy, appointments, and clinic services. Do you have any questions about your therapy or scheduling?"

IMPORTANT RULES:
1. After using show_calendly, always ask the user something like "Please let me know if you need any help with the booking" or "Let me know once you've completed your booking".
2. Only use show_calendly when the user EXPLICITLY requests to book/schedule a NEW appointment. Do NOT use it for follow-up messages like "thank you", "thanks", "great", "ok", or general acknowledgments.
3. Once you've shown the calendar, do not show it again unless the user explicitly asks to book another appointment.
4. Be professional, empathetic, and supportive in your tone.
5. Always encourage users to contact our clinic directly for urgent or complex medical concerns.
6. STAY IN CHARACTER: Only respond to physical therapy and clinic-related questions. Politely decline off-topic requests.

Be conversational, helpful, and focused on patient care."""


def get_response(messages: list[dict], session_id: str = None) -> dict:
    """Send messages to Claude and return response with optional tool calls."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
    )

    # Check if Claude wants to use a tool
    show_calendly = False
    query_kb = False
    text_response = ""
    tool_used = None

    for block in response.content:
        if block.type == "tool_use" and block.name == "show_calendly":
            show_calendly = True
            tool_used = "show_calendly"
        elif (
            block.type == "tool_use"
            and block.name == "get_information_about_me"
        ):
            query_kb = True
            tool_used = "get_information_about_me"
            # Execute the KB query and send result back to Claude
            tool_id = block.id
            query = block.input.get("query", "")
            kb_result = get_information_about_me([query])

            # Add assistant's tool use and tool result to messages
            messages.append({"role": "assistant", "content": response.content})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": str(kb_result),
                        }
                    ],
                }
            )

            # Log the first API call (with tool use)
            save_api_call(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                tool_used=tool_used,
                session_id=session_id,
            )

            # Get Claude's final response with the KB information
            final_response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Log the follow-up API call
            save_api_call(
                input_tokens=final_response.usage.input_tokens,
                output_tokens=final_response.usage.output_tokens,
                tool_used=None,
                session_id=session_id,
            )

            # Extract text from final response
            for final_block in final_response.content:
                if final_block.type == "text":
                    text_response = final_block.text
                    break

            return {
                "text": text_response,
                "show_calendly": show_calendly,
                "query_kb": query_kb,
            }
        elif block.type == "text":
            text_response = block.text

    # Log API call for non-KB responses
    save_api_call(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        tool_used=tool_used,
        session_id=session_id,
    )

    return {
        "text": text_response,
        "show_calendly": show_calendly,
        "query_kb": query_kb,
    }


def get_information_about_me(query: str):
    from utils.chroma_db import ChromaDB

    chroma_db = ChromaDB()
    result = chroma_db.search_knowledge_base(query)

    return result
