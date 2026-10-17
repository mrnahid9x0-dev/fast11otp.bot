import asyncio
import copy
import io
import math
import re
import json
import html
import os
import httpx
import random
import string
import time
import unicodedata
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.request import HTTPXRequest

# ==================== PORT BINDING FIX FOR RENDER ====================

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("", port), SimpleHTTPRequestHandler)
    server.serve_forever()

def bind_port():
    thread = threading.Thread(target=start_server)
    thread.daemon = True
    thread.start()

# ==================== CONFIGURATION SECTION ====================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8843109906:AAFnX-5IyOSzWrDV9H1mEuD_Zf8U-8AUYJ0")
ADMINS = [7256447733]

# Data Files
USER_DATA_FILE = "users.json"
PAID_SMS_FILE = "paid_sms.json"
STATS_FILE = "user_stats.json"
BANNED_USERS_FILE = "banned_users.json"
WITHDRAW_DATA_FILE = "withdraw_requests.json"
ACTIVITY_LOGS_FILE = "activity_logs.json"
SETTINGS_FILE = "settings.json"
ACTIVE_NUMBERS_FILE = "active_numbers.json"
MANUAL_RANGES_FILE = "manual_ranges.json"

DESIGN_VERSION = 5

# ---- Ultra-Premium Bold Sans-serif Font ----
_PREMIUM_FONT = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
)

def fancy(t):
    return str(t).translate(_PREMIUM_FONT)

def info_row(icon, label, value):
    return f"{icon} <b>{label}</b> ⟡ {value}"

def card(title, rows, icon="✨"):
    """World-Class Pro Aesthetic Dashboard Design"""
    out = [f"<b>{icon} {fancy(title.upper())} {icon}</b>\n<blockquote>"]
    for r in rows:
        if r == "---":
            out.append("━━━━━━━━━━━━━━━━━━━━━")
        else:
            out.append(str(r))
    out.append("</blockquote>")
    return "\n".join(out)

def ask(title, hint, example=None):
    rows = [f"✍️ <i>{hint}</i>"]
    if example:
        rows.append(f"💡 <code>{example}</code> <i>(Tap to copy)</i>")
    return card(title, rows, icon="📝")

BANNED_MSG = card("ACCESS DENIED", ["🚫 আপনাকে আমাদের সিস্টেম থেকে ব্যান করা হয়েছে।"], icon="⛔")
MAINT_MSG = card("SYSTEM UPDATE", ["🛠 সার্ভার মেইনটেন্যান্স চলছে।", "⏳ অনুগ্রহ করে কিছুক্ষণ পর চেষ্টা করুন।"], icon="⚙️")

DEFAULT_SETTINGS = {
    "api_key": "PUT_YOUR_NEW_API_KEY_HERE",
    "base_url": "https://axnumberserver.shop/number/api",
    "otp_group_id": "-1003964441772",  
    "welcome_message": card("PREMIUM OTP HUB", [
        "🚀 <b>Welcome to the Ultimate OTP Service!</b>",
        "---",
        info_row("⚡", "Speed", "Lightning Fast Numbers"),
        info_row("💰", "Reward", "Earn crypto on every OTP"),
        info_row("💸", "Payout", "Instant Withdrawals"),
        "---",
        "👇 <b>GET NUMBER</b> বাটনে ক্লিক করে শুরু করুন"
    ], icon="💠"),
    "design_version": DESIGN_VERSION,
    "otp_group_url": "https://t.me/+bc82Xno-7YMyZDM1",
    "channel_url": "https://t.me/otprecibe",
    "support_username": "admin",
    "maintenance_mode": False,
    "min_withdraw": 0.5,
    "max_withdraw": 100.0,
    "cooldown_time": 1.0,
    "otp_reward": 0.0020,
    "refer_bonus": 0.050,
    "numbers_per_request": 1,
    "force_join_enabled": False,
    "force_join_channels": ["@otprecibe"],
    "join_alert_enabled": True,
    "auto_range": True
}

BLOCKED_SERVICES = {"verify", "twilio", "notice", "ding", "twverify", "authmsg"}
SERVICE_PRIORITY = ["whatsapp", "telegram", "facebook", "imo", "instagram", "tiktok"]

