import logging
import datetime
import random
import ipaddress
import pickle
import os
import asyncio
import io

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ------------------ تنظیمات و پیکربندی ------------------

CARD_NUMBERS = {
    "default": {"number": "6037 9917 0465 7182", "name": "فریده قمری"}
}

custom_buttons = {}  # {"name": {"file_id": "", "type": "file/text", "content": "", "price": 0}}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

ADMIN_IDS_FILE = os.path.join(DATA_DIR, "admin_ids.pkl")

def load_admin_ids():
    global admin_ids
    if os.path.exists(ADMIN_IDS_FILE):
        with open(ADMIN_IDS_FILE, "rb") as f:
            admin_ids = pickle.load(f)
    else:
        admin_ids = {6607557664}

def save_admin_ids():
    with open(ADMIN_IDS_FILE, "wb") as f:
        pickle.dump(admin_ids, f)

# تنظیمات اولیه
admin_ids = set()  # از فایل بارگذاری خواهد شد
ADMIN_PASSWORD = "1"
SUPPORT_ID = "@s_poshtibani"

user_balance = {}       # {user_id: موجودی}
purchase_history = {}   # {user_id: [تراکنش‌ها]}
pending_receipts = {}
receipt_photos = {}
pending_balance_requests = {}
pending_balance_receipts = {}
admin_state = {}        # {admin_id: وضعیت عملیات}

temp_discount_codes = {}
discount_codes = {"OFF10": 10, "OFF20": 20, "OFF30": 30}
user_discount = {}      # {user_id: (code, درصد)}
awaiting_discount_code = {}  # {user_id: True}

referral_points = {}
referred_users = set()
all_users = set()

BOT_USERNAME = "dnsgolden_bot"
# برای جویین اجباری، از لیست کانال‌ها (بدون @) استفاده می‌کنیم:
FORCE_JOIN_CHANNEL = ["YourChannel1", "YourChannel2"]
FORCE_JOIN_ENABLED = False
BOT_UPDATING = False

ENABLE_DNS_BUTTON = True
ENABLE_ACCOUNT_BUTTON = True
ENABLE_BALANCE_BUTTON = True
ENABLE_REFERRAL_BUTTON = True
ENABLE_WIREGUARD_BUTTON = True
ENABLE_SITE_SUBSCRIPTION_BUTTON = True

SITE_SUBSCRIPTION_PLANS = {
    "1": {"name": "اشتراک 1 ماهه", "price": 450000, "username": "null", "password": "null", "identifier": "null"},
    "3": {"name": "اشتراک 3 ماهه", "price": 650000, "username": "null", "password": "null", "identifier": "null"},
    "6": {"name": "اشتراک 6 ماهه", "price": 850000, "username": "null", "password": "null", "identifier": "null"},
}

TERMS_TEXT = (
    "📜 قوانین و مقررات:\n\n"
    "1. استفاده از سرویس تنها برای اهداف قانونی می‌باشد.\n"
    "2. سرویس‌های ارائه شده تست شده‌اند.\n"
    "3. در صورت بروز مشکل، با ☎️ پشتیبانی تماس بگیرید.\n\n"
    "برای بازگشت به منوی اصلی روی دکمه زیر کلیک کنید."
)

WIREGUARD_PRICE = 130000
awaiting_custom_balance = {}

# ------------------ تنظیمات رنج‌های وایرگارد ------------------
WIREGUARD_RANGES = {
    "آلمان1": {
        "cidr_ranges": [
            "85.10.192.0/18", "88.99.0.0/16", "116.202.0.0/16",
            "135.181.0.0/16", "142.132.128.0/17", "144.76.0.0/16"
        ],
    },
    "روسیه": {
        "cidr_ranges": [
            "45.8.144.0/22", "45.90.28.0/22", "45.139.104.0/22",
            "45.144.28.0/22", "45.146.164.0/22", "45.155.124.0/22"
        ],
    },
    "امارات": {
        "cidr_ranges": [
            "5.75.128.0/17", "31.223.184.0/21", "37.252.181.0/24",
            "45.9.228.0/22", "45.159.248.0/22", "89.46.248.0/22"
        ],
    },
    "ایتالیا": {
        "cidr_ranges": [
            "2.228.128.0/17", "5.134.112.0/20", "31.14.248.0/22",
            "37.206.64.0/18", "45.138.228.0/22", "45.143.176.0/22"
        ],
    },
    "ترکیه": {
        "cidr_ranges": [
            "31.206.0.0/16", "37.148.208.0/21", "45.155.168.0/22",
            "62.248.0.0/17", "77.92.96.0/19", "78.135.0.0/16"
        ],
    },
    "آمریکا": {
        "cidr_ranges": [
            "23.19.0.0/16", "23.226.48.0/20", "45.42.128.0/17",
            "45.58.0.0/17", "64.120.0.0/17", "66.150.0.0/16"
        ],
    },
}

# دکمه‌های سفارشی اضافه شده توسط مدیر (مثلاً { "دکمه جدید": file_id })
custom_buttons = {}  
# انتظار برای وارد کردن کد تخفیف در خرید DNS
awaiting_dns_discount = {}

# ------------------ تنظیمات DNS ------------------

DNS_CONFIGS = {
    "آمریکا": {
        "name": "سرور آمریکا",
        "price": 60000,
        "cidr_ranges": [
            "3.0.0.0/8", "4.0.0.0/8", "8.0.0.0/8", "9.0.0.0/8",
            "11.0.0.0/8", "12.0.0.0/8", "13.0.0.0/8", "15.0.0.0/8",
            "16.0.0.0/8", "17.0.0.0/8", "18.0.0.0/8", "19.0.0.0/8",
            "20.0.0.0/8", "23.0.0.0/8", "24.0.0.0/8", "26.0.0.0/8"
        ],
        "flag": "🇺🇸",
        "ipv6_prefix": "2600:1f00",
    },
    "امارات": {
        "name": "سرور امارات",
        "price": 110000,
        "cidr_ranges": [
            "184.25.205.0/24", "5.30.0.0/15", "5.32.0.0/17", "23.194.192.0/22",
            "46.19.77.0/24", "46.19.78.0/23", "80.227.0.0/16", "87.200.0.0/15",
            "91.72.0.0/14", "94.200.0.0/14", "94.204.0.0/15", "94.206.0.0/16",
            "94.207.0.0/19", "94.207.48.0/20", "94.207.64.0/18", "94.207.128.0/17",
            "104.109.251.0/24", "149.24.230.0/23", "160.83.52.0/23", "213.132.32.0/19"
        ],
        "flag": "🇦🇪",
        "ipv6_prefix": "2a02:2ae8",
    },
    "آلمان1": {
        "name": "سرور آلمان 1",
        "price": 80000,
        "cidr_ranges": [
            "84.128.0.0/10", "87.128.0.0/10", "91.0.0.0/10", "79.192.0.0/10",
            "93.192.0.0/10", "217.224.0.0/11", "80.128.0.0/11", "91.32.0.0/11",
            "93.192.0.0/11", "217.80.0.0/12"
        ],
        "flag": "🇩🇪",
        "ipv6_prefix": "2a02:2ae8",
    },
    "ترکیه": {
        "name": "سرور ترکیه",
        "price": 70000,
        "cidr_ranges": [
            "78.161.221.0/24", "78.163.24.0/24", "78.163.96.0/21", "78.163.105.0/24",
            "78.163.112.0/20", "78.163.128.0/22", "78.163.156.0/23", "78.163.164.0/22",
            "78.164.209.0/24", "78.165.64.0/20", "78.165.80.0/21", "78.165.88.0/24",
            "78.165.92.0/22", "78.165.96.0/19", "78.165.192.0/20", "78.165.208.0/24",
            "78.165.211.0/24", "78.165.212.0/23", "78.165.215.0/24", "78.165.216.0/24"
        ],
        "flag": "🇹🇷",
        "ipv6_prefix": "2a02:2ae8",
    },
    "روسیه": {
        "name": "سرور روسیه",
        "price": 50000,
        "cidr_ranges": [
            "2.60.0.0/15", "2.62.0.0/16", "5.136.0.0/15", "5.138.0.0/16",
            "31.162.0.0/15", "31.180.0.0/15", "37.20.0.0/14", "37.78.0.0/15",
            "46.158.0.0/15", "78.36.0.0/15", "78.85.0.0/16", "185.27.148.0/22",
            "185.140.148.0/22", "185.169.100.0/22", "185.199.4.0/22", "185.205.128.0/22",
            "185.226.128.0/22", "188.16.0.0/16", "188.17.0.0/18", "188.17.64.0/19",
            "188.17.96.0/20", "188.17.120.0/21", "188.17.128.0/18", "188.17.192.0/19",
            "188.18.0.0/18", "188.18.64.0/19", "188.18.96.0/20", "188.18.120.0/21",
            "188.18.128.0/17", "188.19.0.0/16", "188.113.0.0/18", "188.114.0.0/18",
            "188.128.0.0/17", "188.133.192.0/18", "188.254.0.0/17", "195.19.96.0/20",
            "195.38.32.0/19", "195.46.96.0/19", "195.162.32.0/19", "212.20.0.0/18",
            "212.32.192.0/19", "212.34.96.0/19", "212.35.160.0/19", "212.48.192.0/19",
            "212.55.96.0/19", "212.57.128.0/18", "212.96.192.0/19", "212.106.32.0/19",
            "212.120.160.0/19", "212.124.0.0/20", "212.164.0.0/16", "212.220.0.0/17",
            "212.220.128.0/18", "212.220.192.0/20", "212.220.224.0/19", "213.24.112.0/20",
            "213.59.192.0/18", "213.129.32.0/19", "213.135.96.0/19", "213.155.200.0/21",
            "213.155.208.0/20", "213.158.0.0/20", "213.167.192.0/19", "213.177.96.0/19",
            "213.228.64.0/19", "213.228.96.0/20", "213.242.0.0/18", "217.20.80.0/20",
            "217.23.16.0/20", "217.65.80.0/20", "217.70.96.0/19", "217.107.64.0/19",
            "217.107.112.0/20", "217.107.128.0/18", "217.107.224.0/19", "217.116.128.0/19"
        ],
        "flag": "🇷🇺",
        "ipv6_prefix": "2a00:1e88",
    },
    "قطر": {
        "name": "سرور قطر",
        "price": 60000,
        "cidr_ranges": [
            "37.208.128.0/17", "37.211.128.0/17", "78.100.64.0/18", "78.100.128.0/18",
            "78.100.192.0/19", "78.101.32.0/19", "78.101.96.0/19", "78.101.128.0/19",
            "78.101.192.0/19", "89.211.0.0/18", "89.211.64.0/19", "176.202.0.0/15",
            "178.152.0.0/16", "178.153.0.0/18", "178.153.96.0/19", "178.153.128.0/18",
            "212.77.192.0/19"
        ],
        "flag": "🇶🇦",
        "ipv6_prefix": "2001:1a11",
    },
}

