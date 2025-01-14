# frontend/app.py
import streamlit as st
import requests
import json
from typing import List, Dict
import time

# Constants
API_BASE_URL = "http://localhost:8000"
CDP_PLATFORMS = ["Segment", "mParticle", "Lytics", "Zeotap"]

# Page configuration
st.set_page_config(
    page_title="CDP Support Chatbot",
    page_icon="💬",
    layout="wide"
)

# Initialize session state for chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

def send_message(query: str, platform: str) -> Dict:
    """Send message to backend API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/chat/query",
            json={"query": query, "platform": platform}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with backend: {str(e)}")
        return None

def main():
    # Title and description
    st.title("CDP Support Chatbot 💬")
    st.markdown("""
    Ask me any questions about CDP platforms! I'm here to help you understand:
    - How to set up and configure sources
    - How to manage integrations
    - How to handle data tracking
    - And much more!
    """)

    # Sidebar for platform selection
    with st.sidebar:
        st.header("Settings")
        selected_platform = st.selectbox(
            "Select CDP Platform",
            CDP_PLATFORMS
        )
        
        # Add platform information
        st.markdown("---")
        st.markdown(f"### About {selected_platform}")
        platform_info = {
            "Segment": "A customer data platform that helps you collect, clean, and control customer data.",
            "mParticle": "A customer data infrastructure that helps you integrate and orchestrate all of your data.",
            "Lytics": "A customer data platform that helps you create and activate segments.",
            "Zeotap": "A customer intelligence platform that helps you unify and activate customer data."
        }
        st.markdown(platform_info[selected_platform])
        
        # Clear chat button
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()

    # Chat interface
    chat_container = st.container()
    
    # Display chat messages
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask your question here..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Show thinking message
        with st.chat_message("assistant"):
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("🤔 Thinking...")
            
            # Send message to backend
            response = send_message(prompt, selected_platform)
            
            if response:
                # Update thinking message with actual response
                thinking_placeholder.markdown(response["response"])
                # Add assistant response to chat history
                st.session_state.messages.append(
                    {"role": "assistant", "content": response["response"]}
                )
            else:
                thinking_placeholder.markdown("❌ Sorry, I couldn't process your request. Please try again.")

    # Add some styling
    st.markdown("""
    <style>
    .stChat {
        padding: 20px;
    }
    .stChatMessage {
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()