# ==================== DATA & SETTINGS ENGINE ====================

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)
        return copy.deepcopy(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        updated = False
        if data.get("design_version") != DESIGN_VERSION:
            data["welcome_message"] = DEFAULT_SETTINGS["welcome_message"]
            data["design_version"] = DESIGN_VERSION
            updated = True
        for k, v in DEFAULT_SETTINGS.items():
            if k not in data:
                data[k] = copy.deepcopy(v)
                updated = True
        if updated:
            save_settings(data)
        return data
    except Exception:
        return copy.deepcopy(DEFAULT_SETTINGS)

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def load_json(filepath, default_val):
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            json.dump(default_val, f)
        return default_val
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception:
        return default_val

def save_json(filepath, data):
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving {filepath}: {e}")

# ==================== USER & BALANCE MANAGEMENT ====================

def get_user(uid, username=None, full_name=None):
    uid_str = str(uid)
    data = load_json(USER_DATA_FILE, {})
    if uid_str not in data:
        data[uid_str] = {
            "user_id": uid_str,
            "balance": 0.0,
            "username": username,
            "full_name": full_name,
            "referrals": 0,
            "referral_earnings": 0.0,
            "referred_by": None,
            "withdrawal_method": None
        }
        save_json(USER_DATA_FILE, data)
    else:
        updated = False
        if username and data[uid_str].get("username") != username:
            data[uid_str]["username"] = username
            updated = True
        if full_name and data[uid_str].get("full_name") != full_name:
            data[uid_str]["full_name"] = full_name
            updated = True
        if updated:
            save_json(USER_DATA_FILE, data)
    return data[uid_str]

async def update_db_balance(uid, amount):
    uid_str = str(uid)
    data = load_json(USER_DATA_FILE, {})
    if uid_str in data:
        data[uid_str]["balance"] = round(data[uid_str].get("balance", 0.0) + amount, 4)
        save_json(USER_DATA_FILE, data)
        return data[uid_str]["balance"]
    return 0.0

def is_admin(user_id):
    return user_id in ADMINS

def is_user_banned(uid):
    banned_list = load_json(BANNED_USERS_FILE, [])
    return str(uid) in banned_list

def ban_user(uid):
    banned_list = load_json(BANNED_USERS_FILE, [])
    uid_str = str(uid)
    if uid_str not in banned_list:
        banned_list.append(uid_str)
        save_json(BANNED_USERS_FILE, banned_list)
        return True
    return False

def unban_user(uid):
    banned_list = load_json(BANNED_USERS_FILE, [])
    uid_str = str(uid)
    if uid_str in banned_list:
        banned_list.remove(uid_str)
        save_json(BANNED_USERS_FILE, banned_list)
        return True
    return False

# ==================== UTILITY FUNCTIONS ====================

def strip_html_tags(text: str) -> str:
    return re.sub(r'<[^>]*>', '', str(text))

def unstyle_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFKC', str(text))

def normalize_number(num):
    return re.sub(r'\D', '', str(num))

def mask_number(num):
    num_str = str(num).replace('+', '').replace(' ', '').strip()
    if len(num_str) >= 8:
        return f"{num_str[:4]}••••{num_str[-4:]}"
    return num_str

def format_balance(balance):
    return f"{balance:.4f}"

def generate_payment_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def extract_otp(text):
    if not text or text == "No Content":
        return "N/A"
    text_clean = str(text).strip()
    
    # 1. Instagram Specific Logic
    ig_match = re.search(r'(?:ig-|instagram code\s*[:\-]?\s*)(\d{6})', text_clean, re.IGNORECASE)
    if ig_match: return ig_match.group(1)
    
    ig_match_2 = re.search(r'\b(\d{6})\b\s+(?:is your )?instagram', text_clean, re.IGNORECASE)
    if ig_match_2: return ig_match_2.group(1)

    # 2. WhatsApp Specific Logic
    wa_match = re.search(r'whatsapp.*?(\d{3}[\s-]?\d{3})', text_clean, re.IGNORECASE)
    if wa_match: return wa_match.group(1).replace('-', '').replace(' ', '')
    
    # 3. Generic Labels
    label_match = re.search(r'(?:code|otp|verify|verification|pin|confirmation|kod|passcode)[\s:-]+([a-zA-Z0-9]{3,10})\b', text_clean, re.IGNORECASE)
    if label_match:
        return label_match.group(1).strip()
        
    # 4. Fallback matches
    spaced_otp = re.search(r'\b(\d{3}[\s-]\d{3})\b', text_clean)
    if spaced_otp:
        return spaced_otp.group(1)
    digit_match = re.search(r'\b(\d{4,8})\b', text_clean)
    if digit_match:
        return digit_match.group(1)
        
    return "N/A"

def load_country_map(filename="Country.txt"):
    country_map = {}
    if not os.path.exists(filename):
        return country_map
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("|")
                    if len(parts) >= 3:
                        prefix = parts[0].strip()
                        flag = parts[1].strip()
                        name = parts[2].strip()
                        country_map[prefix] = (flag, name)
    except Exception:
        pass
    return country_map

def get_country_info(number):
    clean_num = normalize_number(str(number).split('|')[-1])
    country_map = load_country_map()
    sorted_prefixes = sorted(country_map.keys(), key=len, reverse=True)
    for prefix in sorted_prefixes:
        if clean_num.startswith(prefix):
            return country_map[prefix]
    return "🌐", "Global"

def detect_service(full_sms):
    if not full_sms:
        return "SMS SERVICE"
    sms_lower = full_sms.lower()
    if "facebook" in sms_lower or "fb" in sms_lower:
        return "FACEBOOK"
    if "instagram" in sms_lower or "insta" in sms_lower or "ig-" in sms_lower:
        return "INSTAGRAM"
    if "whatsapp" in sms_lower:
        return "WHATSAPP"
    if "telegram" in sms_lower or "tg" in sms_lower:
        return "TELEGRAM"
    if "tiktok" in sms_lower:
        return "TIKTOK"
    if "uber" in sms_lower:
        return "UBER"
    if "discord" in sms_lower:
        return "DISCORD"
    return "SMS SERVICE"

def clean_range_id(range_str: str) -> str:
    if not range_str:
        return ""
    number_str = str(range_str).split('|')[-1].strip()
    return re.sub(r'[^\w]', '', number_str)

def get_service_icon(app_name):
    name = str(app_name).lower().strip()
    if "whatsapp" in name: return "💬"      
    if "facebook" in name or "fb" in name: return "🌐"  
    if "telegram" in name or "tg" in name: return "🚀"  
    if "instagram" in name or "insta" in name: return "📸" 
    if "tiktok" in name: return "🎵"        
    if "imo" in name: return "🗨️"         
    if "alipay" in name: return "💳"      
    if "bigolive" in name: return "📹"    
    if "twitter" in name or "x" in name: return "🐦"
    if "google" in name: return "🔍"
    if "microsoft" in name: return "🪟"
    if "netflix" in name: return "🎬"
    return "💠"

def get_service_percentage(app_name):
    name = str(app_name).lower().strip()
    if "whatsapp" in name: return "98%"
    if "facebook" in name or "fb" in name: return "95%"
    if "telegram" in name or "tg" in name: return "92%"
    if "imo" in name: return "90%"
    return None

def service_button_label(app_name):
    icon = get_service_icon(app_name)
    pct = get_service_percentage(app_name)
    if pct:
        return f"{icon} {app_name} ⟡ {pct}"
    return f"{icon} {app_name}"

def is_valid_service(name):
    n = str(name).lower().strip()
    if not n or n in BLOCKED_SERVICES:
        return False
    if re.fullmatch(r'[\d\s+\-()]+', n):
        return False
    return True

def service_sort_key(name):
    n = str(name).lower()
    for i, key in enumerate(SERVICE_PRIORITY):
        if key in n:
            return (i, n)
    return (len(SERVICE_PRIORITY), n)

def make_bar(pct, size=10):
    filled = max(0, min(size, round(pct / 100 * size)))
    return "▰" * filled + "▱" * (size - filled)

# ==================== STATS & LOGS ENGINE ====================

def add_number_taken(uid, count=1):
    uid = str(uid)
    stats = load_json(STATS_FILE, {})
    if uid not in stats:
        stats[uid] = {"numbers_taken": [], "otps_received": []}
    now = datetime.now().isoformat()
    for _ in range(count):
        stats[uid]["numbers_taken"].append(now)
    save_json(STATS_FILE, stats)

def add_otp_received(uid):
    uid = str(uid)
    stats = load_json(STATS_FILE, {})
    if uid not in stats:
        stats[uid] = {"numbers_taken": [], "otps_received": []}
    stats[uid]["otps_received"].append(datetime.now().isoformat())
    save_json(STATS_FILE, stats)

def log_global_activity(uid, action, details):
    logs = load_json(ACTIVITY_LOGS_FILE, [])
    now = datetime.now()
    log_entry = {
        "uid": str(uid),
        "action": action,
        "details": details,
        "timestamp": now.isoformat()
    }
    logs.append(log_entry)
    save_json(ACTIVITY_LOGS_FILE, logs)

# ==================== BUTTON LABELS (DESIGN) ====================
BTN_GET     = "🚀 𝗚𝗘𝗧 𝗡𝗨𝗠𝗕𝗘𝗥"
BTN_BALANCE = "💼 𝗪𝗔𝗟𝗟𝗘𝗧"
BTN_REFER   = "🎁 𝗥𝗘𝗙𝗘𝗥 𝗔𝗡𝗗 𝗘𝗔𝗥𝗡"
BTN_TRAFFIC = "📡 𝗟𝗜𝗩𝗘 𝗧𝗥𝗔𝗙𝗙𝗜𝗖"
BTN_LEADER  = "👑 𝗟𝗘𝗔𝗗𝗘𝗥𝗕𝗢𝗔𝗥𝗗"
BTN_SUPPORT = "🎧 𝗦𝗨𝗣𝗣𝗢𝗥𝗧"
BTN_ADMIN   = "👨‍💻 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟"

USER_MENU_TEXTS = {
    BTN_GET, "GET NUMBER", "🚀 GET NUMBER", "📱 GET NUMBER",
    BTN_BALANCE, "💵 BALANCE", "BALANCE", "💼 WALLET", "💳 WALLET",
    BTN_REFER, "🎁 REFER & EARN", "REFER & EARN", "🎁 REFER AND EARN",
    BTN_TRAFFIC, "📊 TRAFFIC", "TRAFFIC", "📡 LIVE TRAFFIC",
    BTN_LEADER, "🏆 LEADERBOARD", "LEADERBOARD", "👑 LEADERBOARD",
    BTN_SUPPORT, "💬 SUPPORT", "SUPPORT", "🎧 SUPPORT",
    BTN_ADMIN, "⚙️ ADMIN PANEL", "ADMIN PANEL", "👨‍💻 ADMIN PANEL",
}

ADMIN_MENU_TEXTS = {
    "⚙️ SYSTEM CONFIG", "💵 USER & BALANCE", "🔒 SECURITY & JOIN", "📢 NOTICE & B-CAST",
    "🔙 BACK TO MAIN", "BACK TO MAIN", "🔑 SET API KEY", "🌐 SET API BASE URL",
    "📢 SET OTP CHANNEL ID", "💰 SET WITHDRAW LIMITS", "🎁 SET REFER BONUS", "⏱ SET COOLDOWN",
    "🚫 TOGGLE MAINTENANCE", "🔙 BACK TO ADMIN", "BACK TO ADMIN", "➕ ADD BALANCE",
    "➖ REMOVE BALANCE", "💬 DIRECT MSG USER", "🔍 SEARCH BY USERNAME", "📜 ALL USER BALANCE",
    "🚫 BAN USER", "✅ UNBAN USER", "📢 FORCE CHANNELS", "📜 BAN USER LIST",
    "➕ ADD CHANNEL", "➖ DELETE CHANNEL", "🔙 BACK TO SECURITY", "📢 BROADCAST NOTICE",
    "📝 SET WELCOME MSG", "💬 SET SUPPORT USERNAME", "🔗 SET CHANNEL LINK",
}

MENU_TEXTS = USER_MENU_TEXTS | ADMIN_MENU_TEXTS

# ==================== KEYBOARDS ====================

def rkbtn(text: str, style: str = None):
    return KeyboardButton(text=fancy(text))

def rbtn(text: str, style: str = None, callback_data: str = None, url: str = None):
    return InlineKeyboardButton(text=text, callback_data=callback_data, url=url)

def copybtn(text: str, value):
    return InlineKeyboardButton(text=text, api_kwargs={"copy_text": {"text": str(value)}})

async def safe_send(bot, chat_id, text, kb=None):
    try:
        return await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        if kb is not None:
            try:
                return await bot.send_message(chat_id, text, parse_mode="HTML")
            except Exception as e2:
                print(f"[safe_send] {chat_id}: {e2}")
        else:
            print(f"[safe_send] {chat_id}: {e}")
    return None

def main_keyboard(user_id):
    keyboard = [
        [rkbtn(BTN_GET)],
        [rkbtn(BTN_BALANCE), rkbtn(BTN_REFER)],
        [rkbtn(BTN_TRAFFIC), rkbtn(BTN_LEADER)],
    ]
    if is_admin(user_id):
        keyboard.append([rkbtn(BTN_SUPPORT), rkbtn(BTN_ADMIN)])
    else:
        keyboard.append([rkbtn(BTN_SUPPORT)])
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="⚡ Select an option below..."
    )