# ------------------ توابع بارگذاری و ذخیره اطلاعات ------------------
def load_balance():
    global user_balance
    file_path = os.path.join(DATA_DIR, "balance.pkl")
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            user_balance = pickle.load(f)
    else:
        user_balance = {}

def save_balance():
    file_path = os.path.join(DATA_DIR, "balance.pkl")
    with open(file_path, "wb") as f:
        pickle.dump(user_balance, f)

def load_history():
    global purchase_history
    file_path = os.path.join(DATA_DIR, "history.pkl")
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            purchase_history = pickle.load(f)
    else:
        purchase_history = {}

def save_history():
    file_path = os.path.join(DATA_DIR, "history.pkl")
    with open(file_path, "wb") as f:
        pickle.dump(purchase_history, f)

async def notify_balance_change(user_id: int, change: int, context: ContextTypes.DEFAULT_TYPE):
    new_balance = user_balance.get(user_id, 0)
    if change > 0:
        text = f"✅ موجودی شما افزایش یافت. مبلغ اضافه شده: {change:,} تومان. موجودی جدید: {new_balance:,} تومان."
    else:
        text = f"❌ موجودی شما کاهش یافت. مبلغ کسر شده: {-change:,} تومان. موجودی جدید: {new_balance:,} تومان."
    try:
        await context.bot.send_message(chat_id=user_id, text=text)
    except Exception as e:
        logger.error(f"خطا در اطلاع‌رسانی به کاربر {user_id}: {e}")

# ------------------ سیستم تایید شماره تلفن ------------------
VERIFIED_PHONES_FILE = os.path.join(DATA_DIR, "verified_phones.pkl")
verified_phones = {}  # {user_id: {"phone": phone_number, "verified_at": timestamp}}

def load_verified_phones():
    global verified_phones
    if os.path.exists(VERIFIED_PHONES_FILE):
        with open(VERIFIED_PHONES_FILE, "rb") as f:
            verified_phones = pickle.load(f)

def save_verified_phones():
    with open(VERIFIED_PHONES_FILE, "wb") as f:
        pickle.dump(verified_phones, f)

def is_valid_iranian_phone(phone: str) -> bool:
    # Remove all spaces and dashes
    phone = phone.replace(" ", "").replace("-", "")

    # Check if starts with +98 or 0098
    if phone.startswith("+98"):
        phone = phone[3:]
    elif phone.startswith("0098"):
        phone = phone[4:]
    # Remove leading 0 if exists
    elif phone.startswith("0"):
        phone = phone[1:]

    # Check if the number is exactly 10 digits and starts with 9
    if not (phone.isdigit() and len(phone) == 10 and phone.startswith("9")):
        return False

    # Additional validation for Iranian mobile prefixes
    valid_prefixes = ['91', '92', '93', '94', '95', '96', '97', '98', '99', '90']
    if phone[:2] not in valid_prefixes:
        return False

    return True

# ------------------ توابع اصلی منو ------------------
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if user_id not in verified_phones and user_id not in admin_ids:
        keyboard = [[InlineKeyboardButton("📱 تایید شماره تلفن", callback_data="verify_phone")]]
        text = "⚠️ برای دسترسی به منوی اصلی، لطفا ابتدا شماره تلفن خود را تایید کنید."
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = "🏠 منوی اصلی:"
    is_admin = user_id in admin_ids
    rows = []
    if is_admin or ENABLE_DNS_BUTTON:
        rows.append([InlineKeyboardButton("🛒 خرید DNS اختصاصی", callback_data="dns_menu")])
    row = []
    if is_admin or ENABLE_ACCOUNT_BUTTON:
        row.append(InlineKeyboardButton("👤 حساب کاربری", callback_data="account_menu"))
    if is_admin or ENABLE_REFERRAL_BUTTON:
        row.append(InlineKeyboardButton("🔗 رفرال و امتیاز", callback_data="referral_menu"))
    if row:
        rows.append(row)
    row = [InlineKeyboardButton("☎️ پشتیبانی", callback_data="support_menu")]
    if is_admin or ENABLE_WIREGUARD_BUTTON:
        row.append(InlineKeyboardButton("🔑 وایرگارد اختصاصی", callback_data="wireguard_menu"))
    if row:
        rows.append(row)
    row = []
    if is_admin or ENABLE_BALANCE_BUTTON:
        row.append(InlineKeyboardButton("💳 افزایش موجودی", callback_data="balance_increase"))
    if is_admin or ENABLE_SITE_SUBSCRIPTION_BUTTON:
        row.append(InlineKeyboardButton("💻 خرید یوزرپسورد سایت", callback_data="site_subscription_menu"))
    if row:
        rows.append(row)
    if user_id not in verified_phones:
        rows.append([InlineKeyboardButton("📱 تایید شماره تلفن", callback_data="verify_phone")])
    rows.append([InlineKeyboardButton("🗃️ خرید سورس ربات", callback_data="buy_bot_source")])
    # دکمه‌های سفارشی اضافه شده توسط مدیر
    for btn_name in custom_buttons:
        rows.append([InlineKeyboardButton(btn_name, callback_data=f"custombutton_{btn_name}")])
    if is_admin:
        rows.append([InlineKeyboardButton("⚙️ پنل ادمین", callback_data="admin_panel_menu")])
    rows.append([InlineKeyboardButton("📜 قوانین و مقررات", callback_data="terms")])
    rows.append([InlineKeyboardButton("🌐 مینی اپ", web_app=WebAppInfo(url="https://dnsgolden.shop/"))])
    keyboard_main = InlineKeyboardMarkup(rows)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard_main)
    else:
        await update.message.reply_text(text, reply_markup=keyboard_main)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    if BOT_UPDATING:
        await update.message.reply_text("⚠️ ربات در حال بروزرسانی است. لطفاً بعداً تلاش کنید.")
        return
    all_users.add(user_id)

    # Store referral info for later use after phone verification
    if context.args:
        context.user_data['start_args'] = context.args
    if FORCE_JOIN_ENABLED and FORCE_JOIN_CHANNEL:
        if isinstance(FORCE_JOIN_CHANNEL, list):
            text_force = "برای استفاده از ربات باید در چنل‌های زیر عضو شوید:"
            keyboard = []
            for channel in FORCE_JOIN_CHANNEL:
                keyboard.append([InlineKeyboardButton("عضویت", url=f"https://t.me/{channel}")])
            keyboard.append([InlineKeyboardButton("بررسی عضویت", callback_data="check_force_join")])
            await update.message.reply_text(text_force, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        else:
            channel_url = f"https://t.me/{FORCE_JOIN_CHANNEL[1:]}" if FORCE_JOIN_CHANNEL.startswith("@") else FORCE_JOIN_CHANNEL
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("عضویت", url=channel_url)]])
            await update.message.reply_text(f"❌ لطفاً ابتدا در کانال {FORCE_JOIN_CHANNEL} عضو شوید.", reply_markup=keyboard)
            return
    text = f"سلام {user.first_name}!\nبه ربات خدمات DNS اختصاصی خوش آمدید."
    keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

# ------------------ توابع خرید DNS ------------------
def generate_dns_ip_pair(plan_id: str):
    ranges = DNS_CONFIGS[plan_id]["cidr_ranges"]
    chosen_range = random.choice(ranges)
    try:
        network = ipaddress.ip_network(chosen_range)
        if network.num_addresses < 3:
            return None, None
        ip1_int = random.randint(int(network.network_address) + 1, int(network.broadcast_address) - 1)
        ip2_int = random.randint(int(network.network_address) + 1, int(network.broadcast_address) - 1)
        while ip2_int == ip1_int:
            ip2_int = random.randint(int(network.network_address) + 1, int(network.broadcast_address) - 1)
        ip1 = str(ipaddress.ip_address(ip1_int))
        ip2 = str(ipaddress.ip_address(ip2_int))
        return ip1, ip2
    except Exception as e:
        logger.error("Error generating DNS IP pair: " + str(e))
        return None, None

def generate_dns_ipv6_pair(plan_id: str):
    prefix = DNS_CONFIGS[plan_id]["ipv6_prefix"]
    def random_ipv6(prefix):
        groups = prefix.split(":")
        remaining_groups = 8 - len(groups)
        remaining = [format(random.randint(0, 0xffff), 'x') for _ in range(remaining_groups)]
        return prefix + ":" + ":".join(remaining)
    ipv6_1 = random_ipv6(prefix)
    ipv6_2 = random_ipv6(prefix)
    while ipv6_1 == ipv6_2:
        ipv6_2 = random_ipv6(prefix)
    return ipv6_1, ipv6_2

async def dns_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("لطفاً لوکیشن DNS اختصاصی را انتخاب کنید:", reply_markup=build_dns_selection_menu())

def build_dns_selection_menu():
    keyboard = []
    for plan_id, config in DNS_CONFIGS.items():
        keyboard.append([InlineKeyboardButton(f"{config['flag']} {config['name']} - {config['price']:,} تومان", callback_data=f"buy_dnsplan_{plan_id}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def buy_dns_plan_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # فرمت: buy_dnsplan_{plan_id}
    parts = data.split("_")
    if len(parts) < 3:
        await query.edit_message_text("❌ خطا در انتخاب پلن.")
        return
    plan_id = parts[2]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("ثبت کد تخفیف", callback_data=f"enter_discount_dns_{plan_id}")],
        [InlineKeyboardButton("خرید بدون کد", callback_data=f"confirm_buy_dns_{plan_id}")]
    ])
    await query.edit_message_text("آیا کد تخفیف دارید؟", reply_markup=keyboard)

async def finalize_dns_purchase(plan_id: str, user_id: int, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    base_cost = DNS_CONFIGS[plan_id]["price"]
    discount_text = ""
    final_cost = base_cost
    if user_id in user_discount:
        code, discount_percent = user_discount[user_id]
        discount_value = int(base_cost * discount_percent / 100)
        final_cost = base_cost - discount_value
        discount_text = f"\n✅ کد تخفیف {code} اعمال شد: {discount_percent}% تخفیف (-{discount_value:,} تومان)"
        del user_discount[user_id]
    balance = user_balance.get(user_id, 0)
    if balance < final_cost:
        await query.edit_message_text("❌ موجودی شما کافی نیست. لطفاً ابتدا موجودی خود را افزایش دهید.")
        return
    user_balance[user_id] = balance - final_cost
    save_balance()
    await notify_balance_change(user_id, -final_cost, context)
    await query.edit_message_text("⏳ در حال پردازش، لطفاً کمی صبر کنید...")
    await asyncio.sleep(1)
    ip1, ip2 = generate_dns_ip_pair(plan_id)
    if not ip1 or not ip2:
        await query.edit_message_text("❌ خطا در تولید آی‌پی‌ها. لطفاً دوباره تلاش کنید.")
        return
    ipv6_1, ipv6_2 = generate_dns_ipv6_pair(plan_id)
    dns_caption = ("⚠️  حتماً از دی‌ان‌اس‌های الکترو :\n<code>78.157.42.100\n78.157.42.101</code>\n"
                "یا رادار:\n<code>10.202.10.10\n10.202.10.11</code>\n\n")
    final_text = (f"✅ خرید DNS اختصاصی انجام شد.\n\n"
                f"🌐 آی‌پی‌های اختصاصی شما :\nIPv4:\nIP 1: <code>{ip1}</code>\nIP 2: <code>{ip2}</code>\n\n"
                f"توجه داشته باشید ایپی های اختصاصی یکی را به دلخواه داخل جای اول و برای جای دوم یکی از ایپی های رادار (ایرنسل) یا الکترو (همراه اول) را استفاده کنید.\n\n"
                f"IPv6:\nIP 1: <code>{ipv6_1}</code>\nIP 2: <code>{ipv6_2}</code>\n\n"
                f"💸 مبلغ کسر شده: {final_cost:,} تومان{discount_text}\n\n{dns_caption}")
    await query.edit_message_text(final_text, parse_mode="HTML")
    record = {"type": "dns", "plan": plan_id, "ip1": ip1, "ip2": ip2,
            "ipv6_1": ipv6_1, "ipv6_2": ipv6_2, "cost": final_cost,
            "discount": discount_text.strip(), "timestamp": datetime.datetime.now()}
    purchase_history.setdefault(user_id, []).append(record)
    save_history()


async def confirm_buy_dns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # فرمت: confirm_buy_dns_{plan_id}
    parts = data.split("_")
    if len(parts) < 4:
        await query.edit_message_text("❌ خطا در پردازش خرید.")
        return
    plan_id = parts[3]
    user_id = query.from_user.id
    await finalize_dns_purchase(plan_id, user_id, query, context)

async def enter_discount_dns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # فرمت: enter_discount_dns_{plan_id}
    parts = data.split("_")
    if len(parts) < 4:
        await query.edit_message_text("❌ خطا در انتخاب پلن.")
        return
    plan_id = parts[3]
    awaiting_dns_discount[query.from_user.id] = plan_id
    await query.edit_message_text("✏️ لطفاً کد تخفیف خود را ارسال کنید:")

# ------------------ توابع بررسی عضویت اجباری و پشتیبانی ------------------
async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    all_joined = True
    if isinstance(FORCE_JOIN_CHANNEL, list):
        for channel in FORCE_JOIN_CHANNEL:
            try:
                member = await context.bot.get_chat_member(channel, user_id)
                if member.status not in ["member", "creator", "administrator"]:
                    all_joined = False
                    break
            except Exception:
                all_joined = False
                break
    if all_joined:
        await query.edit_message_text("✅ عضویت شما تأیید شد. لطفاً از منوی اصلی استفاده کنید.")
    else:
        await query.edit_message_text("❌ شما هنوز عضو همه چنل‌های مورد نیاز نیستید. لطفاً ابتدا عضو شوید.")

async def support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = f"☎️ اطلاعات پشتیبانی:\n\n- تلگرام: {SUPPORT_ID}\n\nدر صورت نیاز به راهنمایی با ما تماس بگیرید."
    keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def terms_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        TERMS_TEXT,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]])
    )

# ------------------ توابع اشتراک سایت ------------------
async def site_subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "💻 خرید یوزرپسورد سایت:\nلطفاً پلن مورد نظر را انتخاب کنید:"
    buttons = []
    for plan_key, plan_info in SITE_SUBSCRIPTION_PLANS.items():
        buttons.append(InlineKeyboardButton(f"{plan_info['name']} - {plan_info['price']:,} تومان", callback_data=f"buy_site_subscription_{plan_key}"))
    rows = [[button] for button in buttons]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))

async def buy_site_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) < 4:
        await query.edit_message_text("❌ خطا در انتخاب پلن.")
        return
    plan_key = parts[3]
    if plan_key not in SITE_SUBSCRIPTION_PLANS:
        await query.edit_message_text("❌ پلن نامعتبر.")
        return
    plan_info = SITE_SUBSCRIPTION_PLANS[plan_key]
    user_id = query.from_user.id
    cost = plan_info["price"]
    balance = user_balance.get(user_id, 0)
    if balance < cost:
        await query.edit_message_text("❌ موجودی شما کافی نیست. لطفاً ابتدا موجودی خود را افزایش دهید.")
        return
    user_balance[user_id] = balance - cost
    save_balance()
    await notify_balance_change(user_id, -cost, context)
    username = plan_info.get("username", "N/A")
    password = plan_info.get("password", "N/A")
    identifier = plan_info.get("identifier", "N/A")
    text = (f"✅ خرید {plan_info['name']} با موفقیت انجام شد.\n\n"
            f"💸 مبلغ کسر شده: {cost:,} تومان\n\n"
            "جزئیات اشتراک شما:\n"
            f"👤 یوزرنیم: {username}\n"
            f"🔑 پسورد: {password}\n"
            f"🔖 شناسه: {identifier}\n")
    await query.edit_message_text(text)
    record = {"type": "site_subscription", "plan": plan_key, "cost": cost, "timestamp": datetime.datetime.now()}
    purchase_history.setdefault(user_id, []).append(record)
    save_history()

# ------------------ توابع رسید و تایید خرید ------------------
async def receipt_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in pending_balance_requests:
        pending_balance_receipts[user_id] = update.message.photo[-1].file_id
        keyboard = [[InlineKeyboardButton("💳 ارسال درخواست افزایش موجودی", callback_data="balance_request_confirm")]]
        await update.message.reply_text("✅ عکس رسید دریافت شد. برای نهایی کردن درخواست افزایش موجودی روی دکمه مربوطه کلیک کنید.", reply_markup=InlineKeyboardMarkup(keyboard))
    elif user_id in pending_receipts:
        receipt_photos[user_id] = update.message.photo[-1].file_id
        keyboard = [[InlineKeyboardButton("قبول درخواست", callback_data="confirm_receipt")]]
        await update.message.reply_text("✅ عکس رسید دریافت شد. برای نهایی کردن خرید روی دکمه 'قبول درخواست' کلیک کنید.", reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in pending_receipts or user_id not in receipt_photos:
        await query.edit_message_text("❌ رسید شما یافت نشد. لطفاً ابتدا عکس رسید را ارسال کنید.")
        return
    purchase_info = pending_receipts[user_id]
    photo_file_id = receipt_photos[user_id]
    if purchase_info["type"] == "dns":
        caption = (f"خرید DNS اختصاصی\n"
                   f"لوکیشن: {DNS_CONFIGS[purchase_info['plan']]['name']}\n"
                   f"IPv4: <code>{purchase_info['ip1']}</code> - <code>{purchase_info['ip2']}</code>\n"
                   f"IPv6: <code>{purchase_info['ipv6_1']}</code> - <code>{purchase_info['ipv6_2']}</code>\n"
                   f"مبلغ: {purchase_info['cost']:,} تومان")
    else:
        caption = "نوع درخواست نامعتبر."
    for admin in admin_ids:
        try:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید خرید", callback_data=f"admin_approve_purchase_{user_id}"),
                                              InlineKeyboardButton("❌ رد خرید", callback_data=f"admin_reject_purchase_{user_id}")]])
            await context.bot.send_photo(chat_id=admin, photo=photo_file_id,
                                           caption=f"رسید پرداخت از کاربر {user_id}:\n{caption}",
                                           parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"خطا در ارسال رسید به ادمین {admin}: {e}")
    await query.edit_message_text("✅ رسید شما ارسال شد و در انتظار تایید ادمین می‌باشد.")

async def admin_approve_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) < 4:
        if query.message.photo:
            await query.edit_message_caption(caption="❌ داده‌های نامعتبر.")
        else:
            await query.edit_message_text("❌ داده‌های نامعتبر.")
        return
    try:
        user_id = int(parts[3])
    except ValueError:
        if query.message.photo:
            await query.edit_message_caption(caption="❌ خطا در پردازش اطلاعات کاربر.")
        else:
            await query.edit_message_text("❌ خطا در پردازش اطلاعات کاربر.")
        return
    if user_id not in pending_receipts:
        if query.message.photo:
            await query.edit_message_caption(caption="❌ درخواست خرید یافت نشد.")
        else:
            await query.edit_message_text("❌ درخواست خرید یافت نشد.")
        return
    del pending_receipts[user_id]
    if user_id in receipt_photos:
        del receipt_photos[user_id]
    try:
        await context.bot.send_message(chat_id=user_id, text="✅ خرید شما تایید شد.")
    except Exception as e:
        logger.error(f"خطا در ارسال پیام به کاربر {user_id}: {e}")
    if query.message.photo:
        await query.edit_message_caption(caption="✅ خرید تایید شد.")
    else:
        await query.edit_message_text("✅ خرید تایید شد.")

async def admin_reject_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) < 4:
        if query.message.photo:
            await query.edit_message_caption(caption="❌ داده‌های نامعتبر.")
        else:
            await query.edit_message_text("❌ داده‌های نامعتبر.")
        return
    try:
        user_id = int(parts[3])
    except ValueError:
        if query.message.photo:
            await query.edit_message_caption(caption="❌ خطا در پردازش اطلاعات کاربر.")
        else:
            await query.edit_message_text("❌ خطا در پردازش اطلاعات کاربر.")
        return
    if user_id not in pending_receipts:
        if query.message.photo:
            await query.edit_message_caption(caption="❌ درخواست خرید یافت نشد.")
        else:
            await query.edit_message_text("❌ درخواست خرید یافت نشد.")
        return
    purchase_info = pending_receipts[user_id]
    user_balance[user_id] = user_balance.get(user_id, 0) + purchase_info["cost"]
    save_balance()
    await notify_balance_change(user_id, purchase_info["cost"], context)
    try:
        await context.bot.send_message(chat_id=user_id,
                                       text="❌ خرید شما توسط ادمین رد شد. مبلغ کسر شده به حساب شما بازگردانده شد.")
    except Exception as e:
        logger.error(f"خطا در ارسال پیام به کاربر {user_id}: {e}")
    del pending_receipts[user_id]
    if user_id in receipt_photos:
        del receipt_photos[user_id]
    if query.message.photo:
        await query.edit_message_caption(caption="✅ خرید رد شد. مبلغ به حساب کاربر بازگردانده شد.")
    else:
        await query.edit_message_text("✅ خرید رد شد. مبلغ به حساب کاربر بازگردانده شد.")

