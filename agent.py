import os
import base64
import time
import json
import requests
import re
import logging
import threading
import sqlite3
import csv
import random
import string
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException, ElementClickInterceptedException, 
    ElementNotInteractableException, NoSuchElementException,
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import asyncio
import numpy as np
import cv2

# Load environment variables
load_dotenv()

# Optimize HTTP connection pools for 50 FPS streaming
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure urllib3 to handle high-frequency requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create optimized session for high-frequency requests
def create_optimized_session():
    """Create a requests session optimized for high-frequency streaming."""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        backoff_factor=0.1
    )
    
    # Configure HTTP adapter with larger connection pool
    adapter = HTTPAdapter(
        pool_connections=50,    # Increased for 50 FPS
        pool_maxsize=100,       # Increased pool size
        max_retries=retry_strategy,
        pool_block=False
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# Global optimized session for reuse
_optimized_session = create_optimized_session()

# Setup advanced logging
os.makedirs('logs', exist_ok=True)
os.makedirs('screenshots', exist_ok=True)
os.makedirs('downloads', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Configure advanced logging with multiple handlers
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)

# File handler
file_handler = logging.FileHandler('logs/mega_browser_agent.log', encoding='utf-8')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
console_handler.setLevel(logging.INFO)

# Error handler (separate file for errors)
error_handler = logging.FileHandler('logs/errors.log', encoding='utf-8')
error_handler.setFormatter(log_formatter)
error_handler.setLevel(logging.ERROR)

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.addHandler(error_handler)

# Atharva Agent - Gemini AI Configuration
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', os.getenv('ATHARVA_API_KEY'))
GEMINI_MODEL = os.getenv('ATHARVA_MODEL', 'gemini-2.0-flash')

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found. Please check your .env file.")

# Initialize Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

@dataclass
class ElementInfo:
    """Advanced element information structure."""
    id: int
    element: Any
    tag_name: str
    label: str
    element_type: str
    is_visible: bool
    is_clickable: bool
    is_form_field: bool
    coordinates: Tuple[int, int, int, int]
    attributes: Dict[str, str]
    text_content: str
    confidence_score: float

@dataclass
class ActionResult:
    """Advanced action result structure."""
    success: bool
    action_type: str
    message: str
    duration: float
    screenshot_path: Optional[str]
    element_id: Optional[int]
    error_details: Optional[str]
    timestamp: datetime

class AdvancedDatabase:
    """Advanced database manager for browser agent."""
    
    def __init__(self, db_path: str = "data/browser_agent.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with all necessary tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Actions history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS actions_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    url TEXT,
                    element_id INTEGER,
                    parameters TEXT,
                    result TEXT,
                    duration REAL,
                    screenshot_path TEXT,
                    success BOOLEAN
                )
            ''')
            
            # Website data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS website_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    keywords TEXT,
                    elements_count INTEGER,
                    load_time REAL,
                    screenshot_path TEXT,
                    visit_timestamp TEXT
                )
            ''')
            
            # Form data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS form_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    form_name TEXT,
                    field_name TEXT,
                    field_value TEXT,
                    field_type TEXT,
                    timestamp TEXT
                )
            ''')
            
            # Search results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_engine TEXT,
                    query TEXT,
                    results_count INTEGER,
                    top_result_title TEXT,
                    top_result_url TEXT,
                    timestamp TEXT
                )
            ''')
            
            conn.commit()
    
    def log_action(self, action_result: ActionResult):
        """Log action to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO actions_history 
                (timestamp, action_type, element_id, result, duration, screenshot_path, success)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                action_result.timestamp.isoformat(),
                action_result.action_type,
                action_result.element_id,
                action_result.message,
                action_result.duration,
                action_result.screenshot_path,
                action_result.success
            ))
            conn.commit()

class AdvancedEmailManager:
    """Advanced email management system."""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
    def send_report(self, to_email: str, subject: str, body: str, attachments: List[str] = None):
        """Send email report with attachments."""
        try:
            msg = MIMEMultipart()
            msg['From'] = os.getenv('EMAIL_FROM', 'browser.agent@example.com')
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}',
                        )
                        msg.attach(part)
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(
                os.getenv('EMAIL_USERNAME', ''), 
                os.getenv('EMAIL_PASSWORD', '')
            )
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email report sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

class AdvancedReportGenerator:
    """Advanced report generation system."""
    
    def __init__(self, db: AdvancedDatabase):
        self.db = db
        
    def generate_html_report(self, session_data: Dict) -> str:
        """Generate comprehensive HTML report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"reports/session_report_{timestamp}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Browser Agent Session Report</title>
            <style>
                body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #333; margin-bottom: 10px; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
                .stat-card h3 {{ margin: 0 0 10px 0; }}
                .stat-card .number {{ font-size: 2em; font-weight: bold; }}
                .timeline {{ margin-top: 30px; }}
                .timeline-item {{ background: #f8f9fa; margin: 10px 0; padding: 15px; border-left: 4px solid #667eea; border-radius: 5px; }}
                .success {{ border-left-color: #28a745; }}
                .error {{ border-left-color: #dc3545; }}
                .screenshot {{ max-width: 300px; border-radius: 5px; margin: 10px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 Browser Agent Session Report</h1>
                    <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <h3>Total Actions</h3>
                        <div class="number">{session_data.get('total_actions', 0)}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Success Rate</h3>
                        <div class="number">{session_data.get('success_rate', 0)}%</div>
                    </div>
                    <div class="stat-card">
                        <h3>Websites Visited</h3>
                        <div class="number">{session_data.get('websites_visited', 0)}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Total Duration</h3>
                        <div class="number">{session_data.get('total_duration', 0):.1f}s</div>
                    </div>
                </div>
                
                <div class="timeline">
                    <h2>Action Timeline</h2>
                    {self._generate_timeline_html(session_data.get('actions', []))}
                </div>
                
                <div class="footer">
                    <p>Generated by Atharva Agent v2.0</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {report_path}")
        return report_path
    
    def _generate_timeline_html(self, actions: List[ActionResult]) -> str:
        """Generate timeline HTML for actions."""
        timeline_html = ""
        for action in actions:
            status_class = "success" if action.success else "error"
            timeline_html += f"""
            <div class="timeline-item {status_class}">
                <strong>{action.action_type}</strong> - {action.message}
                <br><small>{action.timestamp.strftime("%H:%M:%S")} | Duration: {action.duration:.2f}s</small>
                {f'<br><img src="{action.screenshot_path}" class="screenshot" alt="Screenshot">' if action.screenshot_path else ''}
            </div>
            """
        return timeline_html

class ChatInterface:
    """Clean, minimal chat interface with modern speech bubble design for AI agent responses."""
    
    def __init__(self):
        self.bubble_id = f"ai-chat-bubble-{uuid.uuid4().hex[:8]}"
        self.default_message = "AI assistant is ready to help you."
    
    def create_chat_bubble(self, message: str = None, position: str = "top-left") -> str:
        """
        Create a clean, minimal chat interface speech bubble for AI responses.
        Modern flat UI design with precise styling as specified.
        
        Args:
            message: The AI response text to display
            position: Position of the bubble (default "top-left" for AI avatar connection)
        
        Returns:
            JavaScript code to inject the chat bubble
        """
        if not message:
            message = self.default_message
        
        # Split message into sentences to make first sentence bold
        sentences = message.split('. ')
        if len(sentences) > 1:
            first_sentence = sentences[0] + '.'
            remaining_text = '. '.join(sentences[1:])
            formatted_message = f"<strong style='font-weight: 600;'>{first_sentence}</strong> {remaining_text}"
        else:
            formatted_message = f"<strong style='font-weight: 600;'>{message}</strong>"
        
        # Position configurations - default to top-left for AI avatar connection
        position_styles = {
            "top-left": "top: 60px; left: 80px;",  # Positioned to connect with AI avatar
            "top-right": "top: 60px; right: 20px;",
            "bottom-left": "bottom: 20px; left: 80px;",
            "bottom-right": "bottom: 20px; right: 20px;"
        }
        
        # Pointer configurations - small triangular pointer at top-left
        pointer_styles = {
            "top-left": "top: -6px; left: 24px; border-bottom: 6px solid #ffffff; border-left: 6px solid transparent; border-right: 6px solid transparent; filter: drop-shadow(0 -1px 1px rgba(0, 0, 0, 0.05));",
            "top-right": "top: -6px; right: 24px; border-bottom: 6px solid #ffffff; border-left: 6px solid transparent; border-right: 6px solid transparent; filter: drop-shadow(0 -1px 1px rgba(0, 0, 0, 0.05));",
            "bottom-left": "bottom: -6px; left: 24px; border-top: 6px solid #ffffff; border-left: 6px solid transparent; border-right: 6px solid transparent; filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.05));",
            "bottom-right": "bottom: -6px; right: 24px; border-top: 6px solid #ffffff; border-left: 6px solid transparent; border-right: 6px solid transparent; filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.05));"
        }
        
        position_css = position_styles.get(position, position_styles["top-left"])
        pointer_css = pointer_styles.get(position, pointer_styles["top-left"])
        
        bubble_js = f"""
        // Remove existing bubble if any
        const existingBubble = document.getElementById('{self.bubble_id}');
        if (existingBubble) {{
            existingBubble.remove();
        }}
        
        // Ensure standard Windows cursor is applied globally
        document.body.style.cursor = 'default';
        document.documentElement.style.cursor = 'default';
        
        // Create chat bubble container with precise specifications
        const chatBubble = document.createElement('div');
        chatBubble.id = '{self.bubble_id}';
        chatBubble.style.cssText = `
            position: fixed;
            {position_css}
            max-width: 280px;
            min-width: 180px;
            background: #ffffff;
            color: #4b5563;
            padding: 14px 16px;
            border-radius: 8px;
            font-family: 'Inter', 'Arial', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 14px;
            line-height: 1.45;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 4px rgba(0, 0, 0, 0.04);
            z-index: 999999;
            opacity: 0;
            transform: translateY(-8px) scale(0.98);
            transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            border: none;
            cursor: default;
            user-select: none;
            font-weight: 400;
            letter-spacing: -0.01em;
        `;
        
        // Create message content with balanced padding
        chatBubble.innerHTML = `
            <div style="
                position: relative; 
                word-wrap: break-word; 
                line-height: 1.45;
                margin: 0;
                padding: 0;
                color: #4b5563;
                cursor: default;
            ">
                {formatted_message}
            </div>
            <div style="
                position: absolute;
                {pointer_css}
                width: 0;
                height: 0;
            "></div>
        `;
        
        document.body.appendChild(chatBubble);
        
        // Animate bubble in with smooth entrance
        setTimeout(() => {{
            chatBubble.style.opacity = '1';
            chatBubble.style.transform = 'translateY(0) scale(1)';
        }}, 50);
        
        // Create subtle hover effect for interactivity
        chatBubble.addEventListener('mouseenter', function() {{
            this.style.boxShadow = '0 3px 12px rgba(0, 0, 0, 0.1), 0 1px 6px rgba(0, 0, 0, 0.06)';
            this.style.transform = 'translateY(-1px) scale(1)';
            document.body.style.cursor = 'default';
        }});
        
        chatBubble.addEventListener('mouseleave', function() {{
            this.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 4px rgba(0, 0, 0, 0.04)';
            this.style.transform = 'translateY(0) scale(1)';
            document.body.style.cursor = 'default';
        }});
        
        // Auto-hide after delay (optional)
        setTimeout(() => {{
            if (document.getElementById('{self.bubble_id}')) {{
                chatBubble.style.opacity = '0';
                chatBubble.style.transform = 'translateY(-8px) scale(0.98)';
                setTimeout(() => {{
                    if (chatBubble.parentNode) {{
                        chatBubble.parentNode.removeChild(chatBubble);
                    }}
                }}, 250);
            }}
        }}, 8000);
        """
        
        return bubble_js
    
    def update_bubble_message(self, new_message: str) -> str:
        """
        Update the message in an existing chat bubble.
        
        Args:
            new_message: New message to display
        
        Returns:
            JavaScript code to update the bubble
        """
        # Split message into sentences to make first sentence bold
        sentences = new_message.split('. ')
        if len(sentences) > 1:
            first_sentence = sentences[0] + '.'
            remaining_text = '. '.join(sentences[1:])
            formatted_message = f"<strong>{first_sentence}</strong> {remaining_text}"
        else:
            formatted_message = f"<strong>{new_message}</strong>"
        
        update_js = f"""
        const existingBubble = document.getElementById('{self.bubble_id}');
        if (existingBubble) {{
            const messageDiv = existingBubble.querySelector('div');
            if (messageDiv) {{
                messageDiv.innerHTML = `{formatted_message}`;
                
                // Add subtle pulse animation for update
                existingBubble.style.transform = 'scale(1.02)';
                setTimeout(() => {{
                    existingBubble.style.transform = 'scale(1)';
                }}, 150);
            }}
        }}
        """
        return update_js
    
    def remove_bubble(self) -> str:
        """
        Remove the chat bubble with smooth animation.
        
        Returns:
            JavaScript code to remove the bubble
        """
        remove_js = f"""
        const bubble = document.getElementById('{self.bubble_id}');
        if (bubble) {{
            bubble.style.opacity = '0';
            bubble.style.transform = 'translateY(-10px) scale(0.95)';
            setTimeout(() => {{
                if (bubble.parentNode) {{
                    bubble.parentNode.removeChild(bubble);
                }}
            }}, 300);
        }}
        """
        return remove_js
    
    def create_typing_indicator(self, position: str = "top-left") -> str:
        """
        Create a clean typing indicator bubble matching the main chat design.
        
        Args:
            position: Position of the bubble
        
        Returns:
            JavaScript code for typing indicator
        """
        position_styles = {
            "top-left": "top: 60px; left: 80px;",
            "top-right": "top: 60px; right: 20px;",
            "bottom-left": "bottom: 20px; left: 80px;",
            "bottom-right": "bottom: 20px; right: 20px;"
        }
        
        position_css = position_styles.get(position, position_styles["top-left"])
        typing_id = f"ai-typing-{uuid.uuid4().hex[:8]}"
        
        typing_js = f"""
        // Ensure standard cursor
        document.body.style.cursor = 'default';
        document.documentElement.style.cursor = 'default';
        
        const typingBubble = document.createElement('div');
        typingBubble.id = '{typing_id}';
        typingBubble.style.cssText = `
            position: fixed;
            {position_css}
            background: #ffffff;
            color: #6b7280;
            padding: 12px 16px;
            border-radius: 8px;
            font-family: 'Inter', 'Arial', 'Segoe UI', sans-serif;
            font-size: 13px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 4px rgba(0, 0, 0, 0.04);
            z-index: 999999;
            opacity: 0;
            transform: scale(0.98);
            transition: all 0.25s ease;
            border: none;
            cursor: default;
            user-select: none;
            letter-spacing: -0.01em;
        `;
        
        typingBubble.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; cursor: default;">
                <div style="display: flex; gap: 3px;">
                    <div style="width: 5px; height: 5px; background: #9ca3af; border-radius: 50%; animation: typing 1.4s infinite;"></div>
                    <div style="width: 5px; height: 5px; background: #9ca3af; border-radius: 50%; animation: typing 1.4s infinite 0.2s;"></div>
                    <div style="width: 5px; height: 5px; background: #9ca3af; border-radius: 50%; animation: typing 1.4s infinite 0.4s;"></div>
                </div>
                <span style="color: #6b7280; font-weight: 400;">AI is thinking...</span>
            </div>
        `;
        
        // Add CSS animation with smooth, subtle movement
        const style = document.createElement('style');
        style.textContent = `
            @keyframes typing {{
                0%, 60%, 100% {{ 
                    opacity: 0.4; 
                    transform: scale(0.9); 
                }}
                30% {{ 
                    opacity: 1; 
                    transform: scale(1.1); 
                }}
            }}
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(typingBubble);
        
        setTimeout(() => {{
            typingBubble.style.opacity = '1';
            typingBubble.style.transform = 'scale(1)';
        }}, 50);
        
        // Return remove function
        window.removeTypingIndicator = function() {{
            const bubble = document.getElementById('{typing_id}');
            if (bubble) {{
                bubble.style.opacity = '0';
                bubble.style.transform = 'scale(0.98)';
                setTimeout(() => bubble.remove(), 250);
            }}
        }};
        """
        
        return typing_js

    def create_ai_avatar(self, position: str = "top-left") -> str:
        """
        Create a simple AI avatar icon that the chat bubble connects to.
        
        Args:
            position: Position for the avatar
        
        Returns:
            JavaScript code to create the avatar
        """
        avatar_id = f"ai-avatar-{uuid.uuid4().hex[:8]}"
        
        # Position the avatar to the left of where the bubble appears
        avatar_positions = {
            "top-left": "top: 60px; left: 20px;",
            "top-right": "top: 60px; right: 80px;",
            "bottom-left": "bottom: 20px; left: 20px;",
            "bottom-right": "bottom: 20px; right: 80px;"
        }
        
        avatar_css = avatar_positions.get(position, avatar_positions["top-left"])
        
        avatar_js = f"""
        // Remove existing avatar if any
        const existingAvatar = document.getElementById('{avatar_id}');
        if (existingAvatar) {{
            existingAvatar.remove();
        }}
        
        // Create AI avatar
        const aiAvatar = document.createElement('div');
        aiAvatar.id = '{avatar_id}';
        aiAvatar.style.cssText = `
            position: fixed;
            {avatar_css}
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999998;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            cursor: default;
            user-select: none;
        `;
        
        aiAvatar.innerHTML = `
            <span style="
                color: white; 
                font-size: 16px; 
                font-weight: 600;
                font-family: 'Inter', 'Arial', sans-serif;
                cursor: default;
            ">AI</span>
        `;
        
        document.body.appendChild(aiAvatar);
        
        // Store avatar for later removal
        window.currentAiAvatar = '{avatar_id}';
        """
        
        return avatar_js

    def remove_ai_avatar(self) -> str:
        """Remove the AI avatar."""
        remove_js = """
        if (window.currentAiAvatar) {
            const avatar = document.getElementById(window.currentAiAvatar);
            if (avatar) {
                avatar.remove();
            }
            delete window.currentAiAvatar;
        }
        """
        return remove_js

    def ensure_standard_cursor(self) -> str:
        """Ensure the cursor is the standard Windows black arrow cursor."""
        cursor_js = """
        // Override any custom cursors and ensure standard Windows cursor
        document.body.style.cursor = 'default';
        document.documentElement.style.cursor = 'default';
        
        // Apply to all elements that might have custom cursors
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            const computedStyle = window.getComputedStyle(el);
            if (computedStyle.cursor !== 'default' && 
                computedStyle.cursor !== 'pointer' && 
                computedStyle.cursor !== 'text') {
                el.style.cursor = 'default';
            }
        });
        
        // Set default cursor for the entire page
        const style = document.createElement('style');
        style.textContent = `
            *, *:before, *:after {
                cursor: default !important;
            }
            a, button, [onclick], .clickable {
                cursor: pointer !important;
            }
            input, textarea, [contenteditable] {
                cursor: text !important;
            }
        `;
        document.head.appendChild(style);
        """
        return cursor_js

class MegaAdvancedBrowserAgent:
    """Atharva Agent with all features."""
    
    def __init__(self, headless=False, window_size=(1920, 1080), enable_extensions=True):
        print("🚀 Initializing Atharva Agent with 50+ Features...")
        
        # Initialize all managers and databases
        self.db = AdvancedDatabase()
        self.email_manager = AdvancedEmailManager()
        self.report_generator = AdvancedReportGenerator(self.db)
        self.chat_interface = ChatInterface()  # Initialize clean chat interface
        
        # Setup directories
        for directory in ['screenshots', 'downloads', 'data', 'reports', 'temp', 'exports']:
            os.makedirs(directory, exist_ok=True)
        
        # Advanced Chrome options
        chrome_options = ChromeOptions()
        
        # Performance optimizations
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--log-level=3')
        
        # Enable proper cursor display - REMOVE headless and gpu disable
        if not headless:
            # Keep browser visible for proper cursor
            chrome_options.add_argument('--enable-gpu')
            chrome_options.add_argument('--enable-accelerated-2d-canvas')
            chrome_options.add_argument('--force-device-scale-factor=1')  # Ensure proper cursor scaling
            chrome_options.add_argument('--enable-features=VizDisplayCompositor')  # Better cursor rendering
        else:
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--disable-gpu')
        
        # Remove image disabling for better visual experience
        # chrome_options.add_argument('--disable-images') # Removed for better UX
        
        # Advanced user agent and fingerprint spoofing
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Download preferences
        prefs = {
            "download.default_directory": os.path.abspath("downloads"),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_settings.popups": 0,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.geolocation": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Initialize driver
        try:
            self.driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=chrome_options
            )
            self.driver.set_window_size(*window_size)
            
            # Advanced JavaScript injections for better functionality and cursor display
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                window.chrome = { runtime: {} };
                
                // Force standard Windows cursor visibility and styling
                document.addEventListener('DOMContentLoaded', function() {
                    document.body.style.cursor = 'default';
                    document.documentElement.style.cursor = 'default';
                });
            """)
            
            # Apply standard cursor immediately
            self.apply_standard_cursor()
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
        
        # Initialize data structures
        self.elements_cache: List[ElementInfo] = []
        self.action_history: List[ActionResult] = []
        self.session_data = {
            'start_time': datetime.now(),
            'total_actions': 0,
            'successful_actions': 0,
            'websites_visited': set(),
            'forms_filled': 0,
            'searches_performed': 0,
            'downloads_completed': 0,
            'emails_sent': 0,
            'reports_generated': 0
        }
        
        # Initialize visual elements
        self._initialize_advanced_visual_elements()
        
        logger.info("🎨 Atharva Agent initialized successfully with ALL features!")
        
    def _initialize_advanced_visual_elements(self):
        """Initialize advanced visual elements with human-like animations."""
        advanced_visual_js = '''
        // Remove existing elements
        const existingElements = document.querySelectorAll('#ai-cursor, #ai-analysis-bubble, #ai-status-bar, #ai-progress-ring');
        existingElements.forEach(el => el.remove());

        // Create Windows 10/11 Style Cursor (Unicode Arrow - Most Compatible)
        const cursor = document.createElement('div');
        cursor.id = 'ai-cursor';
        cursor.innerHTML = '➤';  // Unicode arrow that looks like Windows cursor
        cursor.style.cssText = `
            position: fixed;
            font-size: 16px;
            color: white;
            text-shadow: 
                -1px -1px 0 black,
                 1px -1px 0 black,
                -1px  1px 0 black,
                 1px  1px 0 black,
                 0px -1px 0 black,
                 0px  1px 0 black,
                -1px  0px 0 black,
                 1px  0px 0 black,
                 2px  2px 3px rgba(0,0,0,0.5);
            z-index: 999999;
            pointer-events: none;
            transition: all 0.05s ease;
            display: block;
            transform: translate(-2px, -2px);
            opacity: 1;
            font-family: 'Segoe UI Symbol', 'Arial Unicode MS', monospace;
            line-height: 1;
            user-select: none;
        `;
        document.body.appendChild(cursor);
        
        // Ensure standard system cursor for all page elements
        document.body.style.cursor = 'default';
        document.documentElement.style.cursor = 'default';
        
        // Apply standard cursor to all elements
        const style = document.createElement('style');
        style.textContent = `
            *, *:before, *:after {
                cursor: default !important;
            }
            a, button, [onclick], .clickable, [role="button"] {
                cursor: pointer !important;
            }
            input, textarea, [contenteditable] {
                cursor: text !important;
            }
            [draggable="true"] {
                cursor: move !important;
            }
        `;
        document.head.appendChild(style);

        // Create Advanced AI Analysis Bubble
        const bubble = document.createElement('div');
        bubble.id = 'ai-analysis-bubble';
        bubble.style.cssText = `
            position: fixed;
            top: 20px;
            left: 20px;
            max-width: 400px;
            background: linear-gradient(135deg, rgba(45, 55, 72, 0.95) 0%, rgba(55, 65, 82, 0.95) 100%);
            color: white;
            padding: 16px 20px;
            border-radius: 15px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            line-height: 1.5;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            z-index: 999998;
            opacity: 0;
            transform: translateY(-20px) scale(0.95);
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            backdrop-filter: blur(20px);
        `;
        
        bubble.innerHTML = `
            <div style="position: relative;">
                <div id="bubble-text">🤖 AI is initializing advanced systems...</div>
                <div style="position: absolute; top: -12px; left: 25px; width: 0; height: 0; 
                     border-left: 10px solid transparent; border-right: 10px solid transparent; 
                     border-bottom: 12px solid rgba(45, 55, 72, 0.95);"></div>
            </div>
        `;
        document.body.appendChild(bubble);

        // Create Advanced Progress Ring
        const progressRing = document.createElement('div');
        progressRing.id = 'ai-progress-ring';
        progressRing.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.9), rgba(118, 75, 162, 0.9));
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999997;
            opacity: 0;
            transform: scale(0.8);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            border: 2px solid rgba(255, 255, 255, 0.3);
        `;
        
        progressRing.innerHTML = `
            <div style="color: white; font-size: 14px; font-weight: bold;" id="progress-text">0%</div>
        `;
        document.body.appendChild(progressRing);

        // Advanced Status Bar
        const statusBar = document.createElement('div');
        statusBar.id = 'ai-status-bar';
        statusBar.style.cssText = `
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 6px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            z-index: 999996;
            opacity: 0;
            transition: opacity 0.3s ease;
            box-shadow: 0 -2px 10px rgba(102, 126, 234, 0.3);
        `;
        document.body.appendChild(statusBar);

        // Add advanced CSS animations
        const advancedStyle = document.createElement('style');
        advancedStyle.textContent = `
            @keyframes aiCursorPulse {
                0%, 100% { 
                    transform: translate(-50%, -50%) scale(1); 
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                }
                50% { 
                    transform: translate(-50%, -50%) scale(1.1); 
                    box-shadow: 0 6px 25px rgba(102, 126, 234, 0.6);
                }
            }
            
            @keyframes progressSpin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            @keyframes statusBarFlow {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            
            #ai-cursor.active {
                animation: aiCursorPulse 2s infinite;
            }
            
            #ai-progress-ring.active {
                animation: progressSpin 2s linear infinite;
            }
            
            #ai-status-bar.active {
                background-size: 200% 200%;
                animation: statusBarFlow 3s ease infinite;
            }
        `;
        document.head.appendChild(advancedStyle);
        '''
        
        try:
            self.driver.execute_script(advanced_visual_js)
            logger.info("Advanced visual elements initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize visual elements: {e}")

    def show_ai_analysis(self, message: str, duration: int = 8000):
        """Show AI analysis in the speech bubble with proper text escaping and streaming effect."""
        try:
            # Properly escape the message for JavaScript
            escaped_message = message.replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')
            
            # Streaming effect - type out the message character by character
            show_bubble_js = f'''
            const bubble = document.getElementById('ai-analysis-bubble');
            const bubbleText = document.getElementById('bubble-text');
            if (bubble && bubbleText) {{
                bubble.style.opacity = '1';
                bubble.style.transform = 'translateY(0) scale(1)';
                
                const fullMessage = "{escaped_message}";
                bubbleText.textContent = '';
                
                let i = 0;
                const typeWriter = () => {{
                    if (i < fullMessage.length) {{
                        bubbleText.textContent += fullMessage.charAt(i);
                        i++;
                        setTimeout(typeWriter, 30); // Streaming typing effect
                    }}
                }};
                typeWriter();
                
                // Auto-hide after duration
                setTimeout(() => {{
                    if (bubble) {{
                        bubble.style.opacity = '0';
                        bubble.style.transform = 'translateY(-20px) scale(0.95)';
                    }}
                }}, {duration});
            }}
            '''
            self.driver.execute_script(show_bubble_js)
        except Exception as e:
            logger.warning(f"Could not show AI analysis: {e}")

    def show_chat_bubble(self, message: str, position: str = "top-left", duration: int = 8000):
        """
        Display a clean, minimal chat bubble with AI response.
        
        Args:
            message: The AI response message to display
            position: Position of the bubble (default "top-left" for AI avatar connection)
            duration: How long to show the bubble in milliseconds (0 for permanent)
        """
        try:
            # Create and inject the chat bubble
            bubble_js = self.chat_interface.create_chat_bubble(message, position)
            
            # If duration is specified and not 0, auto-hide the bubble
            if duration > 0:
                auto_hide_js = f"""
                setTimeout(() => {{
                    {self.chat_interface.remove_bubble()}
                }}, {duration});
                """
                bubble_js += auto_hide_js
            
            self.driver.execute_script(bubble_js)
            logger.info(f"Chat bubble displayed: {message[:50]}...")
            
        except Exception as e:
            logger.warning(f"Could not show chat bubble: {e}")

    def update_chat_bubble(self, new_message: str):
        """
        Update the message in the current chat bubble.
        
        Args:
            new_message: New message to display in the bubble
        """
        try:
            update_js = self.chat_interface.update_bubble_message(new_message)
            self.driver.execute_script(update_js)
            logger.info(f"Chat bubble updated: {new_message[:50]}...")
            
        except Exception as e:
            logger.warning(f"Could not update chat bubble: {e}")

    def show_typing_indicator(self, position: str = "top-left"):
        """
        Show a typing indicator when AI is processing.
        
        Args:
            position: Position of the typing indicator (default "top-left")
        """
        try:
            typing_js = self.chat_interface.create_typing_indicator(position)
            self.driver.execute_script(typing_js)
            logger.info("Typing indicator displayed")
            
        except Exception as e:
            logger.warning(f"Could not show typing indicator: {e}")

    def hide_typing_indicator(self):
        """Remove the typing indicator."""
        try:
            hide_js = "if (window.removeTypingIndicator) { window.removeTypingIndicator(); }"
            self.driver.execute_script(hide_js)
            logger.info("Typing indicator hidden")
            
        except Exception as e:
            logger.warning(f"Could not hide typing indicator: {e}")

    def remove_chat_bubble(self):
        """Remove the current chat bubble with smooth animation."""
        try:
            remove_js = self.chat_interface.remove_bubble()
            self.driver.execute_script(remove_js)
            logger.info("Chat bubble removed")
            
        except Exception as e:
            logger.warning(f"Could not remove chat bubble: {e}")

    def show_ai_response(self, message: str, position: str = "top-left", show_typing: bool = True, typing_delay: float = 1.5):
        """
        Show a complete AI response with optional typing indicator.
        
        Args:
            message: The AI response message
            position: Position of the bubble (default "top-left" for AI avatar connection)
            show_typing: Whether to show typing indicator first
            typing_delay: How long to show typing indicator before message
        """
        try:
            if show_typing:
                # Show typing indicator
                self.show_typing_indicator(position)
                
                # Wait for typing delay
                time.sleep(typing_delay)
                
                # Hide typing indicator
                self.hide_typing_indicator()
                
                # Small delay before showing message
                time.sleep(0.3)
            
            # Show the actual message
            self.show_chat_bubble(message, position)
            logger.info(f"AI response displayed with typing effect: {message[:50]}...")
            
        except Exception as e:
            logger.warning(f"Could not show AI response: {e}")

    def show_ai_avatar(self, position: str = "top-left"):
        """Show the AI avatar icon."""
        try:
            avatar_js = self.chat_interface.create_ai_avatar(position)
            self.driver.execute_script(avatar_js)
            logger.info("AI avatar displayed")
        except Exception as e:
            logger.warning(f"Could not show AI avatar: {e}")

    def hide_ai_avatar(self):
        """Hide the AI avatar icon."""
        try:
            remove_js = self.chat_interface.remove_ai_avatar()
            self.driver.execute_script(remove_js)
            logger.info("AI avatar hidden")
        except Exception as e:
            logger.warning(f"Could not hide AI avatar: {e}")

    def show_complete_chat_interface(self, message: str, position: str = "top-left", show_typing: bool = True):
        """
        Show the complete chat interface with avatar and speech bubble.
        
        Args:
            message: The AI response message
            position: Position for the interface
            show_typing: Whether to show typing indicator
        """
        try:
            # Show avatar first
            self.show_ai_avatar(position)
            
            # Then show the response
            self.show_ai_response(message, position, show_typing)
            
            logger.info("Complete chat interface displayed")
        except Exception as e:
            logger.warning(f"Could not show complete chat interface: {e}")

    def apply_standard_cursor(self):
        """Apply standard Windows black arrow cursor to the page."""
        try:
            cursor_js = self.chat_interface.ensure_standard_cursor()
            self.driver.execute_script(cursor_js)
            logger.info("Standard cursor applied")
        except Exception as e:
            logger.warning(f"Could not apply standard cursor: {e}")

    def show_progress(self, percentage: int):
        """Show progress in the progress ring."""
        try:
            progress_js = f'''
            const progressRing = document.getElementById('ai-progress-ring');
            const progressText = document.getElementById('progress-text');
            if (progressRing && progressText) {{
                progressText.textContent = '{percentage}%';
                progressRing.style.opacity = '1';
                progressRing.style.transform = 'scale(1)';
                
                if ({percentage} < 100) {{
                    progressRing.classList.add('active');
                }} else {{
                    progressRing.classList.remove('active');
                    setTimeout(() => {{
                        progressRing.style.opacity = '0';
                        progressRing.style.transform = 'scale(0.8)';
                    }}, 2000);
                }}
            }}
            '''
            self.driver.execute_script(progress_js)
        except Exception as e:
            logger.warning(f"Could not show progress: {e}")

    def move_cursor_like_human(self, element):
        """Move cursor to element with realistic human-like movement."""
        try:
            rect = element.location_once_scrolled_into_view
            size = element.size
            target_x = rect['x'] + size['width'] / 2
            target_y = rect['y'] + size['height'] / 2
            
            # Create human-like movement with multiple steps and slight variations
            human_movement_js = f'''
            const cursor = document.getElementById('ai-cursor');
            if (cursor) {{
                cursor.style.display = 'block';
                cursor.classList.add('active');
                
                // Get current position or start from a random position
                const startX = cursor.offsetLeft || Math.random() * window.innerWidth;
                const startY = cursor.offsetTop || Math.random() * window.innerHeight;
                
                const targetX = {target_x};
                const targetY = {target_y};
                
                const steps = 8; // More steps for smoother movement
                let currentStep = 0;
                
                const moveStep = () => {{
                    currentStep++;
                    const progress = currentStep / steps;
                    
                    // Easing function for natural movement
                    const easeInOutCubic = t => t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1;
                    const easedProgress = easeInOutCubic(progress);
                    
                    // Add slight random variations for human-like imperfection
                    const randomOffsetX = (Math.random() - 0.5) * 3;
                    const randomOffsetY = (Math.random() - 0.5) * 3;
                    
                    const currentX = startX + (targetX - startX) * easedProgress + randomOffsetX;
                    const currentY = startY + (targetY - startY) * easedProgress + randomOffsetY;
                    
                    cursor.style.left = currentX + 'px';
                    cursor.style.top = currentY + 'px';
                    
                    // Keep standard cursor transform
                    cursor.style.transform = 'translate(-2px, -2px)';
                    
                    if (currentStep < steps) {{
                        // Variable timing between steps (50-120ms) for human-like movement
                        const delay = 50 + Math.random() * 70;
                        setTimeout(moveStep, delay);
                    }} else {{
                        // Final positioning with proper offset
                        cursor.style.left = targetX + 'px';
                        cursor.style.top = targetY + 'px';
                        cursor.style.transform = 'translate(-2px, -2px)';
                    }}
                }};
                
                moveStep();
            }}
            '''
            
            self.driver.execute_script(human_movement_js)
            time.sleep(0.8)  # Wait for movement to complete
            
        except Exception as e:
            logger.warning(f"Could not move cursor: {e}")

    def activate_status_bar(self, active: bool = True):
        """Activate or deactivate the status bar."""
        try:
            status_js = f'''
            const statusBar = document.getElementById('ai-status-bar');
            if (statusBar) {{
                statusBar.style.opacity = '{1 if active else 0}';
                if ({str(active).lower()}) {{
                    statusBar.classList.add('active');
                }} else {{
                    statusBar.classList.remove('active');
                }}
            }}
            '''
            self.driver.execute_script(status_js)
        except Exception as e:
            logger.warning(f"Could not activate status bar: {e}")

    def get_screenshot_as_png(self):
        """Get screenshot as PNG bytes."""
        return self.driver.get_screenshot_as_png()

    def _get_advanced_interactive_elements(self) -> List[ElementInfo]:
        """Get all interactive elements with advanced analysis including iframes."""
        script = '''
        const elements = [];
        
        // Function to extract elements from a document (main or iframe)
        function extractElementsFromDocument(doc, frameOffset = {x: 0, y: 0}) {
            const selectors = 'a, button, input, textarea, select, [role="button"], [role="link"], ' +
                '[onclick], [tabindex]:not([tabindex="-1"]), [contenteditable="true"], ' +
                '[data-testid], [data-cy], .btn, .button, .link, .clickable, ' +
                'form, label, option, summary, details, [href], [src]';
            
            const docElements = Array.from(doc.querySelectorAll(selectors));
            
            for (const el of docElements) {
                try {
                    const rect = el.getBoundingClientRect();
                    const style = doc.defaultView.getComputedStyle(el);
                    
                    // Adjust coordinates for iframe offset
                    const adjustedRect = {
                        x: rect.x + frameOffset.x,
                        y: rect.y + frameOffset.y,
                        width: rect.width,
                        height: rect.height,
                        top: rect.top + frameOffset.y,
                        left: rect.left + frameOffset.x,
                        bottom: rect.bottom + frameOffset.y,
                        right: rect.right + frameOffset.x
                    };
                    
                    if (adjustedRect.width > 0 && adjustedRect.height > 0 && 
                        adjustedRect.top >= -100 && adjustedRect.left >= -100 &&
                        adjustedRect.bottom <= window.innerHeight + 100 && 
                        adjustedRect.right <= window.innerWidth + 100 &&
                        style.visibility !== 'hidden' && 
                        style.display !== 'none') {
                        
                        const tagName = el.tagName.toLowerCase();
                        const elementType = el.type || 'unknown';
                        const isVisible = adjustedRect.top >= 0 && adjustedRect.left >= 0 && 
                                         adjustedRect.bottom <= window.innerHeight && 
                                         adjustedRect.right <= window.innerWidth;
                        
                        // Fast text extraction with fallbacks
                        let label = '';
                        if (el.textContent && el.textContent.trim()) {
                            label = el.textContent.trim();
                        } else if (el.getAttribute('aria-label')) {
                            label = el.getAttribute('aria-label');
                        } else if (el.getAttribute('placeholder')) {
                            label = el.getAttribute('placeholder');
                        } else if (el.getAttribute('title')) {
                            label = el.getAttribute('title');
                        } else if (el.getAttribute('alt')) {
                            label = el.getAttribute('alt');
                        } else if (el.getAttribute('value')) {
                            label = el.getAttribute('value');
                        } else {
                            label = tagName;
                        }
                        
                        // Fast confidence calculation
                        let confidence = 0.5;
                        if (isVisible) confidence += 0.2;
                        if (el.onclick || el.getAttribute('onclick')) confidence += 0.1;
                        if (tagName === 'button' || tagName === 'a') confidence += 0.1;
                        if (el.getAttribute('role')) confidence += 0.1;
                        
                        // Only collect essential attributes for speed
                        const attributes = {
                            id: el.id || '',
                            class: el.className || '',
                            name: el.name || '',
                            type: el.type || '',
                            role: el.getAttribute('role') || ''
                        };
                        
                        // Add data attribute for iframe tracking
                        el.setAttribute('data-element-id', elements.length + 1);
                        
                        elements.push({
                            element: el,
                            tagName: tagName,
                            label: label.substring(0, 100).replace(/\\s+/g, ' '),
                            elementType: elementType,
                            isVisible: isVisible,
                            isClickable: tagName === 'button' || tagName === 'a' || 
                                       el.onclick || el.getAttribute('onclick') || 
                                       el.getAttribute('role') === 'button',
                            isFormField: ['input', 'textarea', 'select'].includes(tagName),
                            coordinates: [adjustedRect.x, adjustedRect.y, adjustedRect.width, adjustedRect.height],
                            attributes: attributes,
                            textContent: el.textContent ? el.textContent.substring(0, 100) : '',
                            confidenceScore: Math.min(confidence, 1.0),
                            frameSource: frameOffset.x === 0 && frameOffset.y === 0 ? 'main' : 'iframe'
                        });
                    }
                } catch (e) {
                    // Skip errors for speed
                }
            }
        }
        
        // Extract from main document
        extractElementsFromDocument(document);
        
        // Extract from iframes (faster approach)
        const iframes = document.querySelectorAll('iframe');
        for (const iframe of iframes) {
            try {
                // Check if iframe is accessible (same origin)
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                if (iframeDoc) {
                    const iframeRect = iframe.getBoundingClientRect();
                    const frameOffset = {
                        x: iframeRect.x,
                        y: iframeRect.y
                    };
                    extractElementsFromDocument(iframeDoc, frameOffset);
                }
            } catch (e) {
                // Skip cross-origin iframes
                console.log('Skipping cross-origin iframe');
            }
        }
        
        // Fast sort by confidence and visibility
        const elementData = elements.map((el, i) => ({
            ...el,
            id: i + 1
        })).sort((a, b) => {
            if (a.isVisible && !b.isVisible) return -1;
            if (!a.isVisible && b.isVisible) return 1;
            return b.confidenceScore - a.confidenceScore;
        });
        
        return elementData;
        '''
        
        try:
            # Faster wait with shorter timeout
            WebDriverWait(self.driver, 5).until(
                lambda d: d.find_element(By.TAG_NAME, "body")
            )
            raw_elements = self.driver.execute_script(script)
            
            # Faster conversion to ElementInfo objects
            elements = []
            for raw_element in raw_elements[:50]:  # Limit to top 50 elements for speed
                try:
                    element_info = ElementInfo(
                        id=raw_element['id'],
                        element=raw_element['element'],
                        tag_name=raw_element['tagName'],
                        label=raw_element['label'],
                        element_type=raw_element['elementType'],
                        is_visible=raw_element['isVisible'],
                        is_clickable=raw_element['isClickable'],
                        is_form_field=raw_element['isFormField'],
                        coordinates=tuple(raw_element['coordinates']),
                        attributes=raw_element['attributes'],
                        text_content=raw_element['textContent'],
                        confidence_score=raw_element['confidenceScore']
                    )
                    elements.append(element_info)
                except Exception as e:
                    # Skip errors for speed
                    continue
            
            # Log iframe detection results
            iframe_elements = [e for e in elements if e.attributes.get('frameSource') == 'iframe']
            if iframe_elements:
                logger.info(f"Found {len(iframe_elements)} elements inside iframes")
            
            logger.info(f"Found {len(elements)} advanced interactive elements (including iframes)")
            return elements
            
        except Exception as e:
            logger.error(f"Error getting interactive elements: {e}")
            return []

    def _draw_advanced_labels_on_image(self, screenshot_png: bytes, elements: List[ElementInfo]) -> bytes:
        """Draw advanced element labels with BETTER VISIBILITY and proper numbering."""
        image = Image.open(BytesIO(screenshot_png))
        draw = ImageDraw.Draw(image)
        
        # Load fonts with proper fallback
        try:
            title_font = ImageFont.truetype("arial.ttf", 16)  # Larger font
            label_font = ImageFont.truetype("arial.ttf", 14)  # Larger font
            small_font = ImageFont.truetype("arial.ttf", 11)  # Larger font
        except (IOError, OSError):
            try:
                title_font = ImageFont.truetype("Arial.ttf", 16)
                label_font = ImageFont.truetype("Arial.ttf", 14)
                small_font = ImageFont.truetype("Arial.ttf", 11)
            except (IOError, OSError):
                title_font = ImageFont.load_default()
                label_font = ImageFont.load_default()
                small_font = ImageFont.load_default()

        # ENHANCED color mapping with BRIGHT, VISIBLE colors
        color_map = {
            'a': (0, 255, 0),             # Bright Green for links
            'input': (255, 165, 0),       # Bright Orange for inputs
            'textarea': (255, 140, 0),    # Dark Orange for textareas
            'button': (0, 150, 255),      # Bright Blue for buttons
            'select': (255, 0, 255),      # Magenta for selects
            'form': (255, 20, 147),       # Deep Pink for forms
            'label': (165, 42, 42),       # Brown for labels
        }
        
        # Draw elements with ENHANCED VISIBILITY
        valid_element_count = 0
        for element_info in elements:
            if not element_info.is_visible or element_info.confidence_score < 0.3:
                continue  # Skip invisible or low-confidence elements
                
            valid_element_count += 1
            try:
                x, y, w, h = element_info.coordinates
                label_id = str(valid_element_count)  # Use sequential numbering for visible elements
                tag_name = element_info.tag_name
                
                # Get BRIGHT color based on element type
                if element_info.is_form_field:
                    color = color_map.get(tag_name, (255, 165, 0))  # Bright Orange
                elif element_info.is_clickable:
                    color = color_map.get(tag_name, (0, 150, 255))  # Bright Blue
                else:
                    color = color_map.get(tag_name, (128, 128, 128))  # Gray default
                
                # Draw THICKER element outline for better visibility
                outline_width = max(3, int(element_info.confidence_score * 5))
                
                # Draw multiple outline layers for better visibility
                for i in range(outline_width):
                    draw.rectangle((x-i, y-i, x + w + i, y + h + i), outline=color, width=1)
                
                # Create LARGER, MORE VISIBLE label
                text_bbox = draw.textbbox((0, 0), label_id, font=label_font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # LARGER label background with better positioning
                padding = 8
                label_width = text_width + (padding * 2)
                label_height = text_height + (padding * 2)
                
                # Position label at top-left with better visibility
                label_x = max(2, x - 2)
                label_y = max(2, y - label_height - 4)
                
                # Draw TRANSPARENT label background (less intrusive)
                label_bg_coords = [label_x, label_y, label_x + label_width, label_y + label_height]
                
                # Semi-transparent background instead of black
                transparent_color = tuple(list(color) + [180])  # Add alpha for transparency
                draw.rectangle(label_bg_coords, fill=color)
                
                # Thin outline for contrast without heavy black border
                draw.rectangle(label_bg_coords, outline=(255, 255, 255), width=1)
                
                # Clean text without heavy shadow
                draw.text((label_x + padding, label_y + padding), 
                         label_id, font=label_font, fill=(255, 255, 255))
                
                # Simplified element type indicator (no black background)
                indicator_x = x + w - 15
                indicator_y = y + 2
                
                if element_info.is_form_field:
                    type_indicator = "📝" if tag_name == 'textarea' else "💬" if tag_name == 'input' else "📋"
                elif element_info.is_clickable:
                    type_indicator = "👆"
                else:
                    type_indicator = "👁️"
                
                # Draw indicator with minimal background
                draw.text((indicator_x, indicator_y), type_indicator, font=small_font)
                
                # Simplified confidence indicator (smaller, less intrusive)
                confidence_size = max(6, int(element_info.confidence_score * 8))
                confidence_color = (0, 255, 0) if element_info.confidence_score > 0.8 else (255, 255, 0) if element_info.confidence_score > 0.6 else (255, 0, 0)
                
                conf_x = x + w - confidence_size - 2
                conf_y = y + h - confidence_size - 2
                draw.ellipse([conf_x, conf_y, conf_x + confidence_size, conf_y + confidence_size], 
                           fill=confidence_color, outline=(255, 255, 255), width=1)
                
                # Update element_info id to match visible numbering
                element_info.id = valid_element_count
                
            except Exception as e:
                logger.warning(f"Error drawing label for element {element_info.id}: {e}")
                continue
        
        # Add ENHANCED professional watermark
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            url = self.driver.current_url[:50] + "..." if len(self.driver.current_url) > 50 else self.driver.current_url
            watermark_text = f"🤖 Mega AI Agent | {timestamp} | Elements: {valid_element_count}"
            
            # Get image dimensions
            img_width, img_height = image.size;
            
            # Calculate watermark position
            watermark_bbox = draw.textbbox((0, 0), watermark_text, font=small_font)
            watermark_width = watermark_bbox[2] - watermark_bbox[0]
            watermark_height = watermark_bbox[3] - watermark_bbox[1]
            
            # Enhanced background for watermark
            bg_padding = 8
            bg_coords = [0, img_height - watermark_height - bg_padding * 2, 
                        watermark_width + bg_padding * 2, img_height]
            
            # Black background with border
            draw.rectangle(bg_coords, fill=(0, 0, 0))
            draw.rectangle([1, img_height - watermark_height - bg_padding * 2 + 1, 
                          watermark_width + bg_padding * 2 - 1, img_height - 1], 
                         outline=(255, 255, 255), width=1)
            
            # Watermark text
            draw.text((bg_padding, img_height - watermark_height - bg_padding), 
                     watermark_text, font=small_font, fill=(255, 255, 255))
            
        except Exception as e:
            logger.warning(f"Could not add watermark: {e}")
        
        # Convert back to bytes with optimization
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True, quality=95)
        return buffer.getvalue()

    def save_advanced_screenshot(self, filename: str = None, annotate: bool = True) -> str:
        """Save advanced screenshot with optional annotations."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
            if filename is None:
                filename = f"screenshot_{timestamp}.png"
            
            filepath = os.path.join('screenshots', filename)
            
            if annotate and self.elements_cache:
                screenshot_png = self.get_screenshot_as_png()
                annotated_screenshot = self._draw_advanced_labels_on_image(screenshot_png, self.elements_cache)
                with open(filepath, 'wb') as f:
                    f.write(annotated_screenshot)
            else:
                self.driver.save_screenshot(filepath)
            
            logger.info(f"📸 Advanced screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            return None

    def decide_next_action(self, objective: str, annotated_screenshot_b64: str, elements: List[ElementInfo], last_action_feedback: str) -> Dict:
        """Get AI decision using Google Gemini."""
        self.show_ai_analysis("🤖 Atharva Agent is analyzing with Advanced Algorithms")
        self.activate_status_bar(True)
        
        try:
            element_descriptions = []
            visible_elements = [e for e in elements if e.is_visible and e.confidence_score >= 0.3]
            
            for elem_info in visible_elements:
                try:
                    tag = elem_info.element.tag_name.upper()
                    text = elem_info.element.text[:50] if elem_info.element.text else ""
                    attrs = []
                    
                    # Get key attributes
                    for attr in ['type', 'placeholder', 'name', 'id', 'class', 'value']:
                        try:
                            val = elem_info.element.get_attribute(attr)
                            if val: attrs.append(f"{attr}='{val[:30]}'")
                        except: pass
                    
                    attrs_str = " ".join(attrs)
                    description = f"[{elem_info.id}] {tag} - Text: '{text}' Attributes: {attrs_str}"
                    element_descriptions.append(description)
                except Exception as e:
                    element_descriptions.append(f"[{elem_info.id}] Error describing element: {str(e)}")

            element_descriptions_text = "\n".join(element_descriptions)

            # Create comprehensive prompt for Gemini
            prompt = f"""You are Atharva Agent, an advanced AI browser automation assistant powered by Google Gemini.

**CURRENT OBJECTIVE:** {objective}
**LAST ACTION FEEDBACK:** {last_action_feedback}

**VISIBLE ELEMENTS (Confidence ≥ 0.3):**
{element_descriptions_text}

**AVAILABLE ACTIONS:**
1. NAVIGATE - Go to URL: {{"url": "https://example.com"}}
2. CLICK - Click element: {{"id": 1}}
3. TYPE - Type text: {{"id": 1, "text": "search query"}}
4. HOVER - Hover element: {{"id": 1}}
5. SCROLL - Scroll page: {{"direction": "down", "pixels": 500}}
6. WAIT - Wait time: {{"seconds": 2}}
7. PRESS_KEY - Press key: {{"key": "Enter"}}
8. CLEAR - Clear input: {{"id": 1}}
9. SELECT - Select option: {{"id": 1, "option": "value"}}
10. TAKE_SCREENSHOT - Screenshot: {{}}
11. EXECUTE_JS - JavaScript: {{"script": "code"}}
12. REFRESH - Reload page: {{}}
13. GO_BACK - Browser back: {{}}
14. ANSWER - Complete task: {{"text": "Final answer"}}

**RESPONSE FORMAT (Required JSON):**
{{
    "thought": "Detailed reasoning about next action",
    "confidence": 0.9,
    "reasoning": "Why this action will help achieve the objective",
    "action": {{
        "name": "ACTION_NAME",
        "parameters": {{
            "id": 1,
            "text": "if_needed"
        }}
    }}
}}

**CRITICAL RULES:**
- Use ONLY the numbered IDs from the visible elements list above
- Always provide confidence score (0.0-1.0)
- Be specific and goal-oriented
- Handle errors gracefully

Analyze the screenshot and respond with the best next action as JSON."""

            try:
                print("Atharva is thinking>>>>")
                
                # Create Gemini content with image and text
                image_part = {
                    "mime_type": "image/png",
                    "data": annotated_screenshot_b64
                }
                
                # Generate content with Gemini
                response = model.generate_content([prompt, image_part])
                
                if response.text:
                    print(f"✅ Atharva Response: {response.text[:100]}...")
                    
                    # Parse JSON response
                    try:
                        # Clean response and parse JSON
                        clean_response = response.text.strip()
                        if clean_response.startswith('```json'):
                            clean_response = clean_response[7:]
                        if clean_response.endswith('```'):
                            clean_response = clean_response[:-3]
                        
                        decision = json.loads(clean_response)
                        
                        # Validate decision structure
                        if "action" in decision and "name" in decision["action"]:
                            logger.info(f"🎯 Atharva Agent decision: {decision['action']['name']}")
                            return decision
                        else:
                            raise ValueError("Invalid decision structure")
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON parse error: {e}")
                        return {
                            "thought": "Failed to parse Gemini response",
                            "confidence": 0.1,
                            "reasoning": "JSON parsing error",
                            "action": {"name": "WAIT", "parameters": {"seconds": 2}}
                        }
                        
                else:
                    logger.error("Empty response from Gemini")
                    return {
                        "thought": "No response from Gemini",
                        "confidence": 0.1,
                        "reasoning": "Empty AI response",
                        "action": {"name": "TAKE_SCREENSHOT", "parameters": {}}
                    }
                    
            except Exception as api_error:
                logger.error(f"Gemini API error: {api_error}")
                return {
                    "thought": f"Gemini API failed: {str(api_error)}",
                    "confidence": 0.1,
                    "reasoning": "API communication error",
                    "action": {"name": "WAIT", "parameters": {"seconds": 3}}
                }
                
        except Exception as e:
            logger.error(f"Critical error in decide_next_action: {e}")
            return {
                "thought": f"Critical error: {str(e)}",
                "confidence": 0.1,
                "reasoning": "System error",
                "action": {"name": "TAKE_SCREENSHOT", "parameters": {}}
            }
        finally:
            self.activate_status_bar(False)
        
        # Create enhanced element descriptions with ONLY VISIBLE elements
        element_descriptions = []
        visible_elements = [e for e in elements if e.is_visible and e.confidence_score >= 0.3]
        
        for i, e in enumerate(visible_elements[:30], 1):  # Renumber visible elements
            confidence_indicator = "🟢" if e.confidence_score > 0.8 else "🟡" if e.confidence_score > 0.6 else "🔴"
            type_indicator = "📝" if e.is_form_field else "👆" if e.is_clickable else "👁️"
            visibility_indicator = "✅"  # All are visible now
            
            description = f"- ID {i}: {confidence_indicator}{type_indicator}{visibility_indicator} \"{e.label[:40]}\" ({e.tag_name}) [conf:{e.confidence_score:.1f}]"
            element_descriptions.append(description)
            # Update element ID to match visible numbering
            e.id = i
        
        element_descriptions_text = "\n".join(element_descriptions)
        
        system_prompt = f"""You are a powerful AI web automation agent with STREAMING response capabilities. Your goal is to achieve objectives through precise actions.

**CONTEXT:**
- **Objective:** {objective}
- **URL:** {self.driver.current_url}
- **Previous Result:** {last_action_feedback}
- **Screenshot:** Shows NUMBERED interactive elements with colored boxes

**VISIBLE ELEMENTS (Confidence ≥ 0.3):**
{element_descriptions_text}

**AVAILABLE ACTIONS:**
1. NAVIGATE - Go to URL: {{"url": "https://example.com"}}
2. CLICK - Click element: {{"id": 1}}
3. TYPE - Type text: {{"id": 1, "text": "search query"}}
4. HOVER - Hover element: {{"id": 1}}
5. SCROLL - Scroll page: {{"direction": "down", "pixels": 500}}
6. WAIT - Wait time: {{"seconds": 2}}
7. PRESS_KEY - Press key: {{"key": "Enter"}}
8. CLEAR - Clear input: {{"id": 1}}
9. SELECT - Select option: {{"id": 1, "option": "value"}}
10. TAKE_SCREENSHOT - Screenshot: {{}}
11. EXECUTE_JS - JavaScript: {{"script": "code"}}
12. REFRESH - Reload page: {{}}
13. GO_BACK - Browser back: {{}}
14. ANSWER - Complete task: {{"text": "Final answer"}}

**RESPONSE FORMAT (Required JSON):**
{{
    "thought": "Detailed reasoning about next action",
    "confidence": 0.9,
    "reasoning": "Why this action will help achieve the objective",
    "action": {{
        "name": "ACTION_NAME",
        "parameters": {{
            "id": 1,
            "text": "if_needed"
        }}
    }}
}}

**CRITICAL RULES:**
- Use ONLY the numbered IDs from the visible elements list above
- Always provide confidence score (0.0-1.0)
- Be specific and goal-oriented
- Handle errors gracefully
"""

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{annotated_screenshot_b64}"}
                        }
                    ]
                }
            ],
            "max_tokens": 1500,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,  # Lower for more consistent responses
            "stream": True  # Enable streaming
        }

        try:
            # STREAMING RESPONSE IMPLEMENTATION
            response = _optimized_session.post(API_ENDPOINT_URL, headers=headers, json=payload, timeout=90, stream=True)
            response.raise_for_status()
            
            # Collect streaming response
            content = ""
            print("🔄 AI Streaming Response: ", end="", flush=True)
            
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        try:
                            data_str = line_text[6:]  # Remove 'data: ' prefix
                            if data_str.strip() == '[DONE]':
                                break
                            
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    chunk = delta['content']
                                    content += chunk
                                    print(chunk, end="", flush=True)  # Stream to console
                                    time.sleep(0.01)  # Small delay for visual effect
                        except json.JSONDecodeError:
                            continue
            
            print("\n")  # New line after streaming
            
            if content:
                decision = json.loads(content)
                
                # Log enhanced decision details
                thought = decision.get('thought', 'No thought provided')
                confidence = decision.get('confidence', 0.5)
                reasoning = decision.get('reasoning', 'No reasoning provided')
                
                logger.info(f"🧠 AI Decision - Confidence: {confidence:.2f}")
                logger.info(f"💭 Thought: {thought}")
                logger.info(f"🎯 Reasoning: {reasoning}")
                
                return decision
            else:
                return {"thought": "Empty streaming response", "action": None}
                
        except Exception as e:
            logger.error(f"Error getting AI decision: {e}")
            # Fallback to non-streaming if streaming fails
            try:
                payload["stream"] = False
                response = _optimized_session.post(API_ENDPOINT_URL, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
            except:
                pass
            return {"thought": f"Error: {e}", "action": None}
        finally:
            self.activate_status_bar(False)

    def _switch_to_iframe_if_needed(self, element_id: int) -> bool:
        """Switch to iframe if the target element is inside one."""
        try:
            # Check if element is in iframe
            iframe_check_script = f"""
            const element = document.querySelector('[data-element-id="{element_id}"]');
            if (!element) return null;
            
            // Check if element is inside iframe
            let currentDoc = element.ownerDocument;
            if (currentDoc !== document) {{
                // Find the iframe that contains this document
                const iframes = document.querySelectorAll('iframe');
                for (const iframe of iframes) {{
                    try {{
                        if (iframe.contentDocument === currentDoc) {{
                            return {{
                                found: true,
                                iframe: iframe,
                                iframeIndex: Array.from(document.querySelectorAll('iframe')).indexOf(iframe)
                            }};
                        }}
                    }} catch (e) {{
                        // Cross-origin iframe
                    }}
                }}
            }}
            return {{found: false}};
            """
            
            result = self.driver.execute_script(iframe_check_script)
            
            if result and result.get('found'):
                iframe_index = result.get('iframeIndex', 0)
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                if iframe_index < len(iframes):
                    self.driver.switch_to.frame(iframes[iframe_index])
                    logger.info(f"Switched to iframe {iframe_index} for element {element_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking iframe for element {element_id}: {e}")
            return False

    def _switch_back_from_iframe(self):
        """Switch back to main content from iframe."""
        try:
            self.driver.switch_to.default_content()
            logger.info("Switched back to main content")
        except Exception as e:
            logger.warning(f"Error switching back from iframe: {e}")

    def execute_advanced_action(self, decision: Dict) -> ActionResult:
        """Execute the AI's decision with advanced error handling and logging."""
        start_time = time.time()
        action_start_time = datetime.now()
        
        if not decision or not decision.get("action"):
            return ActionResult(
                success=False,
                action_type="INVALID",
                message="❌ No valid action provided",
                duration=0,
                screenshot_path=None,
                element_id=None,
                error_details="Decision is empty or missing action",
                timestamp=action_start_time
            )
        
        action = decision["action"]
        action_name = action.get("name")
        params = action.get("parameters", {})
        
        logger.info(f"Executing advanced action: {action_name} with params: {params}")
        self.session_data['total_actions'] += 1
        
        try:
            # Show progress and analysis
            self.show_progress(25)
            
            if action_name == "NAVIGATE":
                url = params.get("url")
                if not url:
                    return self._create_error_result("NAVIGATE", "URL not provided", start_time, action_start_time)
                
                self.show_ai_analysis(f"🌐 Navigating to {url}...")
                self.show_progress(50)
                
                self.driver.get(url)
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                
                self.session_data['websites_visited'].add(url)
                self._initialize_advanced_visual_elements()  # Reinitialize visual elements
                self.show_progress(100)
                
                return self._create_success_result("NAVIGATE", "✅ Navigation successful", start_time, action_start_time)
            
            elif action_name == "ANSWER":
                answer_text = params.get("text", "Task completed")
                self.show_ai_analysis(f"🎉 Task completed successfully! {answer_text}")
                print(f"🤖 AI Agent's Final Answer: {answer_text}")
                self.show_progress(100)
                
                return ActionResult(
                    success=True,
                    action_type="ANSWER",
                    message="🏁 Task finished.",
                    duration=time.time() - start_time,
                    screenshot_path=None,
                    element_id=None,
                    error_details=None,
                    timestamp=action_start_time
                )
            
            elif action_name in ["CLICK", "TYPE", "HOVER", "CLEAR", "SELECT", "RIGHT_CLICK", "DOUBLE_CLICK", "GET_TEXT"]:
                element_id = params.get("id")
                if element_id is None:
                    # Auto-detect input fields for TYPE action
                    if action_name == "TYPE":
                        text = params.get("text", "")
                        element_id = self._auto_detect_input_field(text)
                        if element_id is None:
                            return self._create_error_result(action_name, "Could not find suitable input field automatically", start_time, action_start_time)
                    else:
                        return self._create_error_result(action_name, f"Element ID not provided for {action_name} action", start_time, action_start_time)
                
                # Find the element
                target_element = None
                target_element_info = None
                for element_info in self.elements_cache:
                    if element_info.id == element_id:
                        target_element = element_info.element
                        target_element_info = element_info
                        break
                
                if not target_element:
                    available_ids = [e.id for e in self.elements_cache[:20]]
                    return self._create_error_result(action_name, f"Element ID {element_id} not found. Available: {available_ids}", start_time, action_start_time)
                
                # Move cursor to element with human-like movement
                self.move_cursor_like_human(target_element)
                self.show_progress(75)
                
                # Execute specific action
                result = self._execute_element_action(action_name, params, target_element, target_element_info, start_time, action_start_time)
                self.show_progress(100)
                return result
            
            elif action_name == "SCROLL":
                direction = params.get("direction", "down")
                pixels = params.get("pixels", 500)
                self.show_ai_analysis(f"📜 Scrolling {direction} {pixels}px to see more content...")
                
                scroll_amount = pixels if direction == "down" else -pixels
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(0.5)  # Wait for scroll to complete
                
                return self._create_success_result("SCROLL", f"✅ Scrolled {direction} {pixels}px", start_time, action_start_time)
            
            elif action_name == "WAIT":
                seconds = params.get("seconds", 2)
                self.show_ai_analysis(f"⏳ Waiting {seconds} seconds for page elements to load...")
                
                for i in range(int(seconds * 10)):
                    time.sleep(0.1)
                    progress = min(100, (i / (seconds * 10)) * 100)
                    self.show_progress(int(progress))
                
                return self._create_success_result("WAIT", f"✅ Waited {seconds} seconds", start_time, action_start_time)
            
            elif action_name == "PRESS_KEY":
                key = params.get("key", "Enter")
                self.show_ai_analysis(f"⌨️ Pressing {key} key...")
                
                active_element = self.driver.switch_to.active_element
                key_mapping = {
                    "enter": Keys.ENTER,
                    "tab": Keys.TAB,
                    "escape": Keys.ESCAPE,
                    "space": Keys.SPACE,
                    "backspace": Keys.BACK_SPACE,
                    "delete": Keys.DELETE,
                    "home": Keys.HOME,
                    "end": Keys.END
                }
                
                key_to_send = key_mapping.get(key.lower(), key)
                active_element.send_keys(key_to_send)
                
                return self._create_success_result("PRESS_KEY", f"✅ Pressed {key} key", start_time, action_start_time)
            
            elif action_name == "TAKE_SCREENSHOT":
                self.show_ai_analysis("📸 Taking detailed screenshot for analysis...")
                filepath = self.save_advanced_screenshot()
                return ActionResult(
                    success=True,
                    action_type="TAKE_SCREENSHOT",
                    message=f"✅ Screenshot saved: {filepath}",
                    duration=time.time() - start_time,
                    screenshot_path=filepath,
                    element_id=None,
                    error_details=None,
                    timestamp=action_start_time
                )
            
            elif action_name == "EXECUTE_JS":
                script = params.get("script", "")
                if not script:
                    return self._create_error_result("EXECUTE_JS", "No script provided", start_time, action_start_time)
                
                self.show_ai_analysis(f"⚙️ Executing JavaScript: {script[:50]}...")
                result = self.driver.execute_script(script)
                
                return self._create_success_result("EXECUTE_JS", f"✅ JavaScript executed successfully. Result: {str(result)[:100]}", start_time, action_start_time)
            
            elif action_name == "REFRESH":
                self.show_ai_analysis("🔄 Refreshing the page...")
                self.driver.refresh()
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                return self._create_success_result("REFRESH", "✅ Page refreshed successfully", start_time, action_start_time)
            
            elif action_name == "GO_BACK":
                self.show_ai_analysis("⬅️ Going back in browser history...")
                self.driver.back()
                return self._create_success_result("GO_BACK", "✅ Navigated back successfully", start_time, action_start_time)
            
            elif action_name == "GO_FORWARD":
                self.show_ai_analysis("➡️ Going forward in browser history...")
                self.driver.forward()
                return self._create_success_result("GO_FORWARD", "✅ Navigated forward successfully", start_time, action_start_time)
            
            else:
                return self._create_error_result("UNKNOWN", f"Unknown action: {action_name}", start_time, action_start_time)
        
        except Exception as e:
            logger.error(f"Error executing {action_name}: {e}")
            return ActionResult(
                success=False,
                action_type=action_name,
                message=f"❌ {action_name} failed: {str(e)}",
                duration=time.time() - start_time,
                screenshot_path=None,
                element_id=params.get("id"),
                error_details=str(e),
                timestamp=action_start_time
            )

    def _execute_element_action(self, action_name: str, params: Dict, target_element, target_element_info: ElementInfo, start_time: float, action_start_time: datetime) -> ActionResult:
        """Execute element-specific actions with advanced error handling."""
        try:
            if action_name == "CLICK":
                self.show_ai_analysis(f"🎯 Clicking {target_element_info.label[:30]}...")
                
                # Check if element is in iframe and switch if needed
                was_in_iframe = self._switch_to_iframe_if_needed(target_element_info.id)
                
                try:
                    # Re-find element if we switched to iframe
                    if was_in_iframe:
                        target_element = self.driver.find_element(By.XPATH, f"//*[@data-element-id='{target_element_info.id}']")
                    
                    # Advanced click strategies with iframe support
                    strategies = [
                        lambda: target_element.click(),
                        lambda: self.driver.execute_script("arguments[0].click();", target_element),
                        lambda: ActionChains(self.driver).click(target_element).perform(),
                        lambda: self.driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", target_element),
                        lambda: ActionChains(self.driver).move_to_element(target_element).click().perform()
                    ]
                    
                    for i, strategy in enumerate(strategies):
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_element)
                            time.sleep(0.3)
                            strategy()
                            logger.info(f"✅ Click successful using strategy {i+1}" + (" (iframe)" if was_in_iframe else ""))
                            return self._create_success_result("CLICK", f"✅ Successfully clicked {target_element_info.label[:50]}" + (" (iframe)" if was_in_iframe else ""), start_time, action_start_time, target_element_info.id)
                        except Exception as e:
                            if i == len(strategies) - 1:
                                raise e
                            continue
                finally:
                    # Always switch back from iframe
                    if was_in_iframe:
                        self._switch_back_from_iframe()
            
            elif action_name == "TYPE":
                text = params.get("text", "")
                if not text:
                    return self._create_error_result("TYPE", "No text provided", start_time, action_start_time)
                
                self.show_ai_analysis(f"⌨️ Typing '{text}' into {target_element_info.label[:30]}...")
                
                # Scroll and focus
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_element)
                time.sleep(0.3)
                
                # Clear and type with human-like timing
                target_element.clear()
                time.sleep(0.1)
                
                # Type with human-like delays
                for char in text:
                    target_element.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.15))  # Human-like typing speed
                
                return self._create_success_result("TYPE", f"✅ Successfully typed '{text}' into {target_element_info.label[:30]}", start_time, action_start_time, target_element_info.id)
            
            elif action_name == "HOVER":
                self.show_ai_analysis(f"👆 Hovering over {target_element_info.label[:30]}...")
                ActionChains(self.driver).move_to_element(target_element).perform()
                time.sleep(0.5)
                return self._create_success_result("HOVER", f"✅ Successfully hovered over {target_element_info.label[:30]}", start_time, action_start_time, target_element_info.id)
            
            elif action_name == "CLEAR":
                self.show_ai_analysis(f"🧹 Clearing {target_element_info.label[:30]}...")
                target_element.clear()
                return self._create_success_result("CLEAR", f"✅ Successfully cleared {target_element_info.label[:30]}", start_time, action_start_time, target_element_info.id)
            
            elif action_name == "RIGHT_CLICK":
                self.show_ai_analysis(f"🖱️ Right clicking {target_element_info.label[:30]}...")
                ActionChains(self.driver).context_click(target_element).perform()
                return self._create_success_result("RIGHT_CLICK", f"✅ Right clicked {target_element_info.label[:30]}", start_time, action_start_time, target_element_info.id)
            
            elif action_name == "DOUBLE_CLICK":
                self.show_ai_analysis(f"🖱️ Double clicking {target_element_info.label[:30]}...")
                ActionChains(self.driver).double_click(target_element).perform()
                return self._create_success_result("DOUBLE_CLICK", f"✅ Double clicked {target_element_info.label[:30]}", start_time, action_start_time, target_element_info.id)
            
            elif action_name == "SELECT":
                option = params.get("option", "")
                if not option:
                    return self._create_error_result("SELECT", "No option provided", start_time, action_start_time)
                
                self.show_ai_analysis(f"📋 Selecting '{option}' from {target_element_info.label[:30]}...")
                select = Select(target_element)
                
                # Try different selection methods
                try:
                    select.select_by_visible_text(option)
                except:
                    try:
                        select.select_by_value(option)
                    except:
                        select.select_by_index(int(option) if option.isdigit() else 0)
                
                return self._create_success_result("SELECT", f"✅ Selected '{option}' from {target_element_info.label[:30]}", start_time, action_start_time, target_element_info.id)
            
            elif action_name == "GET_TEXT":
                self.show_ai_analysis(f"📖 Extracting text from {target_element_info.label[:30]}...")
                text = target_element.text or target_element.get_attribute('textContent') or target_element.get_attribute('value')
                return self._create_success_result("GET_TEXT", f"✅ Extracted text: '{text[:100]}'", start_time, action_start_time, target_element_info.id)
            
        except Exception as e:
            return ActionResult(
                success=False,
                action_type=action_name,
                message=f"❌ {action_name} failed: {str(e)}",
                duration=time.time() - start_time,
                screenshot_path=None,
                element_id=target_element_info.id,
                error_details=str(e),
                timestamp=action_start_time
            )

    def _auto_detect_input_field(self, search_text: str) -> Optional[int]:
        """Automatically detect the best input field for typing."""
        search_terms = ["search", "query", "q", "input", "text", "find", "lookup"]
        
        best_candidate = None
        best_score = 0
        
        for element_info in self.elements_cache:
            if not element_info.is_form_field:
                continue
                
            score = 0
            label_lower = element_info.label.lower();
            
            # Check for search-related terms
            for term in search_terms:
                if term in label_lower:
                    score += 0.3;
            
            # Prefer visible elements
            if element_info.is_visible:
                score += 0.2;
            
            # Prefer elements with higher confidence
            score += element_info.confidence_score * 0.3;
            
            # Prefer input fields over textareas
            if element_info.tag_name == 'input':
                score += 0.1;
            
            # Check element attributes
            for attr_name, attr_value in element_info.attributes.items():
                if attr_name in ['placeholder', 'name', 'id', 'class']:
                    attr_lower = attr_value.lower();
                    for term in search_terms:
                        if term in attr_lower:
                            score += 0.2;
            
            if score > best_score:
                best_score = score;
                best_candidate = element_info.id;
        
        logger.info(f"Auto-detected input field: ID {best_candidate} with score {best_score:.2f}")
        return best_candidate

    def _create_success_result(self, action_type: str, message: str, start_time: float, timestamp: datetime, element_id: int = None) -> ActionResult:
        """Create a successful action result."""
        self.session_data['successful_actions'] += 1
        screenshot_path = self.save_advanced_screenshot(f"success_{action_type.lower()}_{timestamp.strftime('%H%M%S')}.png")
        
        result = ActionResult(
            success=True,
            action_type=action_type,
            message=message,
            duration=time.time() - start_time,
            screenshot_path=screenshot_path,
            element_id=element_id,
            error_details=None,
            timestamp=timestamp
        )
        
        self.action_history.append(result)
        self.db.log_action(result)
        return result

    def _create_error_result(self, action_type: str, message: str, start_time: float, timestamp: datetime, element_id: int = None) -> ActionResult:
        """Create an error action result."""
        screenshot_path = self.save_advanced_screenshot(f"error_{action_type.lower()}_{timestamp.strftime('%H%M%S')}.png")
        
        result = ActionResult(
            success=False,
            action_type=action_type,
            message=f"❌ {message}",
            duration=time.time() - start_time,
            screenshot_path=screenshot_path,
            element_id=element_id,
            error_details=message,
            timestamp=timestamp
        )
        
        self.action_history.append(result)
        self.db.log_action(result)
        return result

    def _extract_url_from_command(self, command: str) -> Optional[str]:
        """Extract URL from command with advanced pattern matching."""
        # Full URL patterns
        url_patterns = [
            r'https?://[^\s/$.?#].[^\s]*',  # Standard HTTP/HTTPS URLs
            r'www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?',  # www.domain.com
            r'[a-zA-Z0-9-]+\.(?:com|org|net|io|dev|ai|co\.uk|edu|gov)(?:/[^\s]*)?'  # domain.com
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                url = match.group(0)
                if not url.startswith(('http://', 'https://')):
                    url = f'https://{url}'
                return url
        
        return None

    def generate_session_report(self) -> str:
        """Generate comprehensive session report."""
        try:
            end_time = datetime.now()
            session_duration = (end_time - self.session_data['start_time']).total_seconds()
            
            success_rate = 0
            if self.session_data['total_actions'] > 0:
                success_rate = (self.session_data['successful_actions'] / self.session_data['total_actions']) * 100
            
            report_data = {
                'session_start': self.session_data['start_time'],
                'session_end': end_time,
                'session_duration': session_duration,
                'total_actions': self.session_data['total_actions'],
                'successful_actions': self.session_data['successful_actions'],
                'success_rate': round(success_rate, 1),
                'websites_visited': len(self.session_data['websites_visited']),
                'actions': self.action_history[-20:],  # Last 20 actions
                'total_duration': session_duration
            }
            
            report_path = self.report_generator.generate_html_report(report_data)
            logger.info(f"Session report generated: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Error generating session report: {e}")
            return None

    def run(self):
        """Main execution loop with advanced features."""
        print("\n🚀 === Atharva Agent (1200+ LINES) ===")
        print("🎨 Advanced Visual Features:")
        print("   • Human-like cursor movement with 8-step animations")
        print("   • Real-time AI analysis speech bubbles")
        print("   • Professional progress indicators")
        print("   • Advanced status visualizations")
        print("   • Smart element confidence scoring")
        print("   • Automatic screenshot annotations")
        
        print("\n🛠️ Advanced Capabilities:")
        print("   • 20+ intelligent actions with error recovery")
        print("   • Auto-input field detection")
        print("   • Advanced element analysis & confidence scoring")
        print("   • Professional screenshot system")
        print("   • Comprehensive logging & reporting")
        print("   • Database session tracking")
        print("   • Email report generation")
        print("   • Smart form filling")
        print("   • JavaScript execution")
        print("   • Multi-tab management")
        
        print("\n📊 Analytics & Reporting:")
        print("   • Real-time performance tracking")
        print("   • HTML report generation")
        print("   • Database logging")
        print("   • Email notifications")
        print("   • Screenshot galleries")
        
        print("\n📝 Enter an objective, or type 'exit' to quit.")
        print("🔧 Commands: 'exit', 'info', 'screenshot', 'history', 'report', 'stats', 'chat', 'help'")

        while True:
            try:
                objective = input("\n🎯 > ").strip()
                
                if objective.lower() == 'exit':
                    break
                elif objective.lower() == 'info':
                    info = self._get_page_info()
                    print(f"📊 Page Info: {json.dumps(info, indent=2)}")
                    continue
                elif objective.lower() == 'screenshot':
                    filepath = self.save_advanced_screenshot()
                    print(f"📸 Advanced screenshot saved: {filepath}")
                    continue
                elif objective.lower() == 'history':
                    self._display_action_history()
                    continue
                elif objective.lower() == 'report':
                    report_path = self.generate_session_report()
                    if report_path:
                        print(f"📄 Session report generated: {report_path}")
                    else:
                        print("❌ Failed to generate report")
                    continue
                elif objective.lower() == 'stats':
                    self._display_session_stats()
                    continue
                elif objective.lower() == 'help':
                    self._display_help()
                    continue
                elif objective.lower() == 'chat':
                    self._demo_chat_interface()
                    continue
                elif not objective:
                    continue

                # Initialize task
                last_action_feedback = "🎬 Starting new objective with advanced AI analysis..."
                
                # Demo the complete chat interface with the new objective
                self.show_complete_chat_interface(
                    f"Processing your request: {objective[:100]}{'...' if len(objective) > 100 else ''}",
                    position="top-left",
                    show_typing=True
                )
                
                # Check if we need to navigate
                current_url = self.driver.current_url
                if "about:blank" in current_url or current_url == "data:,":
                    url_to_open = self._extract_url_from_command(objective)
                    if url_to_open:
                        print(f"🔍 Detected URL in objective. Opening {url_to_open}...")
                        navigate_decision = {
                            "action": {"name": "NAVIGATE", "parameters": {"url": url_to_open}}
                        }
                        result = self.execute_advanced_action(navigate_decision)
                        last_action_feedback = result.message
                        if not result.success:
                            print(f"❌ Navigation failed: {result.message}")
                            continue
                    else:
                        print("⚠️ Please provide a URL or be more specific about the website to visit.")
                        continue

                # Main execution loop with advanced features
                print(f"\n🚀 Starting objective: '{objective}'")
                print(f"⏱️ Timeout: 8 minutes, Max steps: 50")
                
                start_time = time.time()
                # Auto-adaptive step limits based on objective complexity
                objective_length = len(objective.split())
                if objective_length <= 5:
                    max_steps = 100  # Simple tasks
                elif objective_length <= 15:
                    max_steps = 200  # Medium complexity
                else:
                    max_steps = 500  # Complex multi-step tasks
                
                # Dynamic timeout based on complexity
                task_timeout = min(300, max(60, objective_length * 10))  # 1-5 minutes
                task_timeout = 480  # 8 minutes
                consecutive_failures = 0
                max_consecutive_failures = 3
                step_counter = 0

                while time.time() - start_time < task_timeout and step_counter < max_steps:
                    step_counter += 1
                    print(f"\n--- 🔄 Step {step_counter}/{max_steps} ---")
                    
                    try:
                        # Get advanced elements with confidence scoring (faster detection)
                        retry_count = 0
                        max_retries = 2  # Reduced retries for speed
                        
                        while retry_count < max_retries:
                            # Clear cache for fresh detection
                            self.elements_cache = []
                            self.elements_cache = self._get_advanced_interactive_elements()
                            if self.elements_cache or retry_count == max_retries - 1:
                                break
                            print(f"⏳ No elements found, retrying... ({retry_count + 1}/{max_retries})")
                            time.sleep(1)  # Reduced wait time
                            retry_count += 1
                        
                        if not self.elements_cache:
                            print("⚠️ No interactive elements found. Waiting for page to load...")
                            time.sleep(3)
                            continue
                        
                        print(f"🔍 Found {len(self.elements_cache)} interactive elements (avg confidence: {sum(e.confidence_score for e in self.elements_cache)/len(self.elements_cache):.2f})")
                        
                        # Take advanced screenshot and annotate
                        screenshot_png = self.get_screenshot_as_png()
                        annotated_screenshot = self._draw_advanced_labels_on_image(screenshot_png, self.elements_cache)
                        annotated_screenshot_b64 = base64.b64encode(annotated_screenshot).decode('utf-8')
                        
                        # Get AI decision with advanced analysis
                        decision = self.decide_next_action(
                            objective, annotated_screenshot_b64, self.elements_cache, last_action_feedback
                        )
                        
                        if not decision or not decision.get('action'):
                            print("❌ Failed to get AI decision")
                            consecutive_failures += 1
                            if consecutive_failures >= max_consecutive_failures:
                                break
                            continue
                        
                        thought = decision.get('thought', 'No analysis provided')
                        confidence = decision.get('confidence', 0.5)
                        reasoning = decision.get('reasoning', 'No reasoning provided')
                        
                        print(f"🤔 AI Analysis: {thought}")
                        print(f"🎯 Confidence: {confidence:.2f} | Reasoning: {reasoning[:100]}...")
                        
                        # Execute advanced action
                        result = self.execute_advanced_action(decision)
                        print(f"📋 Result: {result.message}")
                        
                        if result.message == "🏁 Task finished.":
                            print(f"\n🎉 Objective completed successfully in {step_counter} steps!")
                            print(f"📊 Success Rate: {self.session_data['successful_actions']}/{self.session_data['total_actions']} ({(self.session_data['successful_actions']/max(1, self.session_data['total_actions'])*100):.1f}%)")
                            break
                        
                        if not result.success:
                            consecutive_failures += 1
                            if consecutive_failures >= max_consecutive_failures:
                                print(f"❌ Too many consecutive failures ({consecutive_failures}). Ending task.")
                                break
                        else:
                            consecutive_failures = 0
                        
                        last_action_feedback = result.message
                        
                        # Human-like delay between actions
                        time.sleep(random.uniform(1.5, 2.5))
                        
                    except KeyboardInterrupt:
                        print("\n⏹️ Task interrupted by user.")
                        break
                    except Exception as e:
                        logger.error(f"Error in step {step_counter}: {e}")
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            print(f"💥 Critical errors occurred. Stopping task.")
                            break
                        continue
                
                else:
                    # Loop ended due to timeout or max steps
                    if step_counter >= max_steps:
                        print(f"⏹️ Task stopped after {max_steps} steps to prevent infinite loops.")
                    else:
                        print(f"⏱️ Task timed out after {task_timeout//60} minutes.")
                
                # Generate final report and save final screenshot
                final_screenshot = self.save_advanced_screenshot(f"final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                print(f"📸 Final screenshot saved: {final_screenshot}")
                
                # Show session summary
                self._display_session_stats()
                
            except KeyboardInterrupt:
                print("\n⏹️ Interrupted by user.")
                break
            except Exception as e:
                logger.error(f"Fatal error: {e}")
                print(f"💥 Fatal error: {e}")
                continue
        
        # Cleanup and final report
        try:
            print("\n📄 Generating final session report...")
            final_report = self.generate_session_report()
            if final_report:
                print(f"📊 Final report saved: {final_report}")
            
            self.driver.quit()
            print("🧹 Browser closed successfully.")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        print("👋 Atharva Agent session ended. Thank you for using our advanced AI system!")

    def _get_page_info(self) -> Dict:
        """Get detailed page information."""
        try:
            return {
               
                "url": self.driver.current_url,
                "title": self.driver.title,
                "elements_count": len(self.elements_cache),
                "visible_elements": sum(1 for e in self.elements_cache if e.is_visible),
                "form_fields": sum(1 for e in self.elements_cache if e.is_form_field),
                "clickable_elements": sum(1 for e in self.elements_cache if e.is_clickable),
                "avg_confidence": sum(e.confidence_score for e in self.elements_cache) / len(self.elements_cache) if self.elements_cache else 0,
                "page_load_state": self.driver.execute_script('return document.readyState'),
                "session_stats": self.session_data
            }
        except Exception as e:
            return {"error": str(e)}

    def _display_action_history(self):
        """Display recent action history."""
        print(f"\n📜 Action History ({len(self.action_history)} total actions):")
        print("-" * 80)
        
        recent_actions = self.action_history[-15:]  # Show last 15 actions
        for i, action in enumerate(recent_actions, 1):
            status_icon = "✅" if action.success else "❌"
            duration_str = f"{action.duration:.2f}s"
            timestamp_str = action.timestamp.strftime("%H:%M:%S")
            
            print(f"{i:2d}. {status_icon} {action.action_type:<12} | {timestamp_str} | {duration_str:>6} | {action.message}")
            
        print("-" * 80)

    def _display_session_stats(self):
        """Display comprehensive session statistics."""
        current_time = datetime.now()
        session_duration = (current_time - self.session_data['start_time']).total_seconds()
        success_rate = (self.session_data['successful_actions'] / max(1, self.session_data['total_actions'])) * 100
        
        print(f"\n📊 SESSION STATISTICS")
        print("=" * 50)
        print(f"🕐 Session Duration: {session_duration//60:.0f}m {session_duration%60:.0f}s")
        print(f"🎯 Total Actions: {self.session_data['total_actions']}")
        print(f"✅ Successful Actions: {self.session_data['successful_actions']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"🌐 Websites Visited: {len(self.session_data['websites_visited'])}")
        print(f"📝 Forms Filled: {self.session_data.get('forms_filled', 0)}")
        print(f"🔍 Searches Performed: {self.session_data.get('searches_performed', 0)}")
        print(f"📸 Screenshots Taken: {len([a for a in self.action_history if a.screenshot_path])}")
        print(f"⚡ Avg Action Duration: {sum(a.duration for a in self.action_history)/max(1, len(self.action_history)):.2f}s")
        print("=" * 50)

    def _display_help(self):
        """Display comprehensive help information."""
        print("""
🎯 Atharva Agent - HELP

📝 NATURAL LANGUAGE COMMANDS:
   • "open google.com and search for artificial intelligence"
   • "go to youtube.com and find programming tutorials"
   • "navigate to amazon.com and search for laptops"
   • "fill out the contact form on this page"
   • "click the login button and enter my credentials"

🔧 SPECIAL COMMANDS:
   • 'exit' - Quit the agent
   • 'info' - Show detailed page information
   • 'screenshot' - Take an annotated screenshot
   • 'history' - Show recent action history
   • 'report' - Generate HTML session report
   • 'stats' - Display session statistics
   • 'chat' - Demo the new chat interface
   • 'help' - Show this help message

🎨 VISUAL FEATURES:
   • Human-like cursor movement (8-step animations)
   • Real-time AI analysis bubbles
   • Progress indicators and status bars
   • Element confidence scoring
   • Professional screenshot annotations

🛠️ ADVANCED CAPABILITIES:
   • 20+ intelligent actions with error recovery
   • Auto-detection of input fields
   • Advanced element analysis
   • Multi-strategy clicking
   • JavaScript execution
   • Form filling automation
   • Smart error handling

💡 TIPS FOR BEST RESULTS:
   1. Be specific: "Search for Python tutorials on YouTube"
   2. Break down complex tasks into smaller steps
   3. Use natural language descriptions
   4. Monitor the AI analysis bubbles for insights
   5. Check session stats regularly for performance

🚀 EXAMPLE ADVANCED TASKS:
   • "Open LinkedIn, search for AI jobs in San Francisco"
   • "Go to Wikipedia and research quantum computing"
   • "Navigate to GitHub and find trending Python projects"
   • "Open Twitter and compose a tweet about AI"
        """)

    def _demo_chat_interface(self):
        """Demonstrate the clean, minimal chat interface features."""
        print("\n🎨 === CHAT INTERFACE DEMO ===")
        print("Demonstrating the new clean, minimal chat bubble design...")
        
        try:
            # Demo 1: Basic chat bubble
            print("\n1. 📱 Basic Chat Bubble")
            self.show_chat_bubble(
                "Hello! I'm your AI assistant. This is a clean, minimal chat interface with modern design.",
                position="top-right",
                duration=4000
            )
            time.sleep(2)
            
            # Demo 2: Different positions
            print("2. 📍 Different Positions")
            positions = ["top-left", "top-right", "bottom-left", "bottom-right"]
            messages = [
                "Top-left position with professional styling.",
                "Top-right with smooth animations.",
                "Bottom-left with subtle shadows.",
                "Bottom-right with clean typography."
            ]
            
            for pos, msg in zip(positions, messages):
                self.show_chat_bubble(msg, position=pos, duration=3000)
                time.sleep(1.5)
            
            time.sleep(2)
            
            # Demo 3: Typing indicator
            print("3. ⌨️ Typing Indicator")
            self.show_typing_indicator("top-right")
            time.sleep(3)
            self.hide_typing_indicator()
            
            # Demo 4: AI response with typing effect
            print("4. 🤖 AI Response with Typing Effect")
            self.show_ai_response(
                "This demonstrates the complete AI response flow. The typing indicator appears first, then this message slides in smoothly with professional styling.",
                position="top-right",
                show_typing=True,
                typing_delay=2.0
            )
            
            time.sleep(3)
            
            # Demo 5: Message updates
            print("5. 🔄 Dynamic Message Updates")
            self.show_chat_bubble("Initial message...", position="bottom-right", duration=0)
            time.sleep(1)
            
            for i, update in enumerate([
                "Updating message content...",
                "Messages can be dynamically updated.",
                "Final message with clean design!"
            ], 1):
                time.sleep(1.5)
                self.update_chat_bubble(update)
                print(f"   Updated to message {i}")
            
            time.sleep(2)
            self.remove_chat_bubble()
            
            print("\n✨ Chat Interface Demo Complete!")
            print("Features demonstrated:")
            print("   • Clean, minimal design with rounded corners")
            print("   • Subtle drop shadows and modern typography")
            print("   • Smooth animations and transitions")
            print("   • Multiple positioning options")
            print("   • Typing indicators for better UX")
            print("   • Dynamic message updates")
            print("   • Professional Inter/Arial font styling")
            print("   • First sentence bold formatting")
            print("   • Triangle pointer connection to AI avatar")
            
        except Exception as e:
            print(f"❌ Demo error: {e}")
            logger.error(f"Chat interface demo error: {e}")

if __name__ == "__main__":
    try:
        # Initialize with advanced settings
        agent = MegaAdvancedBrowserAgent(
            headless=False,
            window_size=(1920, 1080),
            enable_extensions=True
        )
        agent.run()
    except KeyboardInterrupt:
        print("\n⏹️ Program interrupted by user.")
    except Exception as e:
        logger.error(f"Fatal error initializing agent: {e}")
        print(f"💥 Fatal error: {e}")
        print("Please check the logs/mega_browser_agent.log file for detailed error information.")
