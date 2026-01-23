import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db_manager import (
    get_all_sessions,
    get_all_api_calls,
    get_messages_by_session,
    get_api_calls_by_session,
)
from utils.chroma_db import ChromaDB

st.set_page_config(
    page_title="Management Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Management Dashboard")

# Sidebar navigation
page = st.sidebar.radio(
    "Navigation",
    ["Conversations", "Token Usage Metrics", "Edit Details"],
    index=0,
)

# -----------------------------------------------------------------------------
# Conversations Page
# -----------------------------------------------------------------------------
if page == "Conversations":
    st.header("💬 Conversation History")

    sessions = get_all_sessions()

    if not sessions:
        st.info("No conversations found.")
    else:
        st.write(f"**Total Sessions:** {len(sessions)}")

        # Filter options
        col1, col2 = st.columns([2, 1])
        with col1:
            search_term = st.text_input(
                "Search conversations",
                placeholder="Search by message content...",
            )
        with col2:
            sort_order = st.selectbox(
                "Sort by",
                ["Most Recent", "Oldest First", "Most Messages"],
            )

        # Apply sorting
        if sort_order == "Most Recent":
            sessions = sorted(sessions, key=lambda x: x["last_message_time"], reverse=True)
        elif sort_order == "Oldest First":
            sessions = sorted(sessions, key=lambda x: x["first_message_time"])
        elif sort_order == "Most Messages":
            sessions = sorted(sessions, key=lambda x: x["message_count"], reverse=True)

        # Filter by search term
        if search_term:
            filtered_sessions = []
            for session in sessions:
                for msg in session["messages"]:
                    if search_term.lower() in msg["content"].lower():
                        filtered_sessions.append(session)
                        break
            sessions = filtered_sessions

        st.divider()

        # Display sessions
        for i, session in enumerate(sessions):
            session_id = session["session_id"]
            message_count = session["message_count"]
            first_time = session["first_message_time"]
            messages = session["messages"]

            # Parse timestamp for display
            try:
                dt = datetime.fromisoformat(first_time.replace("Z", "+00:00"))
                formatted_time = dt.strftime("%b %d, %Y %I:%M %p")
            except:
                formatted_time = first_time[:19]

            # Get first user message as preview
            first_user_msg = next(
                (m["content"] for m in messages if m["role"] == "user"),
                "No user message",
            )
            preview = first_user_msg[:100] + "..." if len(first_user_msg) > 100 else first_user_msg

            # Generate summary from conversation
            def generate_summary(msgs):
                """Generate a brief summary of the conversation."""
                user_messages = [m["content"] for m in msgs if m["role"] == "user"]
                assistant_messages = [m["content"] for m in msgs if m["role"] == "assistant"]

                topics = []
                # Check for common topics
                all_content = " ".join(user_messages).lower()
                if any(word in all_content for word in ["appointment", "book", "schedule", "calendly"]):
                    topics.append("Appointment booking")
                if any(word in all_content for word in ["insurance", "coverage", "plan"]):
                    topics.append("Insurance inquiry")
                if any(word in all_content for word in ["price", "cost", "fee", "payment"]):
                    topics.append("Pricing questions")
                if any(word in all_content for word in ["service", "treatment", "therapy"]):
                    topics.append("Service information")
                if any(word in all_content for word in ["location", "address", "hour", "open"]):
                    topics.append("Location/Hours")

                if topics:
                    return ", ".join(topics)
                return "General inquiry"

            summary = generate_summary(messages)

            # Expandable card for each session
            with st.expander(
                f"**{formatted_time}** | {message_count} messages | {summary}",
                expanded=False,
            ):
                st.caption(f"Session ID: `{session_id}`")

                # Get token usage for this session
                api_calls = get_api_calls_by_session(session_id)
                if api_calls:
                    total_input = sum(c.get("input_tokens", 0) or 0 for c in api_calls)
                    total_output = sum(c.get("output_tokens", 0) or 0 for c in api_calls)
                    st.caption(
                        f"Token usage: {total_input:,} input / {total_output:,} output"
                    )

                st.divider()

                # Display messages
                for msg in messages:
                    role = msg["role"]
                    content = msg["content"]
                    show_calendly = msg.get("show_calendly", False)

                    if role == "user":
                        st.markdown(f"**🧑 User:**")
                        st.markdown(f"> {content}")
                    else:
                        st.markdown(f"**🤖 Assistant:**")
                        st.markdown(f"> {content}")
                        if show_calendly:
                            st.caption("📅 Calendly link was shown")

                    st.write("")