# ------------------ توابع افزایش موجودی ------------------
async def balance_increase_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "💳 مقدار افزایش موجودی را انتخاب کنید (به تومان):"
    amounts = [40000, 50000, 60000, 100000, 200000, 500000, 1000000]
    keyboard = []
    row = []
    for amt in amounts:
        row.append(InlineKeyboardButton(f"{amt:,}", callback_data=f"balance_increase_{amt}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✏️ مبلغ دلخواه", callback_data="balance_increase_custom")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_custom_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    awaiting_custom_balance[query.from_user.id] = True
    await query.edit_message_text("✏️ لطفاً مبلغ دلخواه (به تومان) را به صورت عددی ارسال کنید:")

def show_balance_payment_screen(query, context, amount):
    text = (f"برای افزایش موجودی به مبلغ {amount:,} تومان، مبلغ را به حساب بانکی واریز کنید.\n\n"
            "💳 شماره کارت: <code>6037 9917 0465 7182</code>\n"
            "به نام: فریده قمری\n\n"
            "سپس رسید پرداخت را به صورت عکس ارسال کنید و روی دکمه '💳 ارسال درخواست افزایش موجودی' کلیک کنید.")
    keyboard = [[InlineKeyboardButton("💳 ارسال درخواست افزایش موجودی", callback_data="balance_request_confirm")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
    return text, InlineKeyboardMarkup(keyboard)

async def handle_balance_increase_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("balance_increase_"):
        parts = data.split("_")
        if len(parts) != 3:
            await query.edit_message_text("❌ خطا در انتخاب مبلغ.")
            return
        try:
            amount = int(parts[2])
        except ValueError:
            await query.edit_message_text("❌ مقدار نامعتبر.")
            return
        if amount < 10000 or amount > 1000000:
            await query.edit_message_text("❌ مقدار انتخاب شده خارج از محدوده مجاز است.")
            return
        pending_balance_requests[query.from_user.id] = amount
        text, reply_markup = show_balance_payment_screen(query, context, amount)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def balance_request_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in pending_balance_requests or user_id not in pending_balance_receipts:
        await query.edit_message_text("❌ لطفاً ابتدا عکس رسید پرداخت خود را ارسال کنید.")
        return
    amount = pending_balance_requests[user_id]
    photo_file_id = pending_balance_receipts[user_id]
    for admin in admin_ids:
        try:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید", callback_data=f"approve_balance_{user_id}_{amount}"),
                                              InlineKeyboardButton("❌ رد", callback_data=f"reject_balance_{user_id}_{amount}")]])
            await context.bot.send_photo(chat_id=admin, photo=photo_file_id,
                                           caption=f"درخواست افزایش موجودی از کاربر {user_id}:\nمبلغ: {amount:,} تومان",
                                           parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"خطا در ارسال رسید افزایش موجودی به ادمین {admin}: {e}")
    await query.edit_message_text("✅ درخواست افزایش موجودی شما ارسال شد و در انتظار تایید ادمین می‌باشد.")

async def approve_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) < 4:
        if query.message.photo:
            await query.edit_message_caption(caption="❌ داده‌های نامعتبر.")
        else:
            await query.edit_message_text("❌ داده‌های نامعتبر.")
        return
    try:
        user_id = int(parts[2])
        amount = int(parts[3])
    except Exception:
        if query.message.photo:
            await query.edit_message_caption(caption="❌ خطا در پردازش اطلاعات.")
        else:
            await query.edit_message_text("❌ خطا در پردازش اطلاعات.")
        return
    user_balance[user_id] = user_balance.get(user_id, 0) + amount
    save_balance()
    record = {"type": "balance_deposit", "amount": amount, "timestamp": datetime.datetime.now()}
    purchase_history.setdefault(user_id, []).append(record)
    save_history()
    if user_id in pending_balance_requests:
        del pending_balance_requests[user_id]
    if user_id in pending_balance_receipts:
        del pending_balance_receipts[user_id]
    if query.message.photo:
        await query.edit_message_caption(caption="✅ درخواست افزایش موجودی تایید شد. موجودی کاربر به حساب اضافه شد.")
    else:
        await query.edit_message_text("✅ درخواست افزایش موجودی تایید شد. موجودی کاربر به حساب اضافه شد.")
    await notify_balance_change(user_id, amount, context)
    try:
        await context.bot.send_message(chat_id=user_id, text="✅ درخواست افزایش موجودی شما تایید شد. موجودی به حساب شما اضافه شد.")
    except Exception as e:
        logger.error(f"Error notifying user {user_id}: {e}")

async def reject_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) < 4:
        if query.message.photo:
            await query.edit_message_caption(caption="❌ داده‌های نامعتبر.")
        else:
            await query.edit_message_text("❌ داده‌های نامعتبر.")
        return
    try:
        user_id = int(parts[2])
        amount = int(parts[3])
    except Exception:
        if query.message.photo:
            await query.edit_message_caption(caption="❌ خطا در پردازش اطلاعات.")
        else:
            await query.edit_message_text("❌ خطا در پردازش اطلاعات.")
        return
    if user_id in pending_balance_requests:
        del pending_balance_requests[user_id]
    if user_id in pending_balance_receipts:
        del pending_balance_receipts[user_id]
    if query.message.photo:
        await query.edit_message_caption(caption="✅ درخواست افزایش موجودی رد شد.")
    else:
        await query.edit_message_text("✅ درخواست افزایش موجودی رد شد.")
    try:
        await context.bot.send_message(chat_id=user_id, text="❌ درخواست افزایش موجودی شما رد شد.")
    except Exception as e:
        logger.error(f"Error notifying user {user_id}: {e}")

