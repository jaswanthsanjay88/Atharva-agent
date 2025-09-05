# 🤖 Atharva Agent v3.2 - Remote Browser Automation System

An AI-powered web automation agent with remote browser control capabilities, powered by Google Gemini.

## 🌟 Features

### Core Browser Automation
- **AI-Powered Decision Making**: Uses Google Gemini for intelligent web navigation
- **Advanced Chrome Integration**: Custom profiles, anti-detection, cursor optimization
- **Visual Element Detection**: Annotated screenshots with interactive element mapping
- **Smart URL Detection**: Automatic navigation from natural language commands

### Remote Control System
- **WebSocket Server**: Real-time browser control via WebSocket connections
- **Web Frontend**: Beautiful React-like interface for remote browser control
- **Session Management**: Multiple concurrent browser sessions
- **Live Screenshot Streaming**: Real-time visual feedback
- **Command Processing**: Natural language and direct commands

### Advanced Features
- **Database Integration**: Session persistence and data management
- **Email Reporting**: Automated session reports and notifications
- **Chat Interface**: Real-time communication and logging
- **Profile Support**: Use existing Chrome profiles and extensions

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd Agent-main

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Copy the example environment file and add your API keys:
```bash
cp .env.example .env
```

Then edit `.env` and replace the placeholder values with your actual API keys:
```env
GOOGLE_API_KEY=your_actual_google_api_key_here
ATHARVA_API_KEY=your_actual_google_api_key_here
ATHARVA_MODEL=gemini-2.0-flash
```

**Important:** Get your Google Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### 3. Run the Agent

```bash
python agent_atharva.py
```

### 4. Available Commands

- `remote` - Start remote WebSocket and HTTP servers
- `screenshot` - Take a screenshot of current page
- `report` - Generate session report
- `exit` - Quit the agent

## 🌐 Remote Browser Control

### Starting Remote Control

1. Run the agent: `python agent_atharva.py`
2. Type `remote` to start the remote servers
3. The web interface will open automatically at `http://localhost:8000/frontend.html`

### Remote Control Features

- **Live Browser View**: Real-time screenshots of the browser
- **Command Interface**: Send natural language commands
- **Quick Actions**: Screenshot, scroll, navigate buttons
- **Session Logs**: Real-time activity monitoring
- **Page Information**: Current URL, title, and status

### Architecture

```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│   Web Frontend  │ ←────────────→   │  Python Backend │
│   (React-like)  │                  │   (Agent Core)  │
└─────────────────┘                  └─────────────────┘
                                             │
                                             ▼
                                     ┌─────────────────┐
                                     │  Browser Engine │
                                     │   (Selenium)    │
                                     └─────────────────┘
```

## 📁 Project Structure

```
Agent-main/
├── agent_atharva.py        # Main agent with AI and browser automation
├── websocket_server.py     # WebSocket server for remote control
├── http_server.py         # HTTP server for frontend
├── frontend.html          # Web interface for remote control
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
└── logs/                  # Agent logs and reports
    ├── screenshots/       # Captured screenshots
    ├── reports/          # HTML session reports
    └── agent.log         # Detailed logs
```

## 🔧 Configuration

### Chrome Profile Setup

Update the Chrome profile path in the main block:

```python
chrome_profile_path = r"C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data"
profile_directory = "Default"  # or your profile name
```

### Advanced Options

- **Headless Mode**: Set `headless=True` for background operation
- **Window Size**: Customize with `window_size=(width, height)`
- **Extensions**: Enable/disable with `enable_extensions=True/False`

## 🎯 Usage Examples

### Natural Language Commands

```
🎯 > go to google.com and search for AI news
🎯 > navigate to github.com
🎯 > take a screenshot
🎯 > scroll down and click the first link
```

### Remote Control

1. Start remote mode: Type `remote` in the agent console
2. Open the web interface (automatically opens)
3. Use the command input or quick action buttons
4. Monitor real-time logs and screenshots

## 🧠 AI Integration

The agent uses Google Gemini for:
- **Command Understanding**: Natural language processing
- **Decision Making**: Intelligent next-step determination
- **Element Recognition**: Smart element identification
- **Objective Planning**: Multi-step task planning

## 🔒 Security Features