def admin_main_keyboard():
    keyboard = [
        [rkbtn("⚙️ SYSTEM CONFIG"), rkbtn("💵 USER & BALANCE")],
        [rkbtn("🔒 SECURITY & JOIN"), rkbtn("📢 NOTICE & B-CAST")],
        [rkbtn("🔙 BACK TO MAIN")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="👨‍💻 Admin Control Center")

def admin_system_config_keyboard():
    keyboard = [
        [rkbtn("🔑 SET API KEY"), rkbtn("🌐 SET API BASE URL")],
        [rkbtn("📢 SET OTP CHANNEL ID"), rkbtn("💰 SET WITHDRAW LIMITS")],
        [rkbtn("🎁 SET REFER BONUS"), rkbtn("⏱ SET COOLDOWN")],
        [rkbtn("🚫 TOGGLE MAINTENANCE"), rkbtn("🔙 BACK TO ADMIN")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_user_balance_keyboard():
    keyboard = [
        [rkbtn("➕ ADD BALANCE"), rkbtn("➖ REMOVE BALANCE")],
        [rkbtn("💬 DIRECT MSG USER"), rkbtn("🔍 SEARCH BY USERNAME")],
        [rkbtn("📜 ALL USER BALANCE"), rkbtn("🔙 BACK TO ADMIN")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_security_join_keyboard():
    keyboard = [
        [rkbtn("🚫 BAN USER"), rkbtn("✅ UNBAN USER")],
        [rkbtn("📢 FORCE CHANNELS"), rkbtn("📜 BAN USER LIST")],
        [rkbtn("🔙 BACK TO ADMIN")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_force_channel_keyboard():
    keyboard = [
        [rkbtn("➕ ADD CHANNEL"), rkbtn("➖ DELETE CHANNEL")],
        [rkbtn("🔙 BACK TO SECURITY")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_notice_bcast_keyboard():
    keyboard = [
        [rkbtn("📢 BROADCAST NOTICE"), rkbtn("📝 SET WELCOME MSG")],
        [rkbtn("💬 SET SUPPORT USERNAME"), rkbtn("🔗 SET CHANNEL LINK")],
        [rkbtn("🔙 BACK TO ADMIN")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup([[rkbtn("❌ CANCEL")]], resize_keyboard=True)

def build_service_keyboard(top_ranges):
    buttons = []
    row = []
    for app_name in top_ranges.keys():
        row.append(rbtn(service_button_label(app_name), callback_data=f"sel_app_{app_name}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

SERVICE_TITLE = card("SELECT SERVICE", ["🔥 Top Demanded Services", "👇 Select a service below:"], icon="⚡")

# ==================== ASYNC CLIENT & QUEUE ====================

client_async = httpx.AsyncClient(timeout=10.0, verify=False, headers={"User-Agent": "Mozilla/5.0"})
request_queue = asyncio.Queue()
active_numbers = load_json(ACTIVE_NUMBERS_FILE, {})
last_range = {}
last_app = {}
last_request_time = {}
_bg_tasks = set()

def check_cooldown(uid):
    try:
        cd = float(load_settings().get("cooldown_time", 1.0))
    except Exception:
        cd = 1.0
    now = time.time()
    last = last_request_time.get(uid, 0)
    if now - last < cd:
        return round(cd - (now - last), 1)
    last_request_time[uid] = now
    return 0

def prune_active_numbers(max_age_hours=24):
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    removed = False
    for num in list(active_numbers.keys()):
        try:
            ts = datetime.fromisoformat(active_numbers[num].get("timestamp"))
            if ts < cutoff:
                del active_numbers[num]
                removed = True
        except Exception:
            del active_numbers[num]
            removed = True
    if removed:
        save_json(ACTIVE_NUMBERS_FILE, active_numbers)

# ==================== API FUNCTIONS ====================

async def fetch_top_ranges():
    settings = load_settings()
    api_key = settings.get("api_key")
    base_url = settings.get("base_url").rstrip('/')
    
    try:
        url = f"{base_url}/liveaccess?api_key={api_key}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
        r = await client_async.get(url, headers=headers, timeout=10.0)
        
        if r.status_code != 200:
            return None, f"HTTP Status {r.status_code}: Server returned HTML Error"
            
        try:
            data = r.json()
        except Exception:
            return None, f"HTML Page Received instead of JSON"
        
        top_ranges = {}
        services_list = []

        if isinstance(data, dict):
            inner_data = data.get("data")
            if isinstance(inner_data, dict):
                services_list = inner_data.get("services") or inner_data.get("ranges") or []
            elif isinstance(inner_data, list):
                services_list = inner_data
            else:
                services_list = data.get("services") or data.get("ranges") or []

        if isinstance(services_list, list):
            for s_item in services_list:
                if isinstance(s_item, dict):
                    app_raw = s_item.get("sid") or s_item.get("service") or s_item.get("app") or "Unknown"
                    rng_list = s_item.get("ranges", [])
                    app_name = app_raw.strip().title()
                    if app_name not in top_ranges:
                        top_ranges[app_name] = []
                    for rng in rng_list:
                        if rng and rng not in top_ranges[app_name]:
                            top_ranges[app_name].append(rng)
                            
        elif isinstance(services_list, dict):
            for app_raw, rng_list in services_list.items():
                app_name = app_raw.strip().title()
                if app_name not in top_ranges:
                    top_ranges[app_name] = []
                for rng in rng_list:
                    if rng and rng not in top_ranges[app_name]:
                        top_ranges[app_name].append(rng)

        filtered = {k: v for k, v in top_ranges.items() if is_valid_service(k) and v}
        ordered = dict(sorted(filtered.items(), key=lambda kv: service_sort_key(kv[0])))

        return ordered, None
    except Exception as e:
        return None, str(e)

async def fetch_number_async(range_str):
    try:
        settings = load_settings()
        api_key = settings.get("api_key")
        base_url = settings.get("base_url").rstrip('/')
        url = f"{base_url}/getnumber"
        clean_rid = clean_range_id(range_str)
        
        params = {
            "api_key": api_key,
            "rid": clean_rid,
            "national": 1,
            "remove_plus": 1
        }
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        r = await client_async.get(url, params=params, headers=headers, timeout=10.0)
        
        try:
            data = r.json()
        except Exception:
            return None
            
        if isinstance(data, dict) and data.get("status") == "success":
            return data.get("number") or data.get("phone")
    except Exception as e:
        pass
    return None

# ==================== WORKER TASK ====================

async def worker():
    while True:
        task = await request_queue.get()
        try:
            uid = task['uid']
            chat_id = task['chat_id']
            context = task['context']
            range_text = task['range_text']
            app_name = task.get('app')
            
            status_msg = await context.bot.send_message(chat_id=chat_id, text=card("SEARCHING", ["🔍 Generating best number...", f"<code>[{make_bar(50)}]</code>"], icon="⏳"), parse_mode="HTML")
            result = await fetch_number_async(range_text)
            
            if not result:
                await status_msg.edit_text(card("NO NUMBER", ["❌ Out of stock right now.", "🔄 Please try again shortly."], icon="⚠️"), parse_mode="HTML")
            else:
                clean_num = normalize_number(result)
                active_numbers[clean_num] = {"uid": uid, "range": range_text, "timestamp": datetime.now().isoformat()}
                save_json(ACTIVE_NUMBERS_FILE, active_numbers)
                add_number_taken(uid, 1)
                
                flag, c_name = get_country_info(clean_num)
                settings = load_settings()
                otp_target = settings.get("otp_group_id", "")
                otp_link = settings.get("channel_url")
                
                if str(otp_target).startswith("https://t.me/"):
                    otp_link = otp_target
                elif str(otp_target).startswith("@"):
                    otp_link = f"https://t.me/{str(otp_target)[1:]}"
                else:
                    try:
                        chat = await context.bot.get_chat(otp_target)
                        otp_link = f"https://t.me/{chat.username}" if chat.username else (chat.invite_link or await context.bot.export_chat_invite_link(otp_target))
                    except Exception:
                        otp_link = settings.get("channel_url")

                rows = []
                if app_name:
                    rows.append(info_row("📲", "Service", html.escape(str(app_name))))
                rows.append(info_row("🌍", "Country", f"{flag} {html.escape(str(c_name))}"))
                rows.append(info_row("📞", "Number", f"<code>+{clean_num}</code> <i>(Tap to copy)</i>"))
                pct = get_service_percentage(app_name) if app_name else None
                if pct:
                    rows.append(info_row("🎯", "Success Rate", pct))
                rows.append("---")
                rows.append("⏳ <i>Awaiting SMS... OTP will be delivered here.</i>")
                txt = card("NUMBER READY", rows, icon="✨")

                action_row = [rbtn("♻️ CHANGE NUMBER", callback_data="same_range")]
                if otp_link:
                    action_row.append(rbtn("📡 LIVE PANEL", url=otp_link))
                
                kb_full = InlineKeyboardMarkup([[copybtn("📋 𝗖𝗢𝗣𝗬 𝗡𝗨𝗠𝗕𝗘𝗥", f"+{clean_num}")], action_row])
                kb_plain = InlineKeyboardMarkup([action_row])
                
                try:
                    await status_msg.edit_text(txt, parse_mode="HTML", reply_markup=kb_full)
                except Exception:
                    await status_msg.edit_text(txt, parse_mode="HTML", reply_markup=kb_plain)
        except Exception:
            pass
        finally:
            request_queue.task_done()

# ==================== AUTO MONITOR LOOP ====================

async def monitor_loop(app):
    tick = 0
    last_err_time = 0
    while True:
        try:
            tick += 1
            if tick % 600 == 0:
                prune_active_numbers()

            settings = load_settings()
            api_key = settings.get("api_key")
            base_url = settings.get("base_url").rstrip('/')
            otp_target = settings.get("otp_group_id")
            otp_reward = settings.get("otp_reward", 0.0020)
            
            if api_key:
                r = await client_async.get(f"{base_url}/success_otp?api_key={api_key}")
                res = r.json()
                
                otps = []
                if isinstance(res, dict):
                    otps = res.get("data") or res.get("otps") or []
                elif isinstance(res, list):
                    otps = res

                if otps:
                    paid_data = load_json(PAID_SMS_FILE, {})
                    for otp in otps:
                        if not isinstance(otp, dict):
                            continue
                        num = normalize_number(otp.get("number") or otp.get("phone") or otp.get("mobile") or "")
                        
                        raw_code = otp.get("code") or otp.get("otp") or otp.get("otp_code") or ""
                        otp_code = str(raw_code).strip() if raw_code else ""

                        raw_sms = otp.get("message") or otp.get("sms") or otp.get("text") or otp.get("msg") or ""
                        full_sms = str(raw_sms).strip()

                        if not otp_code and full_sms:
                            otp_code = extract_otp(full_sms)

                        if not full_sms:
                            full_sms = f"Your verification code is: {otp_code}" if otp_code else "No SMS Content"

                        if not otp_code:
                            otp_code = "N/A"

                        otp_id = str(otp.get("otp_id") or otp.get("id") or f"{num}_{otp_code}")

                        if num in active_numbers and otp_id not in paid_data:
                            details = active_numbers[num]
                            user_id = details["uid"]
                            paid_data[otp_id] = True
                            save_json(PAID_SMS_FILE, paid_data)
                            
                            await update_db_balance(user_id, otp_reward)
                            add_otp_received(user_id)
                            log_global_activity(user_id, "OTP_RECEIVED", {"number": num, "otp": otp_code, "sms": full_sms})
                            
                            flag, c_name = get_country_info(num)
                            api_service = otp.get("service") or otp.get("app") or ""
                            service = str(api_service).upper() if api_service else detect_service(full_sms)
                            masked_num = mask_number(num)
                            
                            user_rows = [
                                info_row("📞", "Number", f"<code>+{num}</code>"),
                                info_row("🔑", "OTP Code", f"<code>{html.escape(otp_code)}</code> <i>(Tap to copy)</i>"),
                                info_row("💰", "Reward", f"<code>+{otp_reward:.4f}$</code>"),
                                "---",
                                f"💬 <b>SMS Content:</b>\n<code>{html.escape(full_sms)}</code>",
                            ]
                            user_kb = InlineKeyboardMarkup([[copybtn("📋 𝗖𝗢𝗣𝗬 𝗢𝗧𝗣", otp_code)]]) if otp_code != "N/A" else None
                            await safe_send(app.bot, user_id, card("OTP RECEIVED", user_rows, icon="🎉"), user_kb)

                            group_rows = [
                                info_row("⚙️", "Service", f"<b>{html.escape(service)}</b>"),
                                info_row("🌍", "Country", f"{flag} {html.escape(str(c_name))}"),
                                info_row("📞", "Number", f"<code>{masked_num}</code>"),
                                info_row("🔑", "OTP Code", f"<code>{html.escape(otp_code)}</code>"),
                            ]
                            join_url = settings.get("channel_url")
                            group_kb = InlineKeyboardMarkup([[rbtn("💎 JOIN BOT", url=f"https://t.me/{app.bot.username}")]]) if app.bot.username else None
                            await safe_send(app.bot, otp_target, card("LIVE OTP ALERT", group_rows, icon="🚀"), group_kb)

        except Exception as e:
            if time.time() - last_err_time > 60:
                last_err_time = time.time()
        await asyncio.sleep(1.0)

# ==================== FORCE JOIN ====================
async def is_user_member(bot, user_id, channel):
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

async def get_not_joined(bot, uid):
    if is_admin(uid):
        return []
    settings = load_settings()
    if not settings.get("force_join_enabled", False):
        return []
    channels = settings.get("force_join_channels", [])
    not_joined = []
    for ch in channels:
        if not await is_user_member(bot, uid, ch):
            not_joined.append(ch)
    return not_joined

async def check_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    uid = update.effective_user.id
    not_joined = await get_not_joined(context.bot, uid)

    if not_joined:
        buttons = []
        for ch in not_joined:
            clean_ch = ch.replace("@", "")
            buttons.append([rbtn(f"📢 Join {ch}", url=f"https://t.me/{clean_ch}")])
        buttons.append([rbtn("🔄 Verify Join", callback_data="check_join")])

        msg = card("ACCESS LOCKED", ["🔐 <b>বটটি ব্যবহার করতে আমাদের চ্যানেলে জয়েন করুন</b>", "👇 জয়েন করে Verify বাটনে চাপুন"], icon="🔒")
        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        elif update.callback_query:
            await update.callback_query.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return False

    return True

# ==================== COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if is_user_banned(uid):
        await update.message.reply_text(BANNED_MSG, parse_mode="HTML")
        return
    if load_settings().get("maintenance_mode", False) and not is_admin(uid):
        await update.message.reply_text(MAINT_MSG, parse_mode="HTML")
        return
    if not await check_force_sub(update, context):
        return

    username = update.effective_user.username
    full_name = update.effective_user.full_name
    
    users_db = load_json(USER_DATA_FILE, {})
    is_new = str(uid) not in users_db
    get_user(uid, username, full_name)
    
    if context.args and is_new:
        referrer_id = str(context.args[0])
        users_db = load_json(USER_DATA_FILE, {})
        if referrer_id != str(uid) and referrer_id in users_db and str(uid) in users_db:
            settings = load_settings()
            bonus = settings.get("refer_bonus", 0.05)
            
            users_db[str(uid)]["referred_by"] = referrer_id
            ref_user = users_db[referrer_id]
            ref_user["balance"] = round(ref_user.get("balance", 0.0) + bonus, 4)
            ref_user["referrals"] = ref_user.get("referrals", 0) + 1
            ref_user["referral_earnings"] = round(ref_user.get("referral_earnings", 0.0) + bonus, 4)
            save_json(USER_DATA_FILE, users_db)
            
            try:
                await context.bot.send_message(
                    int(referrer_id),
                    card("NEW REFERRAL", [info_row("👤", "User Joined", html.escape(full_name or 'N/A')), info_row("💰", "Bonus Earned", f"<code>+{bonus}$</code>")], icon="🎁"),
                    parse_mode="HTML"
                )
            except Exception:
                pass

    settings = load_settings()
    await update.message.reply_text(settings.get("welcome_message"), parse_mode="HTML", reply_markup=main_keyboard(uid))

# ==================== ADMIN EDIT HANDLER ====================

async def handle_admin_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_mode: str, raw_text: str):
    settings = load_settings()

    if edit_mode == "api_key":
        settings["api_key"] = raw_text
        save_settings(settings)
        await update.message.reply_text("✅ API Key updated!", reply_markup=admin_system_config_keyboard())
    elif edit_mode == "base_url":
        settings["base_url"] = raw_text
        save_settings(settings)
        await update.message.reply_text("✅ API Base URL updated!", reply_markup=admin_system_config_keyboard())
    elif edit_mode == "otp_channel":
        settings["otp_group_id"] = raw_text
        save_settings(settings)
        await update.message.reply_text(f"✅ OTP Channel ID set to: <code>{html.escape(raw_text)}</code>", parse_mode="HTML", reply_markup=admin_system_config_keyboard())
    elif edit_mode == "withdraw_limits":
        parts = raw_text.split()
        if len(parts) == 2:
            mn, mx = float(parts[0]), float(parts[1])
            if not (math.isfinite(mn) and math.isfinite(mx)) or mn < 0 or mx < mn:
                await update.message.reply_text("❌ Invalid limits! Example: 0.5 100", reply_markup=admin_system_config_keyboard())
                return
            settings["min_withdraw"] = mn
            settings["max_withdraw"] = mx
            save_settings(settings)
            await update.message.reply_text(f"✅ Limits set: Min {mn}$ | Max {mx}$", reply_markup=admin_system_config_keyboard())
        else:
            await update.message.reply_text("❌ Invalid format! Example: 0.5 100", reply_markup=admin_system_config_keyboard())
    elif edit_mode == "refer_bonus":
        val = float(raw_text)
        if not math.isfinite(val) or val < 0:
            raise ValueError("bad bonus")
        settings["refer_bonus"] = val
        save_settings(settings)
        await update.message.reply_text("✅ Referral bonus updated!", reply_markup=admin_system_config_keyboard())
    elif edit_mode == "cooldown":
        val = float(raw_text)
        if not math.isfinite(val) or val < 0:
            raise ValueError("bad cooldown")
        settings["cooldown_time"] = val
        save_settings(settings)
        await update.message.reply_text("✅ Cooldown updated!", reply_markup=admin_system_config_keyboard())
    elif edit_mode == "welcome":
        settings["welcome_message"] = raw_text
        save_settings(settings)
        await update.message.reply_text("✅ Welcome Message updated!", reply_markup=admin_notice_bcast_keyboard())
    elif edit_mode == "support":
        settings["support_username"] = raw_text.replace("@", "")
        save_settings(settings)
        await update.message.reply_text("✅ Support username updated!", reply_markup=admin_notice_bcast_keyboard())
    elif edit_mode == "channel_link":
        settings["channel_url"] = raw_text
        save_settings(settings)
        await update.message.reply_text("✅ Channel link updated!", reply_markup=admin_notice_bcast_keyboard())
    elif edit_mode in ("add_balance", "remove_balance"):
        parts = raw_text.split()
        if len(parts) == 2 and parts[0].isdigit():
            t_uid, amt = parts[0], float(parts[1])
            if not math.isfinite(amt) or amt <= 0:
                raise ValueError("bad amount")
            users = load_json(USER_DATA_FILE, {})
            if t_uid not in users:
                await update.message.reply_text("❌ User not found!", reply_markup=admin_user_balance_keyboard())
                return
            if edit_mode == "add_balance":
                new_b = await update_db_balance(t_uid, amt)
                await update.message.reply_text(f"✅ Added {amt}$ to User {t_uid}. New Balance: {new_b}$", reply_markup=admin_user_balance_keyboard())
            else:
                new_b = await update_db_balance(t_uid, -amt)
                await update.message.reply_text(f"✅ Removed {amt}$ from User {t_uid}. New Balance: {new_b}$", reply_markup=admin_user_balance_keyboard())
        else:
            await update.message.reply_text("❌ Format: USER_ID AMOUNT", reply_markup=admin_user_balance_keyboard())
    elif edit_mode == "ban_user":
        target = raw_text.strip()
        if not target.isdigit():
            await update.message.reply_text("❌ Send a valid numeric USER_ID!", reply_markup=admin_security_join_keyboard())
        elif int(target) in ADMINS:
            await update.message.reply_text("❌ You can't ban an admin!", reply_markup=admin_security_join_keyboard())
        elif ban_user(target):
            await update.message.reply_text(f"✅ User {target} banned!", reply_markup=admin_security_join_keyboard())
        else:
            await update.message.reply_text("❌ User already banned!", reply_markup=admin_security_join_keyboard())
    elif edit_mode == "unban_user":
        target = raw_text.strip()
        if unban_user(target):
            await update.message.reply_text(f"✅ User {target} unbanned!", reply_markup=admin_security_join_keyboard())
        else:
            await update.message.reply_text("❌ This user is not banned!", reply_markup=admin_security_join_keyboard())
    elif edit_mode == "search_username":
        uname = raw_text.strip().lstrip("@").lower()
        users = load_json(USER_DATA_FILE, {})
        found = [u for u in users.values() if (u.get("username") or "").lower() == uname]
        if not found:
            await update.message.reply_text("❌ No user found with that username.", reply_markup=admin_user_balance_keyboard())
        else:
            lines = []
            for u in found:
                lines.append(
                    f"👤 <b>{html.escape(u.get('full_name') or 'N/A')}</b>\n"
                    f"🆔 <code>{u.get('user_id')}</code>\n"
                    f"💰 Balance: <code>{u.get('balance', 0.0):.4f}$</code>\n"
                    f"👥 Referrals: {u.get('referrals', 0)}"
                )
            await update.message.reply_text(f"🔍 <b>SEARCH RESULT</b>\n━━━━━━━━━━━━━━━━━━\n" + "\n\n".join(lines), parse_mode="HTML", reply_markup=admin_user_balance_keyboard())
    elif edit_mode == "add_force_channel":
        ch = raw_text.strip()
        channels = settings.get("force_join_channels", [])
        if ch not in channels:
            channels.append(ch)
            settings["force_join_channels"] = channels
            settings["force_join_enabled"] = True
            save_settings(settings)
            await update.message.reply_text(f"✅ Channel <code>{html.escape(ch)}</code> যোগ করা হয়েছে!", parse_mode="HTML", reply_markup=admin_force_channel_keyboard())
        else:
            await update.message.reply_text("❌ এই চ্যানেলটি আগেই তালিকায় রয়েছে!", reply_markup=admin_force_channel_keyboard())
    elif edit_mode == "del_force_channel":
        ch = raw_text.strip()
        channels = settings.get("force_join_channels", [])
        if ch in channels:
            channels.remove(ch)
            settings["force_join_channels"] = channels
            if not channels:
                settings["force_join_enabled"] = False
            save_settings(settings)
            await update.message.reply_text(f"✅ Channel <code>{html.escape(ch)}</code> তালিকা থেকে মুছে ফেলা হয়েছে!", parse_mode="HTML", reply_markup=admin_force_channel_keyboard())
        else:
            await update.message.reply_text("❌ চ্যানেলটি তালিকায় পাওয়া যায়নি!", reply_markup=admin_force_channel_keyboard())
    elif edit_mode == "direct_msg":
        parts = raw_text.split(maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit():
            try:
                await context.bot.send_message(int(parts[0]), card("MESSAGE FROM ADMIN", [html.escape(parts[1])], icon="💬"), parse_mode="HTML")
                await update.message.reply_text("✅ Message sent!", reply_markup=admin_user_balance_keyboard())
            except Exception as e:
                await update.message.reply_text(f"❌ Failed: {e}", reply_markup=admin_user_balance_keyboard())
        else:
            await update.message.reply_text("❌ Format: USER_ID MESSAGE", reply_markup=admin_user_balance_keyboard())
    elif edit_mode == "broadcast":
        users = load_json(USER_DATA_FILE, {})
        succ, fail = 0, 0
        msg = await update.message.reply_text("📢 Broadcasting started...")
        for u_id in users.keys():
            try:
                await context.bot.send_message(int(u_id), card("ANNOUNCEMENT", [raw_text], icon="📢"), parse_mode="HTML")
                succ += 1
            except Exception:
                fail += 1
            await asyncio.sleep(0.04)
        await msg.edit_text(f"✅ Broadcast complete!\nSuccess: {succ} | Failed: {fail}")
        await update.message.reply_text("📢 Done.", reply_markup=admin_notice_bcast_keyboard())

# ==================== MAIN MESSAGE HANDLER ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    uid = update.effective_user.id
    raw_text = update.message.text.strip()
    text = unstyle_text(raw_text)

    if is_user_banned(uid):
        await update.message.reply_text(BANNED_MSG, parse_mode="HTML")
        return
    if load_settings().get("maintenance_mode", False) and not is_admin(uid):
        await update.message.reply_text(MAINT_MSG, parse_mode="HTML")
        return
    if not await check_force_sub(update, context):
        return

    if text == "❌ CANCEL":
        context.user_data.clear()
        await update.message.reply_text(card("CANCELLED", ["↩️ অ্যাকশন বাতিল করা হয়েছে"], icon="✖️"), parse_mode="HTML", reply_markup=main_keyboard(uid))
        return

    if text in MENU_TEXTS:
        context.user_data.pop("withdraw_mode", None)
        context.user_data["admin_edit_mode"] = None

    # --- WITHDRAW INPUT MODE ---
    w_mode = context.user_data.get("withdraw_mode")
    if w_mode == "amount":
        try:
            amount = float(text)
        except ValueError:
            await update.message.reply_text("❌ Send a valid numeric amount!", reply_markup=cancel_keyboard())
            return
        settings = load_settings()
        min_w, max_w = settings.get("min_withdraw", 0.5), settings.get("max_withdraw", 100.0)
        u_bal = get_user(uid)["balance"]

        if not math.isfinite(amount) or amount <= 0:
            await update.message.reply_text("❌ Send a valid numeric amount!", reply_markup=cancel_keyboard())
            return
        if amount < min_w or amount > max_w:
            await update.message.reply_text(f"❌ Invalid amount! Limit: {min_w}$ - {max_w}$", reply_markup=cancel_keyboard())
            return
        if amount > u_bal:
            await update.message.reply_text("❌ Insufficient balance!", reply_markup=cancel_keyboard())
            return

        context.user_data["withdraw_amount"] = amount
        context.user_data["withdraw_mode"] = "number"
        await update.message.reply_text(ask("ACCOUNT NUMBER", "আপনার একাউন্ট নম্বর লিখুন", "017XXXXXXXX"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if w_mode == "number":
        method = context.user_data.get("withdraw_method")
        amount = context.user_data.get("withdraw_amount")
        payment_num = raw_text

        if len(payment_num) < 5:
            await update.message.reply_text("❌ Invalid account number! Try again:", reply_markup=cancel_keyboard())
            return
        if get_user(uid)["balance"] < amount:
            context.user_data.clear()
            await update.message.reply_text("❌ Insufficient balance!", reply_markup=main_keyboard(uid))
            return

        pid = generate_payment_id()
        
        await update_db_balance(uid, -amount)
        
        w_requests = load_json(WITHDRAW_DATA_FILE, {})
        w_requests[pid] = {
            "user_id": uid, "method": method, "amount": amount,
            "number": payment_num, "payment_id": pid, "status": "pending",
            "timestamp": datetime.now().isoformat()
        }
        save_json(WITHDRAW_DATA_FILE, w_requests)
        
        context.user_data.clear()
        await update.message.reply_text(card("REQUEST SENT", ["✅ উইথড্র রিকোয়েস্ট অ্যাডমিনের কাছে গেছে", "⏳ অ্যাপ্রুভালের অপেক্ষা করুন"], icon="💸"), parse_mode="HTML", reply_markup=main_keyboard(uid))
        
        admin_msg = card("NEW WITHDRAWAL", [
            info_row("🆔", "User ID", f"<code>{uid}</code>"),
            info_row("⚙️", "Method", html.escape(str(method))),
            info_row("📞", "Number", f"<code>{html.escape(payment_num)}</code>"),
            info_row("💵", "Amount", f"<code>{amount}$</code>"),
            info_row("🧾", "PID", f"<code>{pid}</code>"),
        ], icon="💰")
        kb = InlineKeyboardMarkup([
            [rbtn("✅ Approve", callback_data=f"adm_app_{pid}"), rbtn("❌ Reject", callback_data=f"adm_rej_{pid}")]
        ])
        for a_id in ADMINS:
            try: await context.bot.send_message(a_id, admin_msg, parse_mode="HTML", reply_markup=kb)
            except Exception: pass
        return

    # --- ADMIN EDIT MODES ---
    edit_mode = context.user_data.get("admin_edit_mode")
    if edit_mode and is_admin(uid):
        context.user_data["admin_edit_mode"] = None
        try:
            await handle_admin_edit(update, context, edit_mode, raw_text)
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Invalid value! মেনু থেকে আবার চেষ্টা করুন।", reply_markup=admin_main_keyboard())
        return

    # --- USER BUTTON COMMANDS ---
    if text in (BTN_GET, "GET NUMBER", "🚀 GET NUMBER", "📱 GET NUMBER"):
        status = await update.message.reply_text("⏳ " + fancy("Loading Services") + f" <code>[{make_bar(30)}]</code>", parse_mode="HTML")
        top_ranges, err = await fetch_top_ranges()
        if err or not top_ranges:
            err_msg = html.escape(err if err else "No active services returned from API")
            await status.edit_text(card("SERVER ERROR", ["❌ সার্ভার থেকে সার্ভিস আনা যায়নি", info_row("🔍", "Reason", f"<code>{err_msg}</code>")], icon="⚠️"), parse_mode="HTML")
            return
        
        context.user_data["top_ranges"] = top_ranges
        context.user_data["country_ranges"] = {}
        await status.edit_text(SERVICE_TITLE, parse_mode="HTML", reply_markup=build_service_keyboard(top_ranges))
        return

    if text in (BTN_BALANCE, "💵 BALANCE", "BALANCE", "💼 WALLET", "💳 WALLET"):
        u_info = get_user(uid)
        settings = load_settings()
        m_method = u_info.get("withdrawal_method") or "Not Set"
        
        bal_text = card("MY WALLET", [
            info_row("💰", "Balance", f"<code>{u_info['balance']:.4f}$</code>"),
            info_row("💳", "Method", f"<code>{html.escape(str(m_method))}</code>"),
            info_row("📉", "Min Withdraw", f"<code>{settings['min_withdraw']}$</code>"),
        ], icon="💼")
        kb = InlineKeyboardMarkup([
            [rbtn("💳 Payment Method", callback_data="set_method")],
            [rbtn("💸 Withdraw Now", callback_data="init_withdraw")]
        ])
        await update.message.reply_text(bal_text, parse_mode="HTML", reply_markup=kb)
        return

    if text in (BTN_REFER, "🎁 REFER & EARN", "REFER & EARN", "🎁 REFER AND EARN"):
        settings = load_settings()
        b_info = await context.bot.get_me()
        ref_link = f"https://t.me/{b_info.username}?start={uid}"
        u_info = get_user(uid)
        
        ref_msg = card("REFER & EARN", [
            f"🔗 <b>Your Link (Click to Copy):</b>",
            f"<code>{ref_link}</code>",
            "---",
            info_row("👥", "Referrals", u_info.get('referrals', 0)),
            info_row("💰", "Earned", f"<code>{u_info.get('referral_earnings', 0.0):.4f}$</code>"),
            info_row("🎯", "Per Referral", f"<code>{settings['refer_bonus']:.4f}$</code>"),
        ], icon="🎁")
        await update.message.reply_text(ref_msg, parse_mode="HTML")
        return

    if text in (BTN_TRAFFIC, "📊 TRAFFIC", "TRAFFIC", "📡 LIVE TRAFFIC"):
        logs = load_json(ACTIVITY_LOGS_FILE, [])
        one_h_ago = datetime.now() - timedelta(hours=1)
        
        counts = {}
        total = 0
        for log in logs:
            if log.get("action") == "OTP_RECEIVED":
                try:
                    ts = datetime.fromisoformat(log.get("timestamp"))
                    if ts >= one_h_ago:
                        dtls = log.get("details", {})
                        num, sms = dtls.get("number"), dtls.get("sms")
                        srv = detect_service(sms)
                        flag, cname = get_country_info(num)
                        key = (srv, flag, cname)
                        counts[key] = counts.get(key, 0) + 1
                        total += 1
                except Exception:
                    pass
                
        if total == 0:
            await update.message.reply_text(card("LIVE TRAFFIC • 1H", ["📭 গত ১ ঘন্টায় কোনো OTP আসেনি"], icon="📡"), parse_mode="HTML")
            return

        rows = []
        for (srv, flag, cname), count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            pct = (count / total) * 100
            rows.append(f"{flag} <b>{srv}</b> ⟡ {html.escape(str(cname))}")
            rows.append(f"   <code>[{make_bar(pct)}]</code> {pct:.1f}%")
        rows.append("---")
        rows.append(info_row("📊", "Total OTP", f"<code>{total}</code>"))
        await update.message.reply_text(card("LIVE TRAFFIC • 1H", rows, icon="📡"), parse_mode="HTML")
        return

    if text in (BTN_LEADER, "🏆 LEADERBOARD", "LEADERBOARD", "👑 LEADERBOARD"):
        stats = load_json(STATS_FILE, {})
        users = load_json(USER_DATA_FILE, {})
        
        ranked = []
        for u_id, s_data in stats.items():
            cnt = len(s_data.get("otps_received", []))
            if cnt > 0: ranked.append((u_id, cnt))
            
        ranked = sorted(ranked, key=lambda x: x[1], reverse=True)[:10]
        medals = ["🥇", "🥈", "🥉"]
        
        rows = []
        if ranked:
            for idx, (r_uid, count) in enumerate(ranked, 1):
                u_name = users.get(str(r_uid), {}).get("full_name") or f"User ({r_uid[-4:]})"
                medal = medals[idx - 1] if idx <= 3 else f"<b>#{idx}</b>"
                rows.append(f"{medal} {html.escape(u_name)} ⟡ <code>{count} OTPs</code>")
        else:
            rows.append("<i>এখনো কোনো OTP রেকর্ড নেই</i>")
        await update.message.reply_text(card("TOP 10 EARNERS", rows, icon="👑"), parse_mode="HTML")
        return

    if text in (BTN_SUPPORT, "💬 SUPPORT", "SUPPORT", "🎧 SUPPORT"):
        settings = load_settings()
        sup = settings.get("support_username")
        kb = InlineKeyboardMarkup([[rbtn("📩 Contact Support", url=f"https://t.me/{sup}")]])
        await update.message.reply_text(card("SUPPORT", ["🛟 সাহায্য লাগলে আমাদের টিম আছে", "👇 নিচের বাটনে ক্লিক করুন"], icon="🎧"), parse_mode="HTML", reply_markup=kb)
        return

    # --- ADMIN MAIN MENU CATEGORIES ---
    if text in (BTN_ADMIN, "⚙️ ADMIN PANEL", "ADMIN PANEL", "👨‍💻 ADMIN PANEL") and is_admin(uid):
        await update.message.reply_text(card("ADMIN CONTROL PANEL", ["⚙️ System ⟡ 💵 Users", "🔒 Security ⟡ 📢 Broadcast"], icon="👨‍💻"), parse_mode="HTML", reply_markup=admin_main_keyboard())
        return

    if text == "⚙️ SYSTEM CONFIG" and is_admin(uid):
        await update.message.reply_text(card("SYSTEM CONFIG", ["🔑 API ⟡ 💰 Limits ⟡ ⏱ Cooldown", "🚫 Maintenance"], icon="⚙️"), parse_mode="HTML", reply_markup=admin_system_config_keyboard())
        return

    if text == "💵 USER & BALANCE" and is_admin(uid):
        await update.message.reply_text(card("USER & BALANCE", ["➕ Add / ➖ Remove Balance", "💬 Message ⟡ 🔍 Search"], icon="💵"), parse_mode="HTML", reply_markup=admin_user_balance_keyboard())
        return

    if "SECURITY & JOIN" in text and is_admin(uid):
        await update.message.reply_text(card("SECURITY & JOIN", ["🚫 Ban / ✅ Unban", "📢 Force Join Channels"], icon="🔒"), parse_mode="HTML", reply_markup=admin_security_join_keyboard())
        return

    if "FORCE CHANNELS" in text and is_admin(uid):
        settings = load_settings()
        ch_list = settings.get("force_join_channels", [])
        channels_text = "\n".join([f"• <code>{html.escape(c)}</code>" for c in ch_list]) if ch_list else "<i>কোনো চ্যানেল সেট করা নেই</i>"
        msg = card("FORCE JOIN", ["📢 বর্তমান চ্যানেলসমূহ", channels_text], icon="🔐")
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=admin_force_channel_keyboard())
        return

    if "ADD CHANNEL" in text and is_admin(uid):
        context.user_data["admin_edit_mode"] = "add_force_channel"
        await update.message.reply_text(ask("ADD CHANNEL", "চ্যানেলের ইউজারনেম লিখুন", "@yourchannel"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if "DELETE CHANNEL" in text and is_admin(uid):
        context.user_data["admin_edit_mode"] = "del_force_channel"
        settings = load_settings()
        ch_list = settings.get("force_join_channels", [])
        channels_text = "\n".join([f"• <code>{html.escape(c)}</code>" for c in ch_list]) if ch_list else "<i>কোনো চ্যানেল নেই</i>"
        await update.message.reply_text(card("DELETE CHANNEL", ["✍️ যেটা বাদ দেবেন তার ইউজারনেম লিখুন", "---", channels_text], icon="🗑"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if "BACK TO SECURITY" in text and is_admin(uid):
        await update.message.reply_text(card("SECURITY & JOIN", ["🚫 Ban / ✅ Unban", "📢 Force Join Channels"], icon="🔒"), parse_mode="HTML", reply_markup=admin_security_join_keyboard())
        return
    if text == "📢 NOTICE & B-CAST" and is_admin(uid):
        await update.message.reply_text(card("NOTICE & BROADCAST", ["📢 Broadcast", "📝 Welcome ⟡ 💬 Support ⟡ 🔗 Link"], icon="📢"), parse_mode="HTML", reply_markup=admin_notice_bcast_keyboard())
        return

    # --- ADMIN SYSTEM CONFIG ---
    if text == "🔑 SET API KEY" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "api_key"
        await update.message.reply_text(ask("SET API KEY", "নতুন API key পাঠান"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "🌐 SET API BASE URL" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "base_url"
        await update.message.reply_text(ask("SET BASE URL", "নতুন API Base URL পাঠান", "https://example.com/api"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "📢 SET OTP CHANNEL ID" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "otp_channel"
        await update.message.reply_text(ask("OTP CHANNEL", "চ্যানেল ID বা ইউজারনেম পাঠান", "-100xxxxxxxxxx  |  @channel"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "💰 SET WITHDRAW LIMITS" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "withdraw_limits"
        await update.message.reply_text(ask("WITHDRAW LIMITS", "MIN আর MAX স্পেস দিয়ে লিখুন", "0.5 100"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "🎁 SET REFER BONUS" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "refer_bonus"
        await update.message.reply_text(ask("REFER BONUS", "বোনাসের পরিমাণ লিখুন", "0.05"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "⏱ SET COOLDOWN" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "cooldown"
        await update.message.reply_text(ask("COOLDOWN", "সেকেন্ডে কুলডাউন লিখুন", "1.0"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "🚫 TOGGLE MAINTENANCE" and is_admin(uid):
        settings = load_settings()
        settings["maintenance_mode"] = not settings.get("maintenance_mode", False)
        save_settings(settings)
        status = "ENABLED" if settings["maintenance_mode"] else "DISABLED"
        await update.message.reply_text(f"🛠 Maintenance Mode is now: <b>{status}</b>", parse_mode="HTML")
        return

    # --- ADMIN USER & BALANCE ---
    if text == "➕ ADD BALANCE" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "add_balance"
        await update.message.reply_text(ask("ADD BALANCE", "USER_ID আর AMOUNT লিখুন", "123456789 5.0"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "➖ REMOVE BALANCE" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "remove_balance"
        await update.message.reply_text(ask("REMOVE BALANCE", "USER_ID আর AMOUNT লিখুন", "123456789 2.0"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "💬 DIRECT MSG USER" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "direct_msg"
        await update.message.reply_text(ask("DIRECT MESSAGE", "USER_ID আর মেসেজ লিখুন", "123456789 Hello"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "🔍 SEARCH BY USERNAME" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "search_username"
        await update.message.reply_text(ask("SEARCH USER", "Telegram username লিখুন (@ ছাড়া)"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "📜 ALL USER BALANCE" and is_admin(uid):
        users = load_json(USER_DATA_FILE, {})
        tot_bal = sum(u.get("balance", 0.0) for u in users.values())
        lines = [f"Total Users: {len(users)} | Total Balance: {tot_bal:.4f}$\n"]
        for idx, (u_id, u_data) in enumerate(users.items(), 1):
            lines.append(f"{idx}. ID: {u_id} | Bal: {u_data.get('balance', 0.0):.4f}$")
        
        file_io = io.BytesIO("\n".join(lines).encode('utf-8'))
        file_io.name = "All_Users_Balance.txt"
        await update.message.reply_document(file_io, caption=f"📊 Total System Balance: {tot_bal:.4f}$")
        return

    # --- ADMIN SECURITY & NOTICE ---
    if text == "🚫 BAN USER" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "ban_user"
        await update.message.reply_text(ask("BAN USER", "যাকে ব্যান করবেন তার USER_ID লিখুন"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "✅ UNBAN USER" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "unban_user"
        await update.message.reply_text(ask("UNBAN USER", "যাকে আনব্যান করবেন তার USER_ID লিখুন"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "📜 BAN USER LIST" and is_admin(uid):
        banned = load_json(BANNED_USERS_FILE, [])
        await update.message.reply_text(f"🚫 <b>Banned Users ({len(banned)}):</b>\n\n" + "\n".join(banned), parse_mode="HTML")
        return

    if text == "📢 BROADCAST NOTICE" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "broadcast"
        await update.message.reply_text(ask("BROADCAST", "সবাইকে পাঠানোর টেক্সট লিখুন"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "📝 SET WELCOME MSG" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "welcome"
        await update.message.reply_text(ask("WELCOME MESSAGE", "নতুন Welcome টেক্সট পাঠান (HTML চলবে)"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "💬 SET SUPPORT USERNAME" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "support"
        await update.message.reply_text(ask("SUPPORT USERNAME", "Support-এর Telegram username লিখুন"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text == "🔗 SET CHANNEL LINK" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "channel_link"
        await update.message.reply_text(ask("CHANNEL LINK", "চ্যানেলের লিংক পাঠান", "https://t.me/yourchannel"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if text in ("🔙 BACK TO ADMIN", "BACK TO ADMIN") and is_admin(uid):
        await update.message.reply_text(card("ADMIN CONTROL PANEL", ["⚙️ System ⟡ 💵 Users", "🔒 Security ⟡ 📢 Broadcast"], icon="👨‍💻"), parse_mode="HTML", reply_markup=admin_main_keyboard())
        return

    if text in ("🔙 BACK TO ADMIN", "BACK TO ADMIN", "🔙 BACK TO MAIN", "BACK TO MAIN"):
        await update.message.reply_text(card("MAIN MENU", ["🏠 হোম মেনুতে ফিরে এসেছেন"], icon="🏠"), parse_mode="HTML", reply_markup=main_keyboard(uid))
        return

# ==================== CALLBACK QUERY HANDLER ====================
ALERT_PREFIXES = ("check_join", "same_range", "init_withdraw", "sel_cty_")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data

    if is_user_banned(uid) and not is_admin(uid):
        await query.answer("🚫 You are banned!", show_alert=True)
        return
    if load_settings().get("maintenance_mode", False) and not is_admin(uid):
        await query.answer("🛠 Bot is under maintenance. Try later.", show_alert=True)
        return

    if data.startswith("adm_") and not is_admin(uid):
        await query.answer("⛔ Not allowed!", show_alert=True)
        return

    if not data.startswith(ALERT_PREFIXES):
        await query.answer()

    if data == "check_join":
        if not await get_not_joined(context.bot, uid):
            await query.answer()
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.reply_text(card("VERIFIED", ["✅ সফলভাবে যাচাই হয়েছে", "🎉 এখন বট ব্যবহার করুন"], icon="🔓"), parse_mode="HTML", reply_markup=main_keyboard(uid))
        else:
            await query.answer("❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি!", show_alert=True)
        return

    if data.startswith("sel_app_"):
        app_name = data.replace("sel_app_", "")
        top_ranges = context.user_data.get("top_ranges", {})
        ranges = top_ranges.get(app_name, [])
        if not ranges:
            await query.edit_message_text("❌ No ranges available for this service.")
            return

        country_map = {}
        for rng in ranges:
            flag, cname = get_country_info(rng)
            c_key = f"{flag} {cname}"
            if c_key not in country_map:
                country_map[c_key] = []
            country_map[c_key].append(rng)

        context.user_data["country_ranges"] = {}

        buttons = []
        row = []
        for c_label, rng_list in country_map.items():
            c_idx = str(len(context.user_data["country_ranges"]) + 1)
            context.user_data["country_ranges"][c_idx] = {
                "app": app_name,
                "label": c_label,
                "ranges": rng_list
            }
            row.append(rbtn(c_label, callback_data=f"sel_cty_{c_idx}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        buttons.append([rbtn("⬅️ Back to Services", callback_data="back_to_services")])
        await query.edit_message_text(
            card("SELECT COUNTRY", [info_row("📲", "Service", html.escape(app_name)), "👇 আপনার দেশ সিলেক্ট করুন"], icon="🌍"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data.startswith("sel_cty_"):
        c_idx = data.replace("sel_cty_", "")
        c_info = context.user_data.get("country_ranges", {}).get(c_idx)
        if not c_info:
            await query.answer()
            await query.edit_message_text("❌ Session expired. Please click GET NUMBER again.")
            return

        wait = check_cooldown(uid)
        if wait:
            await query.answer(f"⏱ Please wait {wait}s before the next request", show_alert=True)
            return
        await query.answer()

        app_name = c_info["app"]
        ranges = c_info["ranges"]

        selected_range = random.choice(ranges)
        last_range[uid] = selected_range
        last_app[uid] = app_name

        try:
            await query.message.delete()
        except Exception:
            pass
        await request_queue.put({
            'uid': uid,
            'chat_id': query.message.chat_id,
            'context': context,
            'range_text': selected_range,
            'app': app_name
        })
        return

    if data == "back_to_services":
        top_ranges = context.user_data.get("top_ranges", {})
        if not top_ranges:
            await query.edit_message_text("❌ Session expired. Please click GET NUMBER again.")
            return
        await query.edit_message_text(SERVICE_TITLE, parse_mode="HTML", reply_markup=build_service_keyboard(top_ranges))
        return

    if data == "same_range":
        r_text = last_range.get(uid)
        if not r_text:
            await query.answer("No previous range found!", show_alert=True)
            return
        wait = check_cooldown(uid)
        if wait:
            await query.answer(f"⏱ Please wait {wait}s before the next request", show_alert=True)
            return
        await query.answer()
        try:
            await query.message.delete()
        except Exception:
            pass
        await request_queue.put({
            'uid': uid,
            'chat_id': query.message.chat_id,
            'context': context,
            'range_text': r_text,
            'app': last_app.get(uid)
        })
        return

    if data == "set_method":
        kb = InlineKeyboardMarkup([
            [rbtn("Bkash", callback_data="m_Bkash"), rbtn("Nagad", callback_data="m_Nagad")],
            [rbtn("Rocket", callback_data="m_Rocket"), rbtn("Binance", callback_data="m_Binance")]
        ])
        await query.edit_message_text(card("PAYMENT METHOD", ["👇 আপনার পেমেন্ট মেথড সিলেক্ট করুন"], icon="💳"), parse_mode="HTML", reply_markup=kb)
        return

    if data.startswith("m_"):
        method_name = data.replace("m_", "")
        users = load_json(USER_DATA_FILE, {})
        if str(uid) in users:
            users[str(uid)]["withdrawal_method"] = method_name
            save_json(USER_DATA_FILE, users)
            await query.edit_message_text(card("METHOD SAVED", [info_row("💳", "Method", html.escape(method_name))], icon="✅"), parse_mode="HTML")
        return

    if data == "init_withdraw":
        u_info = get_user(uid)
        m_method = u_info.get("withdrawal_method")
        if not m_method:
            await query.answer("❌ Set withdrawal method first!", show_alert=True)
            return
            
        settings = load_settings()
        if u_info["balance"] < settings["min_withdraw"]:
            await query.answer(f"❌ Minimum withdrawal is {settings['min_withdraw']}$", show_alert=True)
            return

        await query.answer()
        context.user_data["withdraw_method"] = m_method
        context.user_data["withdraw_mode"] = "amount"
        await query.message.reply_text(ask("WITHDRAW", "কত টাকা উইথড্র করবেন লিখুন", f"Min: {settings['min_withdraw']}$"), parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if data.startswith("adm_app_"):
        pid = data.replace("adm_app_", "")
        w_reqs = load_json(WITHDRAW_DATA_FILE, {})
        if pid in w_reqs and w_reqs[pid]["status"] == "pending":
            w_reqs[pid]["status"] = "approved"
            save_json(WITHDRAW_DATA_FILE, w_reqs)
            
            u_id = w_reqs[pid]["user_id"]
            amt = w_reqs[pid]["amount"]
            try:
                await context.bot.send_message(u_id, card("WITHDRAW APPROVED", [info_row("💵", "Amount", f"<code>{amt}$</code>"), info_row("🧾", "PID", f"<code>{pid}</code>")], icon="✅"), parse_mode="HTML")
            except Exception:
                pass
            
            await query.edit_message_text(f"✅ Approved Request {pid}")
        return

    if data.startswith("adm_rej_"):
        pid = data.replace("adm_rej_", "")
        w_reqs = load_json(WITHDRAW_DATA_FILE, {})
        if pid in w_reqs and w_reqs[pid]["status"] == "pending":
            w_reqs[pid]["status"] = "rejected"
            save_json(WITHDRAW_DATA_FILE, w_reqs)
            
            u_id = w_reqs[pid]["user_id"]
            amt = w_reqs[pid]["amount"]
            
            await update_db_balance(u_id, amt)
            
            try:
                await context.bot.send_message(u_id, card("WITHDRAW REJECTED", ["💸 টাকা ব্যালেন্সে ফেরত দেওয়া হয়েছে", info_row("💵", "Amount", f"<code>{amt}$</code>"), info_row("🧾", "PID", f"<code>{pid}</code>")], icon="❌"), parse_mode="HTML")
            except Exception:
                pass
            
            await query.edit_message_text(f"❌ Rejected Request {pid}")
        return

# ==================== MAIN APPLICATION START ====================

async def post_init(application):
    for coro in (worker(), monitor_loop(application)):
        task = asyncio.create_task(coro)
        _bg_tasks.add(task)
        task.add_done_callback(_bg_tasks.discard)

def main():
    request_config = HTTPXRequest(connect_timeout=15.0, read_timeout=15.0)
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .request(request_config)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("🚀 PRO BOT RUNNING WITH ULTRA PREMIUM UI...")
    bind_port()
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass