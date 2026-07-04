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

# Configure AI Brain (Modern SDK)
if GEMINI_KEY:
    ai_client = genai.Client(api_key=GEMINI_KEY)
else:
    ai_client = None

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# FIX: Changed from 10000 to 8000 to align with your Uvicorn startup configuration port
API_BASE = "http://127.0.0.1:8000" 
main_loop = None
last_alert_hash = None 

async def generate_humanized_response(raw_data: str, context: str) -> str:
    """Feeds raw backend JSON into the LLM to generate a conversational response."""
    if not ai_client:
        return "🤖 **System Error:** GEMINI_API_KEY configuration variable is completely missing!"
    
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

async def process_telemetry_flow(command_string: str):
    cmd = command_string.strip().lower()
    
    if cmd == "!status" or cmd == "!usage" or cmd.startswith("!room"):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{API_BASE}/api/devices") as dev_res, session.get(f"{API_BASE}/api/usage") as use_res:
                    if dev_res.status == 200 and use_res.status == 200:
                        devices = await dev_res.json()
                        usage = await use_res.json()
                        grid_state = json.dumps({"devices": devices, "usage": usage})
                        
                        return await generate_humanized_response(
                            grid_state, 
                            f"The user typed the command: '{cmd}'. Give them the info they requested based on the data."
                        )
            except Exception as e:
                return f"⚠️ Bot failed to read local backend telemetry: {str(e)}"
                
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
    print(f"✅ AI Discord Bot Process logged into Discord as {client.user}")
    if not proactive_alert_broadcaster.is_running():
        proactive_alert_broadcaster.start()

@client.event
async def on_message(message):
    if message.author == client.user: return
    content = message.content.strip()
    if content.startswith("!"):
        async with message.channel.typing():
            reply = await process_telemetry_flow(content)
            await message.channel.send(reply)

async def handle_ui_post(request):
    try:
        data = await request.json()
        command = data.get("command", "")
        reply = await process_telemetry_flow(command)
        if main_loop:
            asyncio.run_coroutine_threadsafe(dispatch_via_discord_core(command, reply), main_loop)
        return web.json_response({"status": "success", "response": reply})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def run_webhook_bridge():
    app = web.Application()
    app.router.add_post('/webhook', handle_ui_post)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8001)
    await site.start()
    print("🔌 Webhook Bridge explicitly listening on http://127.0.0.1:8001")

# --- PROACTIVE AI ALERTS ---
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
                            last_alert_hash = current_hash
                            raw_alert_data = json.dumps(alerts)
                            ai_instruction = (
                                "We just received these system alerts for energy waste. "
                                "Generate a highly conversational, proactive warning message to send to the staff. "
                                "Make it sound like a helpful coworker noticing something was left running."
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

# Async entry point to start the web service immediately
async def main():
    await run_webhook_bridge()
    if TOKEN:
        async with client:
            await client.start(TOKEN)
    else:
        print("❌ ERROR: No Discord token configuration properties profile found.")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())