# ------------------ توابع حساب کاربری و رفرال ------------------
async def account_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    balance = user_balance.get(user_id, 0)
    points = referral_points.get(user_id, 0)
    text = (f"👤 حساب کاربری شما:\n\n"
            f"🆔 آیدی: <code>{user_id}</code>\n"
            f"💰 موجودی: {balance:,} تومان\n"
            f"⭐ امتیاز معرف: {points}\n\n")
    history = purchase_history.get(user_id, [])
    if history:
        text += f"✅ تعداد تراکنش‌های ثبت شده: {len(history)}\n\nآخرین تراکنش‌ها:\n"
        for rec in history[-3:]:
            ts = rec["timestamp"].strftime("%Y-%m-%d %H:%M") if isinstance(rec.get("timestamp"), datetime.datetime) else rec.get("timestamp", "N/A")
            if rec.get("type") in ["dns", "site_subscription"]:
                plan_name = DNS_CONFIGS.get(rec.get("plan"), {}).get("name", rec.get("plan"))
                text += f"• {plan_name} - {rec.get('cost',0):,} تومان - {ts}\n"
                text += f"  IPv4: <code>{rec.get('ip1','N/A')}</code>, <code>{rec.get('ip2','N/A')}</code>\n"
                text += f"  IPv6: <code>{rec.get('ipv6_1','N/A')}</code>, <code>{rec.get('ipv6_2','N/A')}</code>\n"
                if rec.get("discount"):
                    text += f"  تخفیف: {rec['discount']}\n"
            elif rec.get("type") == "balance_deposit":
                text += f"• افزایش موجودی: {rec.get('amount',0):,} تومان - {ts}\n"
            elif rec.get("type") == "balance_adjustment":
                text += f"• تغییر موجودی توسط ادمین ({rec.get('admin')}): {rec.get('amount',0):,} تومان - {ts}\n"
            text += "\n"
    else:
        text += "❌ تراکنشی ثبت نشده است.\n"
    if user_id in user_discount:
        code, percent = user_discount[user_id]
        text += f"\n🎟 کد تخفیف موجود: {code} - {percent}% تخفیف\n"
    keyboard = [[InlineKeyboardButton("🎟 اعمال کد تخفیف", callback_data="apply_discount")],
                [InlineKeyboardButton("🔗 رفرال و امتیاز", callback_data="referral_menu")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    points = referral_points.get(user_id, 0)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    text = (f"🔗 اطلاعات رفرال:\n\n"
            f"⭐ امتیاز فعلی: {points}\n"
            f"🔗 لینک معرف: {referral_link}\n\n"
            "هر کاربر جدیدی که با استفاده از لینک معرف وارد ربات شود، به شما 1 امتیاز تعلق می‌گیرد.\n"
            "همچنین می‌توانید امتیازهای خود را با نرخ 1 امتیاز = 1000 تومان به موجودی تبدیل کنید.")
    keyboard = [[InlineKeyboardButton("💰 تبدیل امتیاز به موجودی", callback_data="convert_referral")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def apply_discount_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    awaiting_discount_code[query.from_user.id] = True
    await query.edit_message_text("✏️ لطفاً کد تخفیف خود را ارسال کنید:")

async def handle_discount_code_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    code = update.message.text.strip().upper()
    discount = None
    if code in discount_codes:
        discount = discount_codes[code]
    elif code in temp_discount_codes:
        expiration = temp_discount_codes[code]["expiration"]
        if datetime.datetime.now() < expiration:
            discount = temp_discount_codes[code]["discount"]
        else:
            del temp_discount_codes[code]
    if discount is not None:
        user_discount[user_id] = (code, discount)
        await update.message.reply_text(f"✅ کد تخفیف {code} با {discount}% تخفیف اعمال شد.")
    else:
        await update.message.reply_text("❌ کد تخفیف نامعتبر است.")
    if user_id in awaiting_discount_code:
        del awaiting_discount_code[user_id]

# ------------------ توابع پنل ادمین ------------------
async def notify_all_users(context: ContextTypes.DEFAULT_TYPE) -> None:
    success_count = 0
    fail_count = 0
    for user_id in all_users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🔔 ربات بروزرسانی شد!\n\nبرای مشاهده امکانات جدید به ربات مراجعه کنید."
            )
            success_count += 1
        except Exception:
            fail_count += 1
    return success_count, fail_count

async def admin_panel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    if admin_id not in admin_ids:
        await query.edit_message_text("❌ دسترسی ندارید.")
        return
    text = "⚙️ پنل ادمین:"
    keyboard = [
        [InlineKeyboardButton("🔔 نوتیفیکیشن", callback_data="admin_send_update"),
         InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_mass_message"),
         InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_user_stats")],
        [InlineKeyboardButton("💰 مدیریت موجودی", callback_data="admin_pending_balance"),
         InlineKeyboardButton("💸 تغییر موجودی", callback_data="admin_modify_balance"),
         InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="admin_change_card")],
        [InlineKeyboardButton("🚫 مسدودسازی", callback_data="admin_block_user"),
         InlineKeyboardButton("✅ رفع مسدودی", callback_data="admin_unblock_user"),
         InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user")],
        [InlineKeyboardButton("🔒 جویین اجباری", callback_data="admin_toggle_force_join"),
         InlineKeyboardButton("📝 تنظیم کانال", callback_data="admin_set_force_channel"),
         InlineKeyboardButton("⚙️ تنظیم دکمه‌ها", callback_data="admin_toggle_buttons_menu")],
        [InlineKeyboardButton("➕ افزودن ادمین", callback_data="admin_add_admin"),
         InlineKeyboardButton("➖ حذف ادمین", callback_data="admin_remove_admin"),
         InlineKeyboardButton("🆔 تغییر پشتیبانی", callback_data="admin_change_support")],
        [InlineKeyboardButton("📝 ویرایش قوانین", callback_data="admin_edit_terms"),
         InlineKeyboardButton("💸 تغییر قیمت‌ها", callback_data="admin_change_button_prices")],
        [InlineKeyboardButton("💰 هدیه موجودی", callback_data="admin_gift_all"),
         InlineKeyboardButton("⭐ تغییر امتیاز", callback_data="admin_modify_referral"),
         InlineKeyboardButton("🎫 کد تخفیف", callback_data="admin_add_temp_discount")],
        [InlineKeyboardButton("➕ دکمه جدید", callback_data="admin_add_custom_button"),
         InlineKeyboardButton("🔄 بروزرسانی", callback_data="toggle_update_mode")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_toggle_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global FORCE_JOIN_ENABLED
    query = update.callback_query
    await query.answer()
    FORCE_JOIN_ENABLED = not FORCE_JOIN_ENABLED
    status = "فعال" if FORCE_JOIN_ENABLED else "غیرفعال"
    await query.edit_message_text(
        f"جویین اجباری کانال به {status} تغییر یافت.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel_menu")]])
    )

async def admin_change_button_prices_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "💸 تغییر قیمت دکمه‌ها:\nلطفاً یکی از موارد زیر را انتخاب کنید:"
    buttons = []
    for plan_id, config in DNS_CONFIGS.items():
        buttons.append(InlineKeyboardButton(f"DNS ({config['name']}) - {config['price']:,} تومان", callback_data=f"change_price_dns_{plan_id}"))
    buttons.append(InlineKeyboardButton(f"وایرگارد - {WIREGUARD_PRICE:,} تومان", callback_data="change_price_wireguard_default"))
    for plan_key, plan_info in SITE_SUBSCRIPTION_PLANS.items():
        buttons.append(InlineKeyboardButton(f"اشتراک {plan_info['name']} - {plan_info['price']:,} تومان", callback_data=f"change_price_site_{plan_key}"))
    keyboard = InlineKeyboardMarkup([[b] for b in buttons] + [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel_menu")]])
    await query.edit_message_text(text, reply_markup=keyboard)

async def admin_change_button_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) < 3:
        await query.edit_message_text("❌ داده‌های نامعتبر.")
        return
    product_type = parts[2]
    product_key = parts[3] if len(parts) >= 4 else "default"
    admin_state[query.from_user.id] = {"operation": "change_button_price", "product_type": product_type, "product_key": product_key}
    await query.edit_message_text("✏️ لطفاً قیمت جدید (به تومان) را وارد کنید:")

async def admin_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lines = []
    lines.append("=== آمار جامع کاربران ===")
    for uid in sorted(all_users):
        try:
            chat = await context.bot.get_chat(uid)
            username = chat.username if chat.username else "-"
        except Exception:
            username = "-"
        balance_val = user_balance.get(uid, 0)
        ref_points = referral_points.get(uid, 0)
        history = purchase_history.get(uid, [])
        lines.append("---------------------------------")
        lines.append(f"آیدی: {uid} | یوزرنیم: {username}")
        lines.append(f"موجودی: {balance_val:,} تومان | امتیاز: {ref_points}")
        lines.append(f"تعداد تراکنش‌ها: {len(history)}")
        if history:
            for rec in history:
                ts = rec.get("timestamp")
                if isinstance(ts, datetime.datetime):
                    ts = ts.strftime("%Y-%m-%d %H:%M")
                rec_str = f"نوع: {rec.get('type')}, "
                if rec.get("type") in ["dns", "site_subscription"]:
                    rec_str += f"مبلغ: {rec.get('cost', 0):,} تومان, "
                    if rec.get("plan"):
                        plan_name = DNS_CONFIGS.get(rec.get("plan"), {}).get("name", rec.get("plan"))
                        rec_str += f"پلن: {plan_name}, "
                    if rec.get("discount"):
                        rec_str += f"تخفیف: {rec.get('discount')}, "
                elif rec.get("type") == "balance_deposit":
                    rec_str += f"مبلغ: {rec.get('amount', 0):,} تومان (افزایش موجودی), "
                elif rec.get("type") == "balance_adjustment":
                    rec_str += f"مبلغ: {rec.get('amount', 0):,} تومان (تغییر توسط ادمین {rec.get('admin')}), "
                rec_str += f"زمان: {ts}"
                lines.append("  - " + rec_str)
    text = "\n".join(lines)
    stats_file = os.path.join(DATA_DIR, "user_stats.txt")
    with open(stats_file, "w", encoding="utf-8") as f:
        f.write(text)
    bio = io.BytesIO(text.encode("utf-8"))
    bio.name = "detailed_user_stats.txt"
    await query.edit_message_text("در حال ارسال آمار جامع کاربران...")
    await context.bot.send_document(chat_id=query.from_user.id, document=bio, filename="detailed_user_stats.txt", caption="آمار جامع کاربران")

async def admin_add_temp_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "add_temp_discount"}
    await query.edit_message_text("✏️ لطفاً کد تخفیف تایمی، درصد تخفیف و مدت زمان (به ساعت) را به صورت زیر وارد کنید:\nCODE,percent,hours")

async def admin_change_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "change_support"}
    await query.edit_message_text("✏️ لطفاً آیدی پشتیبانی جدید (مثلاً @NewSupportID) را ارسال کنید:")

async def admin_set_force_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "set_force_channel"}
    await query.edit_message_text("✏️ لطفاً کانال اجباری را وارد کنید:")

async def admin_edit_terms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "update_terms"}
    await query.edit_message_text("✏️ لطفاً قوانین و مقررات جدید را ارسال کنید:")

async def admin_toggle_buttons_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "⚙️ تنظیم دکمه‌های منوی اصلی:\nانتخاب کنید کدام دکمه‌ها فعال/غیرفعال باشند."
    keyboard = [
         [InlineKeyboardButton("🛒 خرید DNS اختصاصی", callback_data="toggle_dns")],
         [InlineKeyboardButton("👤 حساب کاربری", callback_data="toggle_account")],
         [InlineKeyboardButton("💳 افزایش موجودی", callback_data="toggle_balance")],
         [InlineKeyboardButton("🔗 رفرال و امتیاز", callback_data="toggle_referral")],
         [InlineKeyboardButton("🔑 وایرگارد اختصاصی", callback_data="toggle_wireguard")],
         [InlineKeyboardButton("💻 خرید یوزرپسورد سایت", callback_data="toggle_site_subscription")],
         [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_pending_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not pending_balance_requests:
        await query.edit_message_text("❌ هیچ درخواست افزایش موجودی معلقی وجود ندارد.")
        return
    text = "💳 درخواست‌های افزایش موجودی:\n"
    for uid, amt in pending_balance_requests.items():
        text += f"User {uid}: {amt:,} تومان\n"
    await query.edit_message_text(text)

async def toggle_update_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global BOT_UPDATING
    query = update.callback_query
    await query.answer()
    BOT_UPDATING = not BOT_UPDATING
    status = "بروزرسانی" if BOT_UPDATING else "فعال"
    await query.edit_message_text(f"✅ حالت بروزرسانی ربات به {status} تغییر یافت.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel_menu")]]))

import base64
import os
import secrets

def generate_wireguard_keys():
    private_key = base64.b64encode(secrets.token_bytes(32)).decode()
    # Simulate public key generation (in real implementation, this would use actual WireGuard key generation)
    public_key = base64.b64encode(secrets.token_bytes(32)).decode()
    return private_key, public_key

def generate_wireguard_config(location: str, client_private_key: str, server_public_key: str):
    location_config = DNS_CONFIGS.get(location, {})
    if not location_config:
        return None

    # Generate random IPs from WireGuard CIDR ranges
    cidr_ranges = WIREGUARD_RANGES.get(location, {}).get("cidr_ranges", [])
    if not cidr_ranges:
        return None

    endpoint_ip = None
    dns_ips = []
    for cidr in cidr_ranges:
        network = ipaddress.ip_network(cidr)
        ip = str(ipaddress.ip_address(random.randint(
            int(network.network_address) + 1,
            int(network.broadcast_address) - 1
        )))
        if not endpoint_ip:
            endpoint_ip = ip
        elif len(dns_ips) < 2:
            dns_ips.append(ip)

    if not endpoint_ip or len(dns_ips) < 2:
        return None

    config = f"""[Interface]
PrivateKey = {client_private_key}
Address = 10.202.10.10/32
DNS = 78.157.42.100, {dns_ips[0]}, {dns_ips[1]}
MTU = 1400

[Peer]
PublicKey = {server_public_key}
Endpoint = {endpoint_ip}:443
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 35"""

    suggestions = """پیشنهادات برای بهبود عملکرد:
1. پورت‌های جایگزین: 51820, 1194, 1196
2. تنظیمات MTU جایگزین: 1250, 1300, 1450"""

    return config, suggestions

