HQ Cyber-Grid Energy Core ⚡🤖

HQ Cyber-Grid Energy Core is an interactive, smart-grid digital twin dashboard and conversational monitoring system designed to humanize workspace energy consumption. Built for hackathons, this platform simulates office workspace power footprints at 60x accelerated speed (1 real second = 1 simulated minute), detects anomalies (after-hours waste and continuous usage overruns), and broadcasts humanized alerts to a Discord channel via Google's Gemini 2.5 Flash API.

The project implements a single-instance unified container lifecycle: when Uvicorn boots up the FastAPI backend, a lifespan process manager spawns the Discord bot as an independent, concurrent background subprocess. Both microservices coordinate in-memory over local loopback ports.

📐 System Architecture

Below is the layout of how the frontend dashboard, the FastAPI backend, the Discord Bot process, the Discord WebSocket gateway, and the Gemini AI engine communicate:

                  +----------------------------------+
                  |        Web Browser View          |
                  |     (HTML/Tailwind/JS UI)        |
                  +-----------------+----------------+
                                    |
                    REST / WS Ports | (JSON Telemetry & Toggle Actions)
                                    v
                  +----------------------------------+
                  |          FastAPI App             |
                  |           (main.py)              |
                  |     - Port: 10000 (Render UI)    |
                  |     - Simulated Grid State       |
                  +--------+----------------+--------+
                           |                ^
             Subprocess    |                | Local HTTP API Calls
             Spawns on     |                | (api/devices, api/usage)
             Lifespan Init |                |
                           v                |
                  +-------------------------+--------+
                  |         Discord Bot              |
                  |          (bot.py)                |
                  |     - Internal Webhook (8001)    |
                  |     - Loops Alerts (30s task)    |
                  +----+------------------------+----+
                       |                        |
                       | Discord WebSockets     | Gemini AI SDK
                       v                        v
            +--------------------+    +--------------------+
            |   Discord Servers  |    |  Google AI Studio  |
            | (Chat Commands/Alert)  |    | (Gemini 2.5 Flash) |
            +--------------------+    +--------------------+


📂 Repository File Structure

Ensure your repository contains these core files arranged in the root folder:

TechhackathonProject/
│
├── main.py             # FastAPI App & Subprocess Lifespan Controller
├── bot.py              # Discord Bot & Asynchronous Webhook Receiver
├── index.html          # Interactive Frontend Smart-Grid Layout
├── requirements.txt    # Python Project Dependencies Snapshot
├── .gitignore          # Safeguards private config files (.env, pycache)
└── README.md           # This comprehensive documentation file


⚙️ Prerequisites

Before launching the application, ensure you have configured:

Python 3.11+ installed on your system.

A Discord Bot Token from the Discord Developer Portal with Message Content Intent enabled.

A Google Gemini API Key from Google AI Studio.

🛠️ Local Setup and Execution

Follow these steps to download, install dependencies, and launch the unified stack on your local machine:

1. Clone the Repository

git clone [https://github.com/sanaf410-niaf/TechhackathonProject.git](https://github.com/sanaf410-niaf/TechhackathonProject.git)
cd TechhackathonProject


2. Create and Activate a Virtual Environment

Windows (PowerShell):

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
python -m venv venv
.\venv\Scripts\Activate.ps1


macOS/Linux:

python3 -m venv venv
source venv/bin/activate


3. Install Required Dependencies

pip install -r requirements.txt


4. Create local environment variables

Create a .env file in the root directory (Git will automatically ignore this due to .gitignore):

DISCORD_TOKEN=your_secret_discord_bot_token
GEMINI_API_KEY=your_google_gemini_api_key


5. Launch the Server

python -m uvicorn main:app --host 127.0.0.1 --port 10000 --reload


Once initiated, the Uvicorn runtime automatically spawns bot.py alongside your API router.

Open your browser and navigate to http://127.0.0.1:10000 to view your dashboard.

🚀 Deployment to Render (24/7 Cloud hosting)

To keep your dashboard online and your Discord bot listening 24/7 even after you shut down your PC, deploy it to a single Render Web Service:

Link your GitHub account on the Render Dashboard.

Select New + -> Web Service and choose your TechhackathonProject repository.

Populate the configurations as follows:

Name: techhackathon-grid-core

Runtime: Python

Build Command: pip install -r requirements.txt

Start Command: python -m uvicorn main:app --host 0.0.0.0 --port 10000

Under the Advanced section, select Add Environment Variable to add your secret keys securely without exposing them in code commits:

DISCORD_TOKEN = your_discord_bot_token

GEMINI_API_KEY = your_gemini_api_key

Click Create Web Service.

🤖 Interactive Discord Chat Bot Commands

Once your bot is added to your target server guild containing a #general text channel, staff members and judges can type commands directly in the chat to receive real-time updates parsed through the conversational Gemini LLM:

!status: Queries the real-time device matrix of the grid system and generates a descriptive summary of whether office spaces are operating under normal power thresholds.

!usage: Provides a conversational breakdown of energy load (in Watts) across the Drawing Room, Work Room 1, and Work Room 2 and estimates simulated daily consumption ($kWh$).

!room <room_name>: Fetches device-by-device active states and runtimes of the specified workspace.

🚨 Proactive Energy Waste Warnings

The bot runs a 30-second checking loop against /api/alerts to detect wasteful energy patterns. When an alert condition is met, Gemini formats a conversational message, sounding like a concerned coworker noticing active appliances after-hours, and posts it in the discord channel:

After-Hours Anomaly Detector: Flags any fan or light left running outside standard work shifts (before 9:00 AM or after 5:00 PM accelerated simulation time).

Continuity Waste Watcher: Alerts when every appliance in a workspace remains continuously on for more than 2 simulated hours.