# -----------------------------------------------------------------------------
# Token Usage Metrics Page
# -----------------------------------------------------------------------------
elif page == "Token Usage Metrics":
    st.header("📈 Token Usage Metrics")

    api_calls = get_all_api_calls()

    if not api_calls:
        st.info("No API call data found.")
    else:
        # Convert to DataFrame for analysis
        df = pd.DataFrame(api_calls)

        # Handle missing columns
        if "input_tokens" not in df.columns:
            df["input_tokens"] = 0
        if "output_tokens" not in df.columns:
            df["output_tokens"] = 0
        if "tool_used" not in df.columns:
            df["tool_used"] = None
        if "timestamp" not in df.columns:
            df["timestamp"] = None

        # Fill NaN values
        df["input_tokens"] = df["input_tokens"].fillna(0).astype(int)
        df["output_tokens"] = df["output_tokens"].fillna(0).astype(int)
        df["total_tokens"] = df["input_tokens"] + df["output_tokens"]

        # Overall metrics
        st.subheader("Overall Statistics")
        col1, col2, col3, col4 = st.columns(4)

        total_input = df["input_tokens"].sum()
        total_output = df["output_tokens"].sum()
        total_tokens = total_input + total_output
        total_calls = len(df)

        col1.metric("Total API Calls", f"{total_calls:,}")
        col2.metric("Total Input Tokens", f"{total_input:,}")
        col3.metric("Total Output Tokens", f"{total_output:,}")
        col4.metric("Total Tokens", f"{total_tokens:,}")

        # Estimated cost (Claude Sonnet pricing: $3/1M input, $15/1M output)
        st.subheader("Estimated Cost")
        input_cost = (total_input / 1_000_000) * 3
        output_cost = (total_output / 1_000_000) * 15
        total_cost = input_cost + output_cost

        col1, col2, col3 = st.columns(3)
        col1.metric("Input Cost", f"${input_cost:.4f}")
        col2.metric("Output Cost", f"${output_cost:.4f}")
        col3.metric("Total Cost", f"${total_cost:.4f}")

        st.caption("*Estimated based on Claude Sonnet pricing: $3/1M input, $15/1M output*")

        st.divider()

        # Token usage over time
        st.subheader("Token Usage Over Time")
        if df["timestamp"].notna().any():
            df["date"] = pd.to_datetime(df["timestamp"]).dt.date
            daily_usage = df.groupby("date").agg({
                "input_tokens": "sum",
                "output_tokens": "sum",
                "total_tokens": "sum",
            }).reset_index()

            st.line_chart(
                daily_usage.set_index("date")[["input_tokens", "output_tokens"]],
                use_container_width=True,
            )
        else:
            st.info("No timestamp data available for time series.")

        st.divider()

        # Tool usage breakdown
        st.subheader("Tool Usage Breakdown")
        tool_counts = df["tool_used"].value_counts(dropna=False)
        tool_counts.index = tool_counts.index.fillna("No tool")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Calls by Tool**")
            tool_df = pd.DataFrame({
                "Tool": tool_counts.index,
                "Count": tool_counts.values,
            })
            st.dataframe(tool_df, use_container_width=True, hide_index=True)

        with col2:
            st.write("**Distribution**")
            st.bar_chart(tool_counts, use_container_width=True)

        st.divider()

        # Token usage by session
        st.subheader("Token Usage by Session")
        if "session_id" in df.columns and df["session_id"].notna().any():
            session_usage = df.groupby("session_id").agg({
                "input_tokens": "sum",
                "output_tokens": "sum",
                "total_tokens": "sum",
            }).reset_index()

            session_usage = session_usage.sort_values("total_tokens", ascending=False)

            # Show top 10 sessions
            st.write("**Top 10 Sessions by Token Usage**")
            top_sessions = session_usage.head(10).copy()
            top_sessions["session_id"] = top_sessions["session_id"].str[:8] + "..."
            st.dataframe(
                top_sessions.rename(columns={
                    "session_id": "Session",
                    "input_tokens": "Input",
                    "output_tokens": "Output",
                    "total_tokens": "Total",
                }),
                use_container_width=True,
                hide_index=True,
            )

            # Bar chart
            st.bar_chart(
                top_sessions.set_index("session_id")["total_tokens"],
                use_container_width=True,
            )
        else:
            st.info("No session data available.")

        st.divider()

        # Averages
        st.subheader("Averages")
        col1, col2, col3 = st.columns(3)

        avg_input = df["input_tokens"].mean()
        avg_output = df["output_tokens"].mean()
        avg_total = df["total_tokens"].mean()

        col1.metric("Avg Input Tokens/Call", f"{avg_input:,.0f}")
        col2.metric("Avg Output Tokens/Call", f"{avg_output:,.0f}")
        col3.metric("Avg Total Tokens/Call", f"{avg_total:,.0f}")

        st.divider()

        # Raw data view
        st.subheader("Raw API Call Data")
        with st.expander("View raw data"):
            display_df = df.copy()
            if "timestamp" in display_df.columns:
                display_df = display_df.sort_values("timestamp", ascending=False)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Edit Details Page