async def wireguard_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    text = "🔑 خرید کانفیگ وایرگارد:\n\nلطفاً لوکیشن مورد نظر را انتخاب کنید:"
    keyboard = []
    for location in ["آلمان1", "روسیه", "امارات", "ایتالیا", "ترکیه", "آمریکا"]:
        if location in DNS_CONFIGS:
            price = WIREGUARD_PRICE
            keyboard.append([InlineKeyboardButton(
                f"{DNS_CONFIGS[location]['flag']} {DNS_CONFIGS[location]['name']} - {price:,} تومان",
                callback_data=f"buy_wireguard_{location}"
            )])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def process_wireguard_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    location = query.data.split("_")[2]
    user_id = query.from_user.id

    if user_balance.get(user_id, 0) < WIREGUARD_PRICE:
        await query.edit_message_text(
            "❌ موجودی شما کافی نیست. لطفاً ابتدا موجودی خود را افزایش دهید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="wireguard_menu")]])
        )
        return

    # Generate keys and config
    private_key, public_key = generate_wireguard_keys()
    config_result = generate_wireguard_config(location, private_key, public_key)

    if not config_result:
        await query.edit_message_text(
            "❌ خطا در تولید کانفیگ. لطفاً دوباره تلاش کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="wireguard_menu")]])
        )
        return

    config, suggestions = config_result

    # Generate random string for filename
    random_str = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=6))
    config_filename = f"WG-{random_str}.conf"

    # Create config file in memory
    config_bytes = config.encode('utf-8')
    config_io = io.BytesIO(config_bytes)
    config_io.name = config_filename

    # Update user balance
    user_balance[user_id] = user_balance.get(user_id, 0) - WIREGUARD_PRICE
    save_balance()

    # Save purchase history
    record = {
        "type": "wireguard",
        "location": location,
        "cost": WIREGUARD_PRICE,
        "timestamp": datetime.datetime.now()
    }
    purchase_history.setdefault(user_id, []).append(record)
    save_history()

    # Send config file with caption
    caption = f"✅ کانفیگ وایرگارد شما برای {DNS_CONFIGS[location]['name']}:\n\n{suggestions}"

    try:
        await context.bot.send_document(
            chat_id=user_id,
            document=config_io,
            caption=caption,
            filename=config_filename
        )
        await query.edit_message_text(
            "✅ خرید با موفقیت انجام شد. کانفیگ برای شما ارسال شد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="wireguard_menu")]])
        )
    except Exception as e:
        logger.error(f"Error sending wireguard config: {e}")
        await query.edit_message_text(
            "❌ خطا در ارسال کانفیگ. لطفاً با پشتیبانی تماس بگیرید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="wireguard_menu")]])
        )

async def admin_add_admin_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "add_admin"}
    await query.edit_message_text("✏️ لطفاً آیدی کاربر جدید را به صورت عددی ارسال کنید:")

async def admin_remove_admin_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "remove_admin"}
    await query.edit_message_text("✏️ لطفاً آیدی کاربر مورد نظر برای حذف از ادمین‌ها به صورت عددی ارسال کنید:")

async def admin_search_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "search_user"}
    await query.edit_message_text("✏️ لطفاً آیدی کاربر مورد نظر را به صورت عددی ارسال کنید:")

async def admin_modify_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    if admin_id not in admin_ids:
        await query.edit_message_text("❌ دسترسی ندارید.")
        return
    admin_state[admin_id] = {"operation": "modify_balance", "step": "awaiting_user_id"}
    await query.edit_message_text("✏️ لطفاً آیدی کاربر مورد نظر را (به صورت عددی) ارسال کنید.\nبرای انصراف، /cancel را بزنید.")

async def admin_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    if admin_id not in admin_ids:
        await query.edit_message_text("❌ دسترسی ندارید.")
        return
    admin_state[admin_id] = {"operation": "block_user"}
    await query.edit_message_text("🚫 لطفاً آیدی کاربر مورد نظر برای مسدودسازی را ارسال کنید.")

async def admin_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    if admin_id not in admin_ids:
        await query.edit_message_text("❌ دسترسی ندارید.")
        return
    admin_state[admin_id] = {"operation": "unblock_user"}
    await query.edit_message_text("✅ لطفاً آیدی کاربر مورد نظر برای لغو مسدودسازی را ارسال کنید.")

async def admin_mass_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    if admin_id not in admin_ids:
        await query.edit_message_text("❌ دسترسی ندارید.")
        return
    admin_state[admin_id] = {"operation": "mass_message"}
    await query.edit_message_text("📢 لطفاً متن پیام همگانی را ارسال کنید.")

async def admin_gift_all_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "gift_all_balance"}
    await query.edit_message_text("✏️ لطفاً مبلغ هدیه (به تومان) را وارد کنید:")

async def admin_modify_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "modify_referral"}
    await query.edit_message_text("✏️ لطفاً آیدی کاربر و امتیاز جدید را به صورت زیر وارد کنید:\nUserID,NewPoints")

async def admin_change_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "change_card"}
    await query.edit_message_text("✏️ لطفاً شماره کارت و نام صاحب کارت را به صورت زیر وارد کنید:\nشماره کارت,نام صاحب کارت")

async def admin_add_custom_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_state[query.from_user.id] = {"operation": "add_custom_button"}
    text = ("✏️ لطفاً نام دکمه، نوع محتوا (file/text) و قیمت را به صورت زیر وارد کنید:\n"
            "نام دکمه,نوع محتوا,قیمت\n"
            "مثال: آموزش نصب,text,5000")
    await query.edit_message_text(text)

async def custom_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    btn_name = data.split("_", 1)[1]
    if btn_name in custom_buttons:
        file_id = custom_buttons[btn_name]
        try:
            await context.bot.send_document(chat_id=query.from_user.id, document=file_id, caption=f"📄 این فایل برای دکمه '{btn_name}' است.")
        except Exception as e:
            await query.edit_message_text("❌ خطا در ارسال فایل.")
    else:
        await query.edit_message_text("❌ فایل مربوط به این دکمه یافت نشد.")

