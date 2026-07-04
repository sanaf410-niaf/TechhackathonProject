import discord
from discord.ext import tasks
import aiohttp
from aiohttp import web
import asyncio
import os
import json
from google import genai
from dotenv import load_dotenv

# Load credentials
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Configure the AI Brain (Using modern 2026 SDK)
if GEMINI_KEY:
    ai_client = genai.Client(api_key=GEMINI_KEY)
else:
    ai_client = None

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

API_BASE = "http://127.0.0.1:8000"
main_loop = None
last_alert_hash = None 

async def generate_humanized_response(raw_data: str, context: str) -> str:
    """Feeds raw backend JSON into the LLM to generate a conversational response."""
    if not ai_client:
        return "🤖 **System Error:** GEMINI_API_KEY is missing from the .env file!"
    
    system_prompt = (
        "You are the friendly, helpful AI Energy Manager for our office. "
        "Our boss HATES robotic data dumps. Always be conversational, concise, and natural. "
        "Use occasional emojis, but remain professional. Do not use code blocks."
    )
    
    try:
        response = await ai_client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{system_prompt}\n\nTask: {context}\n\nRaw Alert Data: {raw_data}"
        )
        return response.text
    except Exception as e:
        return f"❌ AI Core offline. Falling back to default. Error: {e}"

# Keeps manual commands working!
async def process_telemetry_flow(command_string: str):
    cmd = command_string.strip().lower()
    
    if cmd == "!status" or cmd == "!usage" or cmd.startswith("!room"):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/api/devices") as dev_res, session.get(f"{API_BASE}/api/usage") as use_res:
                if dev_res.status == 200 and use_res.status == 200:
                    devices = await dev_res.json()
                    usage = await use_res.json()
                    
                    grid_state = json.dumps({"devices": devices, "usage": usage})
                    
                    return await generate_humanized_response(
                        grid_state, 
                        f"The user typed the command: '{cmd}'. Give them the info they requested based on the data."
                    )

    return "🤖 I don't recognize that command! Try asking me for `!status`, `!usage`, or check a room like `!room Work Room 1`."

async def dispatch_via_discord_core(command: str, reply: str):
    for guild in client.guilds:
        target_channel = discord.utils.get(guild.text_channels, name="general")
        if target_channel:
            await target_channel.send(f"💻 **Remote Command Triggered:** `{command}`\n\n{reply}")
            break

@client.event
async def on_ready():
    global main_loop
    main_loop = asyncio.get_running_loop()
    print(f"✅ AI Discord Bot Process spawned independently as {client.user}")
    if not proactive_alert_broadcaster.is_running():
        proactive_alert_broadcaster.start()
    asyncio.create_task(run_webhook_bridge())

@client.event
async def on_message(message):
    if message.author == client.user: return
    content = message.content.strip()
    if content.startswith("!"):
        async with message.channel.typing():
            reply = await process_telemetry_flow(content)
            await message.channel.send(reply)

async def handle_ui_post(request):
    data = await request.json()
    command = data.get("command", "")
    reply = await process_telemetry_flow(command)
    if main_loop:
        asyncio.run_coroutine_threadsafe(dispatch_via_discord_core(command, reply), main_loop)
    return web.json_response({"response": reply})

async def run_webhook_bridge():
    app = web.Application()
    app.router.add_post('/webhook', handle_ui_post)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8001)
    await site.start()

# --- PROACTIVE AI ALERTS ---
# Changed to 5 seconds to keep up with the 60x Time Accelerator!
@tasks.loop(seconds=5) 
async def proactive_alert_broadcaster():
    global last_alert_hash
    await client.wait_until_ready()
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE}/api/alerts") as resp:
                if resp.status == 200:
                    alerts = await resp.json()
                    
                    if alerts:
                        current_hash = hash(json.dumps(alerts))
                        
                        if current_hash != last_alert_hash:
                            last_alert_hash = current_hash # Memory check to prevent spam
                            
                            raw_alert_data = json.dumps(alerts)
                            ai_instruction = (
                                "We just received these system alerts for energy waste. "
                                "Generate a highly conversational, proactive warning message to send to the staff. "
                                "Make it sound like a helpful coworker noticing something was left running "
                                "(e.g., 'Hey! Work Room 2 still has 2 fans and 3 lights ON and it's 10 PM. Did someone forget to leave?')."
                            )
                            
                            humanized_warning = await generate_humanized_response(raw_alert_data, ai_instruction)
                            
                            for guild in client.guilds:
                                target_channel = discord.utils.get(guild.text_channels, name="general")
                                if target_channel:
                                    await target_channel.send(f"🚨 **Grid Monitor Alert:**\n{humanized_warning}")
                                    break
                    else:
                        last_alert_hash = None
        except Exception: pass

if TOKEN:
    client.run(TOKEN)
else:
    print("❌ ERROR: No Discord token payload configured inside the local .env setup profile target.")