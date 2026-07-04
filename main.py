from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import asyncio
import random
import os
import sys
import subprocess
import aiohttp

from dotenv import load_dotenv
load_dotenv()

# --- TIME ACCELERATOR (60x Speed) ---
APP_START_TIME = datetime.now()
TIME_MULTIPLIER = 60

def get_now():
    """Returns the accelerated simulation time instead of real time."""
    real_elapsed = (datetime.now() - APP_START_TIME).total_seconds()
    return APP_START_TIME + timedelta(seconds=real_elapsed * TIME_MULTIPLIER)
# ------------------------------------

system_config = {"mode": "auto"}
devices = {}
rooms_list = ["Drawing Room", "Work Room 1", "Work Room 2"]

def init_devices():
    id_counter = 1
    for room in rooms_list:
        for f in range(1, 3):
            dev_id = f"dev_{id_counter}"
            devices[dev_id] = {
                "id": dev_id, "name": f"Fan {f}", "type": "fan", "room": room,
                "status": "off", "wattage": 60, "toggle_count": 0, 
                "activated_at": None,
                "last_changed": get_now().strftime("%I:%M %p"), "history": []
            }
            id_counter += 1
        for l in range(1, 4):
            dev_id = f"dev_{id_counter}"
            devices[dev_id] = {
                "id": dev_id, "name": f"Light {l}", "type": "light", "room": room,
                "status": "off", "wattage": 15, "toggle_count": 0, 
                "activated_at": None,
                "last_changed": get_now().strftime("%I:%M %p"), "history": []
            }
            id_counter += 1

init_devices()

def get_runtime_string(activated_at_str):
    if not activated_at_str: return "0h 0m 0s"
    try:
        start_time = datetime.fromisoformat(activated_at_str)
        duration = get_now() - start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours}h {minutes}m {seconds}s"
    except Exception: return "0h 0m 0s"

def update_device_state(device_id: str):
    dev = devices[device_id]
    current_status = dev["status"]
    new_status = "on" if current_status == "off" else "off"
    time_str = get_now().strftime("%I:%M %p")
    
    dev["status"] = new_status
    dev["toggle_count"] += 1
    dev["last_changed"] = time_str
    dev["activated_at"] = get_now().isoformat() if new_status == "on" else None
    
    dev["history"].insert(0, f"{new_status.upper()} at {time_str}")
    if len(dev["history"]) > 4: dev["history"].pop()

async def auto_simulation_loop():
    try:
        while True:
            if system_config["mode"] == "auto":
                target_id = random.choice(list(devices.keys()))
                update_device_state(target_id)
            await asyncio.sleep(5)
    except asyncio.CancelledError: pass

def launch_bot_sync(python_exe):
    return subprocess.Popen([python_exe, "bot.py"], env=os.environ.copy())

@asynccontextmanager
async def lifespan(app: FastAPI):
    sim_task = asyncio.create_task(auto_simulation_loop())
    print("🤖 Launcher: Spawning independent secure bot.py process...")
    python_exe = sys.executable
    bot_process = await asyncio.to_thread(launch_bot_sync, python_exe)
    yield
    sim_task.cancel()
    print("🤖 Launcher: Shutting down background bot process...")
    try:
        bot_process.terminate()
        bot_process.wait(timeout=3)
    except Exception: pass

app = FastAPI(title="Office Cyber-Grid Core", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return {"message": "API Online."}

@app.get("/api/devices")
def get_devices():
    out_list = []
    for d in devices.values():
        d_copy = d.copy()
        d_copy["runtime_formatted"] = get_runtime_string(d["activated_at"])
        out_list.append(d_copy)
    return out_list

@app.get("/api/mode")
def get_mode(): return system_config

@app.post("/api/mode/toggle")
def toggle_mode():
    system_config["mode"] = "manual" if system_config["mode"] == "auto" else "auto"
    return system_config

@app.post("/api/toggle/{device_id}")
def toggle_device(device_id: str):
    if device_id not in devices: raise HTTPException(status_code=404, detail="Not found")
    if system_config["mode"] == "auto": raise HTTPException(status_code=400, detail="Blocked")
    update_device_state(device_id)
    d_copy = devices[device_id].copy()
    d_copy["runtime_formatted"] = get_runtime_string(d_copy["activated_at"])
    return d_copy

@app.get("/api/usage")
def get_usage():
    total_watts = sum(d["wattage"] for d in devices.values() if d["status"] == "on")
    breakdown = {room: 0 for room in rooms_list}
    for d in devices.values():
        if d["status"] == "on": breakdown[d["room"]] += d["wattage"]
    estimated_kwh = round((total_watts * 8) / 1000, 2)
    return {"total_power_watts": total_watts, "estimated_today_kwh": estimated_kwh, "room_breakdown": breakdown}

@app.get("/api/alerts")
def get_alerts():
    alerts = []
    now = get_now()
    is_after_hours = now.hour < 9 or now.hour >= 17
    
    room_devices = {room: [] for room in rooms_list}
    for d in devices.values():
        room_devices[d["room"]].append(d)
        if d["status"] == "on" and is_after_hours:
            alerts.append({
                "timestamp": now.strftime("%I:%M:%S %p"), 
                "message": f"After-hours Anomaly: {d['name']} in {d['room']} is currently ON!"
            })
            
    for room, devs in room_devices.items():
        all_on = True
        all_over_2_hours = True
        for d in devs:
            if d["status"] != "on" or not d["activated_at"]:
                all_on = False
                all_over_2_hours = False
                break
            try:
                duration = now - datetime.fromisoformat(d["activated_at"])
                if duration.total_seconds() < 7200:
                    all_over_2_hours = False
            except Exception:
                all_over_2_hours = False
                
        if all_on and all_over_2_hours:
            alerts.append({
                "timestamp": now.strftime("%I:%M:%S %p"),
                "message": f"Critical Waste: EVERY device in {room} has been ON continuously for over 2 hours!"
            })
    return alerts

@app.post("/api/bot-trigger")
async def trigger_bot_command(payload: dict):
    command_text = payload.get("command", "")
    async with aiohttp.ClientSession() as session:
        try:
            # ক্লাউড ও লোকাল উভয়ের জন্য গেটওয়ে ডাইরেক্ট রাউটিং ফিক্স
            target_host = "http://127.0.0.1:8001" if not os.getenv("RENDER") else "http://0.0.0.0:8001"
            async with session.post(f"{target_host}/webhook", json={"command": command_text}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"status": "success", "response": data.get("response", "No response text found.")}
                return {"status": "error", "message": f"Bot process returned status code {resp.status}."}
        except Exception as e:
            return {"status": "error", "message": f"Internal system routing exception: {str(e)}"}