# -----------------------------------------------------------------------------
elif page == "Edit Details":
    st.header("📝 Knowledge Base Management")

    # Initialize ChromaDB
    @st.cache_resource
    def get_chroma_db():
        return ChromaDB()

    chroma_db = get_chroma_db()

    # Create tabs for different operations
    tab1, tab2 = st.tabs(["Manage Documents", "Add New Document"])

    # -------------------------------------------------------------------------
    # Tab 1: Manage Existing Documents
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("Existing Documents")

        # Refresh button
        if st.button("🔄 Refresh Documents", key="refresh_docs"):
            st.cache_resource.clear()
            st.rerun()

        # Get all documents
        documents = chroma_db.get_all_documents()

        if not documents:
            st.info("No documents found in the knowledge base.")
        else:
            st.write(f"**Total Documents:** {len(documents)}")
            st.divider()

            # Display each document with edit/delete options
            for doc in documents:
                doc_id = doc["id"]
                doc_content = doc["content"]

                with st.expander(f"📄 {doc_id}", expanded=False):
                    st.caption(f"Document ID: `{doc_id}`")

                    # Use session state to track edit mode
                    edit_key = f"edit_mode_{doc_id}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False

                    if st.session_state[edit_key]:
                        # Edit mode
                        new_content = st.text_area(
                            "Edit content:",
                            value=doc_content,
                            height=300,
                            key=f"edit_content_{doc_id}",
                        )

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 Save Changes", key=f"save_{doc_id}"):
                                if new_content.strip():
                                    chroma_db.update_document(doc_id, new_content)
                                    st.session_state[edit_key] = False
                                    st.success(f"Document '{doc_id}' updated successfully!")
                                    st.cache_resource.clear()
                                    st.rerun()
                                else:
                                    st.error("Document content cannot be empty.")
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_{doc_id}"):
                                st.session_state[edit_key] = False
                                st.rerun()
                    else:
                        # View mode
                        st.text_area(
                            "Content:",
                            value=doc_content,
                            height=200,
                            disabled=True,
                            key=f"view_content_{doc_id}",
                        )

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✏️ Edit", key=f"edit_btn_{doc_id}"):
                                st.session_state[edit_key] = True
                                st.rerun()
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_btn_{doc_id}"):
                                st.session_state[f"confirm_delete_{doc_id}"] = True

                        # Confirm delete dialog
                        if st.session_state.get(f"confirm_delete_{doc_id}", False):
                            st.warning(f"Are you sure you want to delete '{doc_id}'?")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Yes, Delete", key=f"confirm_del_{doc_id}"):
                                    chroma_db.delete_document(doc_id)
                                    st.session_state[f"confirm_delete_{doc_id}"] = False
                                    st.success(f"Document '{doc_id}' deleted successfully!")
                                    st.cache_resource.clear()
                                    st.rerun()
                            with col2:
                                if st.button("No, Cancel", key=f"cancel_del_{doc_id}"):
                                    st.session_state[f"confirm_delete_{doc_id}"] = False
                                    st.rerun()

    # -------------------------------------------------------------------------
    # Tab 2: Add New Document
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("Add New Document")

        # Document ID input
        new_doc_id = st.text_input(
            "Document ID",
            placeholder="e.g., services.txt, faq.txt",
            help="A unique identifier for this document. Use descriptive names.",
        )

        # Document content input
        new_doc_content = st.text_area(
            "Document Content",
            placeholder="Enter the document content here...",
            height=300,
            help="The text content that will be added to the knowledge base.",
        )

        # Add button
        if st.button("➕ Add Document", type="primary"):
            if not new_doc_id.strip():
                st.error("Please provide a document ID.")
            elif not new_doc_content.strip():
                st.error("Please provide document content.")
            else:
                # Check if document already exists
                existing_docs = chroma_db.get_all_documents()
                existing_ids = [d["id"] for d in existing_docs]

                if new_doc_id in existing_ids:
                    st.error(
                        f"Document with ID '{new_doc_id}' already exists. "
                        "Use the 'Manage Documents' tab to edit it."
                    )
                else:
                    chroma_db.add_to_knowledge_base(new_doc_content, new_doc_id)
                    st.success(f"Document '{new_doc_id}' added successfully!")
                    st.cache_resource.clear()
                    st.rerun()