- **Anti-Detection**: Advanced browser fingerprint spoofing
- **Profile Isolation**: Separate browser profiles for sessions
- **Secure WebSockets**: Encrypted communication channels
- **Session Management**: Secure session handling

## 📊 Monitoring & Reporting

- **Real-time Logs**: Live activity monitoring
- **Session Reports**: Detailed HTML reports with screenshots
- **Performance Metrics**: Success rates and timing data
- **Error Tracking**: Comprehensive error logging

## 🛠️ Development

### Adding Custom Commands

```python
def handle_custom_command(self, parameters):
    """Handle custom command logic."""
    # Your custom logic here
    return {'success': True, 'message': 'Custom command executed'}
```

### Extending WebSocket Server

```python
# In websocket_server.py
elif command_type == 'your_custom_command':
    result = self.agent.handle_custom_command(parameters)
```

## 🐛 Troubleshooting

### Common Issues

1. **Chrome Driver Issues**: Update with `webdriver-manager`
2. **API Key Errors**: Check `.env` file configuration
3. **Port Conflicts**: Change ports in server configuration
4. **Profile Errors**: Ensure Chrome profile path is correct

### Debug Mode

Enable detailed logging:
```python
logger.setLevel(logging.DEBUG)
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## � Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the logs directory for detailed error information
- Review the troubleshooting section

---

**Atharva Agent v3.2** - Bringing AI-powered browser automation to the next level! 🚀

Welcome to the Mega Advanced AI Browser Agent, a sophisticated autonomous agent designed to navigate and interact with the web to achieve complex objectives using the power of large language models.

This isn't just a simple automation script. It's a powerful framework that provides rich, real-time visual feedback directly within the browser, simulating a human-like interaction flow. The agent analyzes web pages, decides on the best course of action, and executes it, all while showing you its thought process through an elegant in-browser UI.


---

## ✨ Features

This project is packed with over 50 advanced features, making it a robust platform for web automation.

#### 🧠 **AI-Powered Core**
*   **Natural Language Control:** Give the agent complex objectives in plain English.
*   **AI Decision Making:** Utilizes a large language model to analyze the screen and decide the next best action.
*   **Streaming AI Responses:** The agent's thoughts and decisions are streamed in real-time for better observability.
*   **Confidence Scoring:** The AI provides a confidence score for each decision it makes.

#### 🎨 **Rich Visual Feedback & In-Browser UI**
*   **Human-like Cursor Movement:** A custom-rendered cursor moves smoothly between elements with realistic, multi-step animations.
*   **Clean Chat Interface:** A modern, minimal speech bubble UI displays AI thoughts, analysis, and status updates.
*   **AI Avatar & Typing Indicator:** An AI avatar and typing indicator create a more intuitive user experience.
*   **Live Element Annotation:** Screenshots are automatically annotated with numbered labels on all interactive elements.
*   **Dynamic Progress Indicators:** Professional progress rings and status bars show the agent's current state.

#### 🛠️ **Advanced Browser Automation**
*   **Comprehensive Action Library:** Supports over 20 actions, including `NAVIGATE`, `CLICK`, `TYPE`, `SCROLL`, `HOVER`, `EXECUTE_JS`, and more.
*   **Robust Element Detection:** Identifies all interactive elements on a page, including those within `iframes`.
*   **Multi-Strategy Interaction:** Uses a cascade of strategies (e.g., WebDriver click, JavaScript click) to ensure successful interactions.
*   **Auto-Detection:** Automatically finds the most relevant input field for a given task, like a search bar.
*   **Advanced Error Handling & Recovery:** The agent is designed to be resilient, with multiple retry mechanisms and failure detection.

#### 📊 **Reporting & Logging**
*   **SQLite Database Logging:** Every action and session detail is logged to a local SQLite database for analysis.
*   **Professional HTML Reports:** Automatically generate a comprehensive HTML report at the end of each session with stats, timelines, and screenshots.
*   **Action-Level Screenshots:** A screenshot is saved for every single action, whether it succeeds or fails, providing a complete visual audit trail.
*   **Email Notifications:** Can be configured to automatically email session reports.
*   **Detailed Session Analytics:** Tracks success rates, actions per minute, total duration, and other key performance indicators.

---

## 🚀 How It Works

The agent operates in a continuous loop, observing the screen, thinking, and acting.

1.  **User Objective:** You provide a high-level goal, like `"Go to Google, search for the latest AI news, and summarize the top result."`
2.  **Observe:** The agent captures the current state of the web page.
3.  **Analyze & Annotate:** It identifies all interactive elements (buttons, links, inputs) and generates a screenshot, drawing numbered labels over each element.
4.  **Think:** The annotated screenshot, the objective, and the history of past actions are sent to the AI model. The AI analyzes the visual information and returns a structured JSON response containing its `thought` process and the next `action` to take (e.g., `{"action": {"name": "TYPE", "parameters": {"id": 5, "text": "latest AI news"}}}`).
5.  **Act:** The agent parses the AI's decision and executes the specified action using Selenium WebDriver. The custom UI (cursor, bubbles) provides visual feedback on this action.
6.  **Log & Repeat:** The result of the action is logged to the database. The loop repeats until the objective is marked as complete by the AI.

---

## 📦 Installation & Setup

Follow these steps to get the agent up and running.

#### **1. Prerequisites**
*   Python 3.8+
*   Google Chrome browser installed

#### **2. Clone the Repository**
```bash
git clone https://github.com/Niansuh/Agent.git
cd Agent
```

#### **3. Create a Virtual Environment**
```bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### **4. Install Dependencies**
Create a `requirements.txt` file with the following contents:

```txt
selenium
webdriver-manager
requests
python-dotenv
Pillow
numpy
opencv-python
```

Then, install them using pip:
```bash
pip install -r requirements.txt
```

#### **5. Configure Environment Variables**
Create a file named `.env` in the root of the project and add your credentials. This is crucial for the AI and email functionality.

```env
# AI Model Configuration (compatible with OpenAI's API format)
API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
API_ENDPOINT_URL="https://your-ai-provider-api.com/v1/chat/completions"
MODEL_NAME="your-chosen-model-name"

# Email Configuration (Optional - for sending reports)
EMAIL_FROM="your-email@gmail.com"
EMAIL_USERNAME="your-email@gmail.com"
EMAIL_PASSWORD="your-gmail-app-password"
```
**Note:** For Gmail, you will need to generate an "App Password" to use here.

---

## 🏃‍♀️ Running the Agent

To start the agent, run the main script from your terminal:

```bash
python your_script_name.py
```

The script will initialize, open a Chrome browser window, and you will be prompted to enter an objective in the console.

#### **Example Objectives**
*   `go to wikipedia.org and search for "Quantum Computing"`
*   `open youtube.com, find a channel called "MKBHD", and click on the latest video`
*   `navigate to github.com and find trending python repositories`

#### **Special Commands**
You can also enter special commands at the prompt:
*   `exit`: Shuts down the agent and generates a final report.
*   `report`: Generates and saves an HTML report for the current session.
*   `stats`: Displays the latest session statistics in the console.
*   `history`: Shows a log of the most recent actions taken.
*   `screenshot`: Manually takes and saves an annotated screenshot.
*   `chat`: Runs a short demo of the in-browser chat UI features.
*   `help`: Displays a list of available commands and tips.

---
## 📁 Project Structure

```
.
├── data/                  # SQLite database files
├── downloads/             # Files downloaded by the agent
├── logs/                  # Detailed .log files for debugging
├── reports/               # Generated HTML session reports
├── screenshots/           # All screenshots taken by the agent
├── .env                   # Environment variables (API keys, etc.)
├── your_script_name.py    # The main Python script
└── README.md              # This file
```

---

## Using Ollama (llama3) locally

If you want to run a local model with Ollama and use `llama3`, here are the exact PowerShell commands.

1) Pull the llama3 model (replace with the exact Ollama model name if different):

```powershell
ollama pull llama3
```

2) Run the model locally (this starts the Ollama server for the model):

```powershell
ollama run llama3
```

3) In a separate PowerShell session, run the agent and tell it to use Ollama:

```powershell
$env:USE_OLLAMA='true'
$env:API_ENDPOINT_URL='http://127.0.0.1:11434/v1/chat/completions'
python e:\Agent-main\agent.py
```

Notes:
- `USE_OLLAMA=true` tells the agent to prefer Ollama/local behavior. The code will try `/v1/generate` if `/v1/chat/completions` returns 404.
- You can also set `MODEL_NAME` to another model in your `.env` if you prefer.
# Atharva-agent