# ------------------ توابع پیام متنی ------------------
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id in awaiting_custom_balance:
        try:
            amount = int(text)
            if amount < 10000 or amount > 1000000:
                await update.message.reply_text("❌ مقدار انتخاب شده خارج از محدوده مجاز است.")
                return
            pending_balance_requests[user_id] = amount
            del awaiting_custom_balance[user_id]
            payment_text = (f"برای افزایش موجودی به مبلغ {amount:,} تومان، مبلغ را به حساب بانکی واریز کنید.\n\n"
                            "💳 شماره کارت: <code>6219 8619 4308 4037</code>\n"
                            "به نام: فریده قمری\n\n"
                            "سپس رسید پرداخت را به صورت عکس ارسال کنید و روی دکمه '💳 ارسال درخواست افزایش موجودی' کلیک کنید.")
            keyboard = [[InlineKeyboardButton("💳 ارسال درخواست افزایش موجودی", callback_data="balance_request_confirm")],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
            await update.message.reply_text(payment_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except ValueError:
            await update.message.reply_text("❌ مقدار وارد شده معتبر نیست.")
        return
    if user_id in awaiting_dns_discount:
        plan_id = awaiting_dns_discount[user_id]
        code = text.upper()
        discount = None
        if code in discount_codes:
            discount = discount_codes[code]
        elif code in temp_discount_codes:
            expiration = temp_discount_codes[code]["expiration"]
            if datetime.datetime.now() < expiration:
                discount = temp_discount_codes[code]["discount"]
            else:
                del temp_discount_codes[code]
        if discount is not None:
            user_discount[user_id] = (code, discount)
            await update.message.reply_text(f"✅ کد تخفیف {code} با {discount}% تخفیف اعمال شد.")
        else:
            await update.message.reply_text("❌ کد تخفیف نامعتبر است.")
        del awaiting_dns_discount[user_id]
        await update.message.reply_text("حال خرید نهایی انجام خواهد شد. لطفاً از منوی خرید DNS اقدام کنید.")
        return
    if user_id in admin_state:
        state = admin_state[user_id]
        operation = state.get("operation")
        if operation == "modify_balance":
            if state.get("step") == "awaiting_user_id":
                try:
                    target_user = int(text)
                    admin_state[user_id]["target_user"] = target_user
                    admin_state[user_id]["step"] = "awaiting_amount"
                    await update.message.reply_text("✏️ لطفاً مبلغ تغییر موجودی (مثبت یا منفی) را وارد کنید:")
                except ValueError:
                    await update.message.reply_text("❌ آیدی معتبر نیست. لطفاً عدد وارد کنید.")
            elif state.get("step") == "awaiting_amount":
                try:
                    amount = int(text)
                    target_user = admin_state[user_id].get("target_user")
                    if target_user is None:
                        await update.message.reply_text("❌ خطا در دریافت آیدی کاربر.")
                        del admin_state[user_id]
                        return
                    user_balance[target_user] = user_balance.get(target_user, 0) + amount
                    save_balance()
                    record = {"type": "balance_adjustment", "amount": amount, "timestamp": datetime.datetime.now(), "admin": user_id}
                    purchase_history.setdefault(target_user, []).append(record)
                    save_history()
                    await update.message.reply_text(f"✅ موجودی کاربر {target_user} تغییر یافت. مبلغ تغییر: {amount:,} تومان")
                    await notify_balance_change(target_user, amount, context)
                    del admin_state[user_id]
                except ValueError:
                    await update.message.reply_text("❌ مقدار وارد شده معتبر نیست. لطفاً عدد وارد کنید.")
            return
        elif operation == "block_user":
            try:
                target_user = int(text)
                await update.message.reply_text(f"🚫 کاربر {target_user} مسدود شد.")
                del admin_state[user_id]
            except ValueError:
                await update.message.reply_text("❌ آیدی معتبر نیست.")
            return
        elif operation == "unblock_user":
            try:
                target_user = int(text)
                await update.message.reply_text(f"✅ کاربر {target_user} از لیست مسدود شده‌ها حذف شد.")
                del admin_state[user_id]
            except ValueError:
                await update.message.reply_text("❌ آیدی معتبر نیست.")
            return
        elif operation == "mass_message":
            message_text = text
            count = 0
            for uid in all_users:
                try:
                    await context.bot.send_message(chat_id=uid, text=message_text)
                    count += 1
                except Exception as e:
                    logger.error(f"Error sending mass message to {uid}: {e}")
            await update.message.reply_text(f"✅ پیام همگانی ارسال شد به {count} کاربر.")
            del admin_state[user_id]
            return
        elif operation == "set_force_channel":
            global FORCE_JOIN_CHANNEL
            FORCE_JOIN_CHANNEL = text
            await update.message.reply_text(f"✅ کانال اجباری تنظیم شد: {FORCE_JOIN_CHANNEL}")
            del admin_state[user_id]
            return
        elif operation == "update_terms":
            global TERMS_TEXT
            TERMS_TEXT = text
            await update.message.reply_text("✅ قوانین و مقررات به‌روزرسانی شد.")
            del admin_state[user_id]
            return
        elif operation == "change_button_price":
            try:
                new_price = int(text)
                product_type = state.get("product_type")
                product_key = state.get("product_key")
                if product_type == "dns":
                    if product_key in DNS_CONFIGS:
                        DNS_CONFIGS[product_key]["price"] = new_price
                        await update.message.reply_text(f"✅ قیمت DNS ({DNS_CONFIGS[product_key]['name']}) به {new_price:,} تومان تغییر یافت.")
                    else:
                        await update.message.reply_text("❌ پلن DNS نامعتبر.")
                elif product_type == "wireguard":
                    global WIREGUARD_PRICE
                    WIREGUARD_PRICE = new_price
                    await update.message.reply_text(f"✅ قیمت وایرگارد به {new_price:,} تومان تغییر یافت.")
                elif product_type == "site":
                    if product_key in SITE_SUBSCRIPTION_PLANS:
                        SITE_SUBSCRIPTION_PLANS[product_key]["price"] = new_price
                        await update.message.reply_text(f"✅ قیمت اشتراک {SITE_SUBSCRIPTION_PLANS[product_key]['name']} به {new_price:,} تومان تغییر یافت.")
                    else:
                        await update.message.reply_text("❌ پلن اشتراک نامعتبر.")
                else:
                    await update.message.reply_text("❌ نوع محصول نامعتبر.")
                del admin_state[user_id]
            except ValueError:
                await update.message.reply_text("❌ مقدار وارد شده معتبر نیست. لطفاً عدد وارد کنید.")
            return
        elif operation == "change_support":
            global SUPPORT_ID
            SUPPORT_ID = text.strip()
            await update.message.reply_text(f"✅ آیدی پشتیبانی به {SUPPORT_ID} تغییر یافت.")
            del admin_state[user_id]
            return
        elif operation == "add_temp_discount":
            try:
                parts = text.split(",")
                if len(parts) != 3:
                    await update.message.reply_text("❌ فرمت وارد شده نادرست است. فرمت صحیح: CODE,percent,hours")
                else:
                    code_str = parts[0].strip().upper()
                    percent = int(parts[1].strip())
                    hours = int(parts[2].strip())
                    expiration = datetime.datetime.now() + datetime.timedelta(hours=hours)
                    temp_discount_codes[code_str] = {"discount": percent, "expiration": expiration}
                    await update.message.reply_text(f"✅ کد تخفیف تایمی {code_str} با {percent}% تخفیف و اعتبار {hours} ساعت ثبت شد.")
                del admin_state[user_id]
            except Exception:
                await update.message.reply_text("❌ خطا در ثبت کد تخفیف تایمی.")
                del admin_state[user_id]
            return
        elif operation == "add_admin":
            try:
                new_admin = int(text)
                admin_ids.add(new_admin)
                save_admin_ids()
                await update.message.reply_text(f"✅ کاربر {new_admin} به عنوان ادمین اضافه شد.")
            except ValueError:
                await update.message.reply_text("❌ آیدی معتبر نیست.")
            del admin_state[user_id]
            return
        elif operation == "remove_admin":
            try:
                rem_admin = int(text)
                if rem_admin in admin_ids:
                    admin_ids.remove(rem_admin)
                    save_admin_ids()
                    await update.message.reply_text(f"✅ کاربر {rem_admin} از لیست ادمین‌ها حذف شد.")
                else:
                    await update.message.reply_text("❌ کاربر مورد نظر در لیست ادمین‌ها یافت نشد.")
            except ValueError:
                await update.message.reply_text("❌ آیدی معتبر نیست.")
            del admin_state[user_id]
            return
        elif operation == "search_user":
            try:
                target_user = int(text)
                balance = user_balance.get(target_user, 0)
                points = referral_points.get(target_user, 0)
                history = purchase_history.get(target_user, [])
                user_info = f"👤 اطلاعات کاربر {target_user}:\n"
                user_info += f"💰 موجودی: {balance:,} تومان\n"
                user_info += f"⭐ امتیاز: {points}\n"
                user_info += f"📝 تعداد تراکنش‌ها: {len(history)}\n"
                if history:
                    for rec in history:
                        ts = rec.get("timestamp")
                        if isinstance(ts, datetime.datetime):
                            ts = ts.strftime("%Y-%m-%d %H:%M")
                        user_info += f" - نوع: {rec.get('type')}, مبلغ/قیمت: {rec.get('cost', rec.get('amount', 'N/A')):,} , زمان: {ts}\n"
                else:
                    user_info += " - هیچ تراکنش ثبت نشده است.\n"
                await update.message.reply_text(user_info)
            except ValueError:
                await update.message.reply_text("❌ آیدی معتبر نیست.")
            del admin_state[user_id]
            return
        elif operation == "gift_all_balance":
            try:
                gift_amount = int(text)
                for uid in all_users:
                    user_balance[uid] = user_balance.get(uid, 0) + gift_amount
                    record = {"type": "balance_deposit", "amount": gift_amount, "timestamp": datetime.datetime.now(), "admin": user_id, "gift": True}
                    purchase_history.setdefault(uid, []).append(record)
                save_balance()
                save_history()
                await update.message.reply_text(f"✅ موجودی تمامی کاربران به میزان {gift_amount:,} تومان افزایش یافت (هدیه).")
            except ValueError:
                await update.message.reply_text("❌ مقدار وارد شده معتبر نیست.")
            del admin_state[user_id]
            return
        elif operation == "modify_referral":
            try:
                parts = text.split(",")
                if len(parts) != 2:
                    await update.message.reply_text("❌ فرمت وارد شده نادرست است. فرمت صحیح: UserID,NewPoints")
                else:
                    target_user = int(parts[0].strip())
                    new_points = int(parts[1].strip())
                    referral_points[target_user] = new_points
                    await update.message.reply_text(f"✅ امتیاز کاربر {target_user} به {new_points} تغییر یافت.")
            except Exception:
                await update.message.reply_text("❌ خطا در تغییر امتیاز رفرال.")
            del admin_state[user_id]
            return
        elif operation == "change_card":
            try:
                parts = text.split(",")
                if len(parts) != 2:
                    await update.message.reply_text("❌ فرمت نادرست. مثال صحیح: 6219-8619-4308-4037,نام صاحب کارت")
                    return
                card_number = parts[0].strip()
                card_name = parts[1].strip()
                CARD_NUMBERS["default"] = {"number": card_number, "name": card_name}
                await update.message.reply_text(f"✅ شماره کارت با موفقیت به\n{card_number}\nبه نام {card_name}\nتغییر یافت.")
            except Exception:
                await update.message.reply_text("❌ خطا در تغییر شماره کارت.")
            del admin_state[user_id]
            return

        elif operation == "add_custom_button":
            try:
                parts = text.split(",")
                if len(parts) != 3:
                    await update.message.reply_text("❌ فرمت نادرست. مثال صحیح: نام دکمه,نوع محتوا,قیمت")
                    return
                btn_name = parts[0].strip()
                content_type = parts[1].strip().lower()
                price = int(parts[2].strip())

                if content_type not in ["file", "text"]:
                    await update.message.reply_text("❌ نوع محتوا باید file یا text باشد.")
                    return

                admin_state[user_id] = {
                    "operation": "upload_custom_button",
                    "button_name": btn_name,
                    "content_type": content_type,
                    "price": price
                }

                if content_type == "text":
                    await update.message.reply_text("✏️ لطفاً متن مورد نظر را ارسال کنید:")
                else:
                    await update.message.reply_text("✏️ لطفاً فایل مورد نظر را ارسال کنید:")
            except ValueError:
                await update.message.reply_text("❌ قیمت وارد شده معتبر نیست.")
            return
        elif operation == "upload_custom_button":
            btn_name = state.get("button_name")
            if update.message.document:
                file_id = update.message.document.file_id
                custom_buttons[btn_name] = file_id
                await update.message.reply_text(f"✅ دکمه '{btn_name}' با موفقیت اضافه شد.")
            else:
                await update.message.reply_text("❌ لطفاً یک فایل معتبر ارسال کنید.")
            del admin_state[user_id]
            return
    if user_id in awaiting_discount_code:
        await handle_discount_code_text(update, context)
        return
    await update.message.reply_text("❌ دستور نامعتبر یا موردی جهت پردازش یافت نشد.")

# ------------------ دستورات اصلی ------------------
def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in admin_ids:
        if context.args and context.args[0] == ADMIN_PASSWORD:
            admin_ids.add(user_id)
            save_admin_ids()
            update.message.reply_text("✅ شما به عنوان ادمین ثبت شدید.")
        else:
            update.message.reply_text("❌ دسترسی غیرمجاز. برای ورود رمز عبور را همراه /admin ارسال کنید. مثال: /admin 1")
            return
    keyboard = [[InlineKeyboardButton("⚙️ پنل ادمین", callback_data="admin_panel_menu")]]
    update.message.reply_text("به پنل ادمین خوش آمدید.", reply_markup=InlineKeyboardMarkup(keyboard))

def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_id = update.effective_user.id
    if admin_id in admin_state:
        del admin_state[admin_id]
    update.message.reply_text("❌ عملیات لغو شد.")

def convert_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    points = referral_points.get(user_id, 0)
    if points > 0:
        credit = points * 1000
        user_balance[user_id] = user_balance.get(user_id, 0) + credit
        save_balance()
        referral_points[user_id] = 0
        query.edit_message_text(f"✅ {points} امتیاز به مبلغ {credit:,} تومان به موجودی شما اضافه شد.")
        asyncio.create_task(notify_balance_change(user_id, credit, context))
    else:
        query.edit_message_text("❌ امتیاز کافی برای تبدیل موجودی ندارید.")

# ------------------ توابع مربوط به تغییر وضعیت دکمه‌های منوی اصلی ------------------
async def toggle_dns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global ENABLE_DNS_BUTTON
    query = update.callback_query
    await query.answer()
    ENABLE_DNS_BUTTON = not ENABLE_DNS_BUTTON
    status = "فعال" if ENABLE_DNS_BUTTON else "غیرفعال"
    await query.edit_message_text(f"✅ وضعیت خرید DNS به {status} تغییر یافت.", 
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_toggle_buttons_menu")]]))

async def toggle_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global ENABLE_ACCOUNT_BUTTON
    query = update.callback_query
    await query.answer()
    ENABLE_ACCOUNT_BUTTON = not ENABLE_ACCOUNT_BUTTON
    status = "فعال" if ENABLE_ACCOUNT_BUTTON else "غیرفعال"
    await query.edit_message_text(f"✅ وضعیت حساب کاربری به {status} تغییر یافت.", 
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_toggle_buttons_menu")]]))

async def toggle_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global ENABLE_BALANCE_BUTTON
    query = update.callback_query
    await query.answer()
    ENABLE_BALANCE_BUTTON = not ENABLE_BALANCE_BUTTON
    status = "فعال" if ENABLE_BALANCE_BUTTON else "غیرفعال"
    await query.edit_message_text(f"✅ وضعیت افزایش موجودی به {status} تغییر یافت.", 
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_toggle_buttons_menu")]]))

async def toggle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global ENABLE_REFERRAL_BUTTON
    query = update.callback_query
    await query.answer()
    ENABLE_REFERRAL_BUTTON = not ENABLE_REFERRAL_BUTTON
    status = "فعال" if ENABLE_REFERRAL_BUTTON else "غیرفعال"
    await query.edit_message_text(f"✅ وضعیت رفرال به {status} تغییر یافت.", 
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_toggle_buttons_menu")]]))

async def toggle_wireguard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global ENABLE_WIREGUARD_BUTTON
    query = update.callback_query
    await query.answer()
    ENABLE_WIREGUARD_BUTTON = not ENABLE_WIREGUARD_BUTTON
    status = "فعال" if ENABLE_WIREGUARD_BUTTON else "غیرفعال"
    await query.edit_message_text(f"✅ وضعیت وایرگارد به {status} تغییر یافت.", 
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_toggle_buttons_menu")]]))

async def toggle_site_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global ENABLE_SITE_SUBSCRIPTION_BUTTON
    query = update.callback_query
    await query.answer()
    ENABLE_SITE_SUBSCRIPTION_BUTTON = not ENABLE_SITE_SUBSCRIPTION_BUTTON
    status = "فعال" if ENABLE_SITE_SUBSCRIPTION_BUTTON else "غیرفعال"
    await query.edit_message_text(f"✅ وضعیت خرید سایت به {status} تغییر یافت.", 
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_toggle_buttons_menu")]]))

# ------------------ تابع main ------------------
async def verify_phone_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # حذف پیام قبلی
    await query.message.delete()

    keyboard = [[KeyboardButton("📱 ارسال شماره تلفن", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await query.message.reply_text(
        "📱 برای تایید شماره تلفن، لطفاً روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contact = update.message.contact
    user_id = update.effective_user.id

    if contact.user_id != user_id:
        await update.message.reply_text(
            "❌ لطفاً فقط شماره تلفن خود را ارسال کنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    phone = contact.phone_number
    if phone.startswith("0098"):
        phone = "+" + phone[2:]
    elif not phone.startswith("+"):
        phone = "+" + phone

    if not is_valid_iranian_phone(phone):
        await update.message.reply_text(
            "❌ شماره تلفن معتبر نیست. لطفاً از شماره ایران (+98) استفاده کنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # Check if phone is already verified by another user
    for uid, data in verified_phones.items():
        if uid != user_id and data.get("phone") == phone:
            await update.message.reply_text(
                "❌ این شماره تلفن قبلاً توسط کاربر دیگری ثبت شده است.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

    verified_phones[user_id] = {
        "phone": phone,
        "verified_at": datetime.datetime.now()
    }
    save_verified_phones()

    # Process referral after phone verification
    if user_id not in referred_users:
        args = context.user_data.get('start_args')
        if args:
            try:
                referrer_id = int(args[0])
                if referrer_id != user_id and referrer_id in all_users:
                    referral_points[referrer_id] = referral_points.get(referrer_id, 0) + 1
                    referred_users.add(user_id)
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"✨ یک کاربر جدید از طریق لینک معرف شما عضو شد و شماره خود را تایید کرد!\n💎 1 امتیاز به شما اضافه شد."
                        )
                    except Exception:
                        pass
            except (ValueError, IndexError):
                pass

    await update.message.reply_text(
        f"✅ شماره تلفن {phone} با موفقیت تأیید شد.\n🏠 به منوی اصلی خوش آمدید.",
        reply_markup=ReplyKeyboardRemove()
    )

    await show_main_menu(update, context)

def main() -> None:
    TOKEN = "7342406071:AAGhXZz8dXdRpIq4tNz0MhvNFISxIqzoHgk"  # Replace with your actual bot token
    load_admin_ids()
    load_balance()
    load_history()
    load_verified_phones()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("cancel", admin_cancel))
    app.add_handler(CommandHandler("account", account_menu))

    app.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(dns_menu, pattern="^dns_menu$"))
    app.add_handler(CallbackQueryHandler(buy_dns_plan_prompt, pattern="^buy_dnsplan_.*"))
    app.add_handler(CallbackQueryHandler(account_menu, pattern="^account_menu$"))
    app.add_handler(CallbackQueryHandler(balance_increase_menu, pattern="^balance_increase$"))
    app.add_handler(CallbackQueryHandler(ask_custom_balance, pattern="^balance_increase_custom$"))
    app.add_handler(CallbackQueryHandler(handle_balance_increase_request, pattern="^balance_increase_.*"))
    app.add_handler(CallbackQueryHandler(balance_request_confirm, pattern="^balance_request_confirm$"))
    app.add_handler(CallbackQueryHandler(confirm_receipt, pattern="^confirm_receipt$"))
    app.add_handler(CallbackQueryHandler(admin_approve_purchase, pattern="^admin_approve_purchase_.*"))
    app.add_handler(CallbackQueryHandler(admin_reject_purchase, pattern="^admin_reject_purchase_.*"))
    app.add_handler(CallbackQueryHandler(approve_balance, pattern="^approve_balance_.*"))
    app.add_handler(CallbackQueryHandler(reject_balance, pattern="^reject_balance_.*"))
    app.add_handler(CallbackQueryHandler(admin_panel_menu, pattern="^admin_panel_menu$"))
    app.add_handler(CallbackQueryHandler(admin_pending_balance, pattern="^admin_pending_balance$"))
    app.add_handler(CallbackQueryHandler(apply_discount_prompt, pattern="^apply_discount$"))
    app.add_handler(CallbackQueryHandler(admin_modify_balance_prompt, pattern="^admin_modify_balance$"))
    app.add_handler(CallbackQueryHandler(convert_referral, pattern="^convert_referral$"))
    app.add_handler(CallbackQueryHandler(admin_block_user, pattern="^admin_block_user$"))
    app.add_handler(CallbackQueryHandler(admin_unblock_user, pattern="^admin_unblock_user$"))
    app.add_handler(CallbackQueryHandler(admin_mass_message, pattern="^admin_mass_message$"))
    app.add_handler(CallbackQueryHandler(admin_toggle_force_join, pattern="^admin_toggle_force_join$"))
    app.add_handler(CallbackQueryHandler(admin_set_force_channel, pattern="^admin_set_force_channel$"))
    app.add_handler(CallbackQueryHandler(referral_menu, pattern="^referral_menu$"))
    app.add_handler(CallbackQueryHandler(wireguard_menu, pattern="^wireguard_menu$"))
    app.add_handler(CallbackQueryHandler(admin_toggle_buttons_menu, pattern="^admin_toggle_buttons_menu$"))
    app.add_handler(CallbackQueryHandler(toggle_dns, pattern="^toggle_dns$"))
    app.add_handler(CallbackQueryHandler(toggle_account, pattern="^toggle_account$"))
    app.add_handler(CallbackQueryHandler(toggle_balance, pattern="^toggle_balance$"))
    app.add_handler(CallbackQueryHandler(toggle_referral, pattern="^toggle_referral$"))
    app.add_handler(CallbackQueryHandler(toggle_wireguard, pattern="^toggle_wireguard$"))
    app.add_handler(CallbackQueryHandler(toggle_site_subscription, pattern="^toggle_site_subscription$"))
    app.add_handler(CallbackQueryHandler(admin_edit_terms, pattern="^admin_edit_terms$"))
    app.add_handler(CallbackQueryHandler(admin_change_button_prices_menu, pattern="^admin_change_button_prices$"))
    app.add_handler(CallbackQueryHandler(admin_change_button_price_handler, pattern="^change_price_.*"))
    app.add_handler(CallbackQueryHandler(admin_user_stats, pattern="^admin_user_stats$"))
    app.add_handler(CallbackQueryHandler(admin_add_temp_discount, pattern="^admin_add_temp_discount$"))
    app.add_handler(CallbackQueryHandler(admin_change_support, pattern="^admin_change_support$"))
    app.add_handler(CallbackQueryHandler(admin_add_admin_prompt, pattern="^admin_add_admin$"))
    app.add_handler(CallbackQueryHandler(admin_remove_admin_prompt, pattern="^admin_remove_admin$"))
    app.add_handler(CallbackQueryHandler(admin_search_user_prompt, pattern="^admin_search_user$"))
    app.add_handler(CallbackQueryHandler(admin_gift_all_balance, pattern="^admin_gift_all$"))
    app.add_handler(CallbackQueryHandler(admin_modify_referral, pattern="^admin_modify_referral$"))
    app.add_handler(CallbackQueryHandler(admin_add_custom_button, pattern="^admin_add_custom_button$"))
    app.add_handler(CallbackQueryHandler(custom_button_handler, pattern="^custombutton_.*"))
    app.add_handler(CallbackQueryHandler(check_force_join, pattern="^check_force_join$"))
    app.add_handler(CallbackQueryHandler(site_subscription_menu, pattern="^site_subscription_menu$"))
    app.add_handler(CallbackQueryHandler(buy_site_subscription, pattern="^buy_site_subscription_.*"))
    app.add_handler(CallbackQueryHandler(confirm_buy_dns, pattern="^confirm_buy_dns_.*"))
    app.add_handler(CallbackQueryHandler(enter_discount_dns, pattern="^enter_discount_dns_.*"))
    app.add_handler(CallbackQueryHandler(toggle_update_mode, pattern="^toggle_update_mode$"))
    app.add_handler(CallbackQueryHandler(process_wireguard_purchase, pattern="^buy_wireguard_.*$"))
    app.add_handler(CallbackQueryHandler(verify_phone_prompt, pattern="^verify_phone$"))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    async def buy_bot_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        text = ("💫 خرید سورس ربات:\n\n"
                "💰 قیمت: 2,000,000 تومان\n"
                "📦 شامل:\n"
                "- سورس کامل\n"
                "- راهنمای نصب\n"
                "- پشتیبانی 1 ماهه\n\n"
                "برای خرید به پشتیبانی پیام دهید:")
        keyboard = [[InlineKeyboardButton("☎️ پشتیبانی", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}")],
                   [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    app.add_handler(CallbackQueryHandler(buy_bot_source, pattern="^buy_bot_source$"))

    async def admin_send_update_notification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        success_count, fail_count = await notify_all_users(context)
        await query.edit_message_text(
            f"✅ نوتیفیکیشن بروزرسانی ارسال شد.\n\n"
            f"موفق: {success_count}\n"
            f"ناموفق: {fail_count}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel_menu")]])
        )

    app.add_handler(CallbackQueryHandler(admin_send_update_notification, pattern="^admin_send_update$"))

    # اضافه کردن handler برای دکمه‌های پشتیبانی و قوانین
    app.add_handler(CallbackQueryHandler(support_menu, pattern="^support_menu$"))
    app.add_handler(CallbackQueryHandler(terms_menu, pattern="^terms$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    app.add_handler(MessageHandler(filters.PHOTO, receipt_photo_handler))

    print("Bot has deployed successfully✅")
    app.run_polling()

if __name__ == "__main__":
    main()