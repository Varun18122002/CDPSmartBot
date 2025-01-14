# frontend/config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    CDP_PLATFORMS: list = ["Segment", "mParticle", "Lytics", "Zeotap"]
    PAGE_TITLE: str = "CDP Support Chatbot"
    PAGE_ICON: str = "💬"
    
config = Config()