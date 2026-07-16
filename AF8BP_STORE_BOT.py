
import os
import html
import sqlite3
import threading
from datetime import datetime
from typing import Optional

import telebot
from telebot import types

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8685046040:AAHokjTTTDqZ4VS8lQmxyt2zClkqNH4MZU4").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required.")

BOT_NAME = "AF8BP STORE BOT"
OWNER_ADMIN_ID = 8299868901
SUPPORT_USERNAME = "@AF8BPWONER"

BANNER_URL = "https://ibb.co/4RL7CvYV"
QR_URL = "https://ibb.co/S4V1Pqbd"
UPI_ID = "atifmohd54726@okaxis"

DB_PATH = os.getenv("DB_PATH", "af8bp_store.db")

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True,
    num_threads=4,
)

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db_lock = threading.RLock()

# Telegram Premium Custom Emoji IDs supplied by the user.
PE = {
    "main": '<tg-emoji emoji-id="6120674721487918156"></tg-emoji>',
    "buy": '<tg-emoji emoji-id="6120731625509623335"></tg-emoji>',
    "stock": '<tg-emoji emoji-id="6271591501378097650"></tg-emoji>',
    "success": '<tg-emoji emoji-id="6269471054549227567"></tg-emoji>',
    "warning": '<tg-emoji emoji-id="6260291455307225663"></tg-emoji>',
    "gift": '<tg-emoji emoji-id="6260084029861666189"></tg-emoji>',
    "pc": '<tg-emoji emoji-id="6120409511552357384"></tg-emoji>',
    "spark": '<tg-emoji emoji-id="6120461910153368936"></tg-emoji>',
}

PRODUCTS = {
    "kos_virtual": {
        "name": "KOS VIRTUAL",
        "button": "⚡ KOS Virtual",
        "plans": {
            "1d": {"label": "1 Day", "inr": 200, "usd": 2},
            "7d": {"label": "7 Days", "inr": 560, "usd": 6},
            "15d": {"label": "15 Days", "inr": 1050, "usd": 11},
            "30d": {"label": "30 Days", "inr": 1650, "usd": 18},
        },
    },
    "kos_mod": {
        "name": "KOS MOD APK",
        "button": "💎 KOS Mod",
        "plans": {
            "1d": {"label": "1 Day", "inr": 150, "usd": 1},
            "7d": {"label": "7 Days", "inr": 450, "usd": 5},
            "15d": {"label": "15 Days", "inr": 650, "usd": 8},
            "30d": {"label": "30 Days", "inr": 1200, "usd": 14},
        },
    },
    "kos_carrom": {
        "name": "KOS CARROM",
        "button": "🎯 KOS Carrom",
        "plans": {
            "1d": {"label": "24 Hours", "inr": 120, "usd": 1.50, "pkr": 400},
            "7d": {"label": "7 Days", "inr": 350, "usd": 4, "pkr": 1100},
            "15d": {"label": "15 Days", "inr": 550, "usd": 7, "pkr": 1950},
            "30d": {"label": "30 Days", "inr": 1000, "usd": 14, "pkr": 3900},
        },
    },
    "bolt_mod": {
        "name": "BOLT MOD",
        "button": "🤖 BOLT Mod",
        "plans": {
            "1d": {"label": "1 Day", "inr": 140, "usd": 1.50},
            "3d": {"label": "3 Days", "inr": 280, "usd": 3},
            "7d": {"label": "7 Days", "inr": 470, "usd": 5},
            "15d": {"label": "15 Days", "inr": 850, "usd": 9},
            "30d": {"label": "30 Days", "inr": 1400, "usd": 15},
        },
    },
}

# =========================================================
# DATABASE
# =========================================================

def now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def init_db() -> None:
    with db_lock:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                balance INTEGER NOT NULL DEFAULT 0,
                total_orders INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admins(
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS keys_stock(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_key TEXT NOT NULL,
                duration TEXT NOT NULL,
                key_value TEXT UNIQUE NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                used_by INTEGER,
                used_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_key TEXT NOT NULL,
                product_name TEXT NOT NULL,
                duration TEXT NOT NULL,
                duration_label TEXT NOT NULL,
                price_inr INTEGER NOT NULL,
                key_value TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS deposits(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                screenshot_file_id TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL,
                reviewed_by INTEGER,
                reviewed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        db.execute(
            "INSERT OR IGNORE INTO admins(user_id,added_by,created_at) VALUES(?,?,?)",
            (OWNER_ADMIN_ID, OWNER_ADMIN_ID, now()),
        )
        defaults = {
            "bot_name": BOT_NAME,
            "support_username": SUPPORT_USERNAME,
            "banner_url": BANNER_URL,
            "qr_url": QR_URL,
            "upi_id": UPI_ID,
        }
        for key, value in defaults.items():
            db.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                (key, value),
            )
        db.commit()


def get_setting(key: str, default: str = "") -> str:
    with db_lock:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with db_lock:
        db.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        db.commit()


def ensure_user(tg_user) -> sqlite3.Row:
    with db_lock:
        db.execute(
            """
            INSERT INTO users(user_id,username,first_name,last_name,created_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name
            """,
            (
                tg_user.id,
                tg_user.username or "",
                tg_user.first_name or "",
                tg_user.last_name or "",
                now(),
            ),
        )
        db.commit()
        return db.execute("SELECT * FROM users WHERE user_id=?", (tg_user.id,)).fetchone()


def is_admin(user_id: int) -> bool:
    with db_lock:
        return bool(db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone())


def admin_ids():
    with db_lock:
        return [r["user_id"] for r in db.execute("SELECT user_id FROM admins").fetchall()]


# =========================================================
# UI HELPERS
# =========================================================

def safe_name(user) -> str:
    first = html.escape(user.first_name or "User")
    last = html.escape(user.last_name or "")
    return f"{first} {last}".strip()


def send_page(chat_id: int, text: str, keyboard=None, photo_url: Optional[str] = None):
    url = photo_url or get_setting("banner_url", BANNER_URL)
    try:
        return bot.send_photo(
            chat_id,
            url,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as error:
        print(f"Banner fallback: {error}")
        return bot.send_message(
            chat_id,
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


def back_button(callback_data: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 Back", callback_data=callback_data))
    return kb


def main_keyboard(user_id: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("🛒 Buy", callback_data="menu_buy"),
        types.InlineKeyboardButton("📊 Live Stock", callback_data="menu_stock"),
    )
    kb.row(
        types.InlineKeyboardButton("💰 Wallet", callback_data="menu_wallet"),
        types.InlineKeyboardButton("📦 My Orders", callback_data="menu_orders"),
    )
    kb.row(
        types.InlineKeyboardButton("👤 Profile", callback_data="menu_profile"),
        types.InlineKeyboardButton("💬 Support", callback_data="menu_support"),
    )
    if is_admin(user_id):
        kb.row(types.InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel"))
    return kb


def show_main(chat_id: int, user):
    row = ensure_user(user)
    username = f"@{html.escape(user.username)}" if user.username else "Not set"
    text = (
        f'{PE["main"]} <b>WELCOME TO {html.escape(get_setting("bot_name", BOT_NAME))}</b>\n\n'
        f"Hello, <b>{safe_name(user)}</b>!\n\n"
        f"👤 Username: {username}\n"
        f"🆔 User ID: <code>{user.id}</code>\n"
        f"💰 Wallet Balance: ₹{row['balance']}\n"
        f"📦 Total Orders: {row['total_orders']}\n\n"
        "Fast delivery, secure payments and premium products.\n"
        "Choose an option below."
    )
    send_page(chat_id, text, main_keyboard(user.id))


# =========================================================
# USER MENUS
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    show_main(message.chat.id, message.from_user)


@bot.callback_query_handler(func=lambda c: c.data == "main_menu")
def cb_main(call):
    bot.answer_callback_query(call.id)
    show_main(call.message.chat.id, call.from_user)


@bot.callback_query_handler(func=lambda c: c.data == "menu_buy")
def menu_buy(call):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("📦 KOS", callback_data="buy_kos"),
        types.InlineKeyboardButton("🤖 BOLT Mod", callback_data="product_bolt_mod"),
    )
    kb.row(types.InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    send_page(
        call.message.chat.id,
        f'{PE["buy"]} <b>SELECT PRODUCT</b>\n\nChoose a category to continue.',
        kb,
    )


@bot.callback_query_handler(func=lambda c: c.data == "buy_kos")
def buy_kos(call):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("🎱 8BP", callback_data="buy_kos_8bp"),
        types.InlineKeyboardButton("🎯 Carrom Pool", callback_data="product_kos_carrom"),
    )
    kb.row(types.InlineKeyboardButton("🔙 Back", callback_data="menu_buy"))
    send_page(call.message.chat.id, f'{PE["spark"]} <b>KOS PRODUCTS</b>\n\nChoose a game.', kb)


@bot.callback_query_handler(func=lambda c: c.data == "buy_kos_8bp")
def buy_kos_8bp(call):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("⚡ KOS Virtual", callback_data="product_kos_virtual"),
        types.InlineKeyboardButton("💎 KOS Mod", callback_data="product_kos_mod"),
    )
    kb.row(types.InlineKeyboardButton("🔙 Back", callback_data="buy_kos"))
    send_page(call.message.chat.id, f'{PE["pc"]} <b>KOS 8BP</b>\n\nSelect a product.', kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("product_"))
def product_menu(call):
    product_key = call.data.replace("product_", "", 1)
    product = PRODUCTS.get(product_key)
    if not product:
        return

    kb = types.InlineKeyboardMarkup(row_width=2)
    for duration, plan in product["plans"].items():
        kb.add(
            types.InlineKeyboardButton(
                f"⏳ {plan['label']}",
                callback_data=f"plan|{product_key}|{duration}",
            )
        )

    back_cb = "menu_buy" if product_key == "bolt_mod" else (
        "buy_kos" if product_key == "kos_carrom" else "buy_kos_8bp"
    )
    kb.row(types.InlineKeyboardButton("🔙 Back", callback_data=back_cb))

    lines = []
    for plan in product["plans"].values():
        pkr = f" | {plan['pkr']} PKR" if "pkr" in plan else ""
        lines.append(f"• {plan['label']}: ₹{plan['inr']} | ${plan['usd']}{pkr}")

    send_page(
        call.message.chat.id,
        f'{PE["buy"]} <b>{html.escape(product["name"])}</b>\n\n'
        + "\n".join(lines)
        + "\n\nSelect a duration.",
        kb,
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("plan|"))
def plan_selected(call):
    _, product_key, duration = call.data.split("|", 2)
    product = PRODUCTS.get(product_key)
    plan = product["plans"].get(duration) if product else None
    if not product or not plan:
        return

    user = ensure_user(call.from_user)
    with db_lock:
        stock = db.execute(
            "SELECT COUNT(*) AS c FROM keys_stock "
            "WHERE product_key=? AND duration=? AND used=0",
            (product_key, duration),
        ).fetchone()["c"]

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("✅ Confirm Order", callback_data=f"confirm|{product_key}|{duration}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data=f"product_{product_key}"),
    )
    kb.row(types.InlineKeyboardButton("🔙 Back", callback_data=f"product_{product_key}"))

    send_page(
        call.message.chat.id,
        f'{PE["spark"]} <b>ORDER SUMMARY</b>\n\n'
        f"Product: <b>{html.escape(product['name'])}</b>\n"
        f"Duration: <b>{plan['label']}</b>\n"
        f"Price: <b>₹{plan['inr']}</b>\n"
        f"Wallet Balance: <b>₹{user['balance']}</b>\n"
        f"Available Stock: <b>{stock}</b>\n\n"
        "Confirm to receive the key instantly.",
        kb,
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm|"))
def confirm_order(call):
    _, product_key, duration = call.data.split("|", 2)
    product = PRODUCTS.get(product_key)
    plan = product["plans"].get(duration) if product else None
    if not product or not plan:
        return

    ensure_user(call.from_user)

    with db_lock:
        try:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute("SELECT * FROM users WHERE user_id=?", (call.from_user.id,)).fetchone()

            if user["balance"] < plan["inr"]:
                db.rollback()
                bot.answer_callback_query(
                    call.id,
                    f"Insufficient balance. Required ₹{plan['inr']}.",
                    show_alert=True,
                )
                return

            key_row = db.execute(
                "SELECT * FROM keys_stock WHERE product_key=? AND duration=? AND used=0 "
                "ORDER BY id LIMIT 1",
                (product_key, duration),
            ).fetchone()

            if not key_row:
                db.rollback()
                bot.answer_callback_query(call.id, "Out of stock.", show_alert=True)
                return

            reserved = db.execute(
                "UPDATE keys_stock SET used=1,used_by=?,used_at=? WHERE id=? AND used=0",
                (call.from_user.id, now(), key_row["id"]),
            )
            if reserved.rowcount != 1:
                db.rollback()
                bot.answer_callback_query(call.id, "Please try again.", show_alert=True)
                return

            db.execute(
                "UPDATE users SET balance=balance-?,total_orders=total_orders+1 WHERE user_id=?",
                (plan["inr"], call.from_user.id),
            )
            cursor = db.execute(
                """
                INSERT INTO orders(
                    user_id,product_key,product_name,duration,
                    duration_label,price_inr,key_value,status,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    call.from_user.id,
                    product_key,
                    product["name"],
                    duration,
                    plan["label"],
                    plan["inr"],
                    key_row["key_value"],
                    "Completed",
                    now(),
                ),
            )
            order_id = cursor.lastrowid
            db.commit()
        except Exception as error:
            db.rollback()
            print(f"Order error: {error}")
            bot.answer_callback_query(call.id, "Order failed.", show_alert=True)
            return

    send_page(
        call.message.chat.id,
        f'{PE["success"]} <b>ORDER COMPLETED</b>\n\n'
        f"Order ID: <code>#{order_id}</code>\n"
        f"Product: <b>{html.escape(product['name'])}</b>\n"
        f"Duration: <b>{plan['label']}</b>\n"
        f"Paid: <b>₹{plan['inr']}</b>\n\n"
        f"Your Key:\n<code>{html.escape(key_row['key_value'])}</code>",
        back_button("main_menu"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "menu_stock")
def menu_stock(call):
    with db_lock:
        rows = db.execute(
            "SELECT product_key,duration,COUNT(*) AS c FROM keys_stock "
            "WHERE used=0 GROUP BY product_key,duration"
        ).fetchall()
    stock = {(r["product_key"], r["duration"]): r["c"] for r in rows}

    sections = []
    for product_key, product in PRODUCTS.items():
        lines = [f"<b>{html.escape(product['name'])}</b>"]
        for duration, plan in product["plans"].items():
            lines.append(f"• {plan['label']}: {stock.get((product_key, duration), 0)}")
        sections.append("\n".join(lines))

    send_page(
        call.message.chat.id,
        f'{PE["stock"]} <b>LIVE STOCK</b>\n\n'
        + "\n\n".join(sections)
        + "\n\nStock updates automatically.",
        back_button("main_menu"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "menu_wallet")
def menu_wallet(call):
    user = ensure_user(call.from_user)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Add Balance", callback_data="wallet_add"))
    kb.add(types.InlineKeyboardButton("📜 Balance History", callback_data="wallet_history"))
    kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    send_page(
        call.message.chat.id,
        f'{PE["gift"]} <b>YOUR WALLET</b>\n\n'
        f"Current Balance: <b>₹{user['balance']}</b>\n\n"
        "Add funds securely using UPI.",
        kb,
    )


@bot.callback_query_handler(func=lambda c: c.data == "wallet_add")
def wallet_add(call):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("✅ Submit Payment", callback_data="payment_submit"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="menu_wallet"),
    )
    send_page(
        call.message.chat.id,
        f'{PE["spark"]} <b>COMPLETE PAYMENT</b>\n\n'
        f"UPI ID:\n<code>{html.escape(get_setting('upi_id', UPI_ID))}</code>\n\n"
        "Pay using the QR code, then tap Submit Payment.",
        kb,
        photo_url=get_setting("qr_url", QR_URL),
    )


@bot.callback_query_handler(func=lambda c: c.data == "payment_submit")
def payment_submit(call):
    msg = bot.send_message(
        call.message.chat.id,
        "Please enter the amount you paid in INR.",
        reply_markup=types.ForceReply(selective=True),
    )
    bot.register_next_step_handler(msg, payment_amount_step)


def payment_amount_step(message):
    try:
        amount = int((message.text or "").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "Send a valid amount, for example: 500")
        return

    msg = bot.send_message(
        message.chat.id,
        "Now send your payment screenshot as a photo.",
        reply_markup=types.ForceReply(selective=True),
    )
    bot.register_next_step_handler(msg, payment_screenshot_step, amount)


def payment_screenshot_step(message, amount: int):
    if not message.photo:
        bot.send_message(message.chat.id, "Please send the screenshot as a photo.")
        return

    file_id = message.photo[-1].file_id
    with db_lock:
        cursor = db.execute(
            "INSERT INTO deposits(user_id,amount,screenshot_file_id,status,created_at) "
            "VALUES(?,?,?,?,?)",
            (message.from_user.id, amount, file_id, "Pending", now()),
        )
        deposit_id = cursor.lastrowid
        db.commit()

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"deposit_approve|{deposit_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"deposit_reject|{deposit_id}"),
    )

    caption = (
        f'{PE["warning"]} <b>NEW PAYMENT REQUEST</b>\n\n'
        f"Name: {safe_name(message.from_user)}\n"
        f"Username: @{html.escape(message.from_user.username or 'not_set')}\n"
        f"User ID: <code>{message.from_user.id}</code>\n"
        f"Amount: <b>₹{amount}</b>"
    )

    for admin_id in admin_ids():
        try:
            bot.send_photo(admin_id, file_id, caption=caption, reply_markup=kb)
        except Exception as error:
            print(f"Admin notify error: {error}")

    send_page(
        message.chat.id,
        f'{PE["success"]} <b>PAYMENT SUBMITTED</b>\n\n'
        "Your payment request has been sent to the admin.",
        back_button("menu_wallet"),
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("deposit_"))
def review_deposit(call):
    if not is_admin(call.from_user.id):
        return

    action, deposit_id_text = call.data.split("|", 1)
    deposit_id = int(deposit_id_text)

    with db_lock:
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM deposits WHERE id=?", (deposit_id,)).fetchone()
            if not row or row["status"] != "Pending":
                db.rollback()
                bot.answer_callback_query(call.id, "Already reviewed.", show_alert=True)
                return

            approved = action == "deposit_approve"
            status = "Approved" if approved else "Rejected"
            db.execute(
                "UPDATE deposits SET status=?,reviewed_by=?,reviewed_at=? WHERE id=?",
                (status, call.from_user.id, now(), deposit_id),
            )
            if approved:
                db.execute(
                    "UPDATE users SET balance=balance+? WHERE user_id=?",
                    (row["amount"], row["user_id"]),
                )
            db.commit()
        except Exception as error:
            db.rollback()
            print(f"Deposit review error: {error}")
            return

    try:
        bot.send_message(
            row["user_id"],
            f"<b>PAYMENT {status.upper()}</b>\n\nAmount: ₹{row['amount']}",
        )
    except Exception:
        pass

    bot.answer_callback_query(call.id, f"Payment {status}.", show_alert=True)


@bot.callback_query_handler(func=lambda c: c.data == "wallet_history")
def wallet_history(call):
    with db_lock:
        rows = db.execute(
            "SELECT * FROM deposits WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (call.from_user.id,),
        ).fetchall()

    body = "No payment history found."
    if rows:
        body = "\n\n".join(
            f"#{r['id']} • ₹{r['amount']} • {r['status']}\n{r['created_at']}"
            for r in rows
        )

    send_page(
        call.message.chat.id,
        f'{PE["stock"]} <b>BALANCE HISTORY</b>\n\n{body}',
        back_button("menu_wallet"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "menu_orders")
def menu_orders(call):
    with db_lock:
        rows = db.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (call.from_user.id,),
        ).fetchall()

    body = "You have not placed any orders yet."
    if rows:
        body = "\n\n".join(
            f"<b>Order #{r['id']}</b>\n"
            f"{html.escape(r['product_name'])} • {r['duration_label']}\n"
            f"₹{r['price_inr']} • {r['status']}"
            for r in rows
        )

    send_page(
        call.message.chat.id,
        f'{PE["stock"]} <b>MY ORDERS</b>\n\n{body}',
        back_button("main_menu"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "menu_profile")
def menu_profile(call):
    user = ensure_user(call.from_user)
    username = f"@{html.escape(call.from_user.username)}" if call.from_user.username else "Not set"
    send_page(
        call.message.chat.id,
        f'{PE["main"]} <b>YOUR PROFILE</b>\n\n'
        f"Name: <b>{safe_name(call.from_user)}</b>\n"
        f"Username: {username}\n"
        f"User ID: <code>{call.from_user.id}</code>\n"
        f"Wallet: <b>₹{user['balance']}</b>\n"
        f"Orders: <b>{user['total_orders']}</b>",
        back_button("main_menu"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "menu_support")
def menu_support(call):
    support = get_setting("support_username", SUPPORT_USERNAME)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💬 Contact Support", url=f"https://t.me/{support.lstrip('@')}"))
    kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="main_menu"))

    send_page(
        call.message.chat.id,
        f'{PE["spark"]} <b>SUPPORT CENTER</b>\n\n'
        f"Need help with an order or payment?\nContact: <b>{html.escape(support)}</b>",
        kb,
    )


# =========================================================
# ADMIN
# =========================================================

def admin_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard"),
        types.InlineKeyboardButton("👥 Users", callback_data="admin_users"),
    )
    kb.row(
        types.InlineKeyboardButton("📊 Live Stock", callback_data="admin_stock"),
        types.InlineKeyboardButton("💰 Wallet Manager", callback_data="admin_wallet"),
    )
    kb.row(
        types.InlineKeyboardButton("🔑 Add Keys", callback_data="admin_add_keys"),
        types.InlineKeyboardButton("🗑️ Remove Keys", callback_data="admin_remove_keys"),
    )
    kb.row(
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("➕ Add Admin", callback_data="admin_add_admin"),
    )
    kb.row(
        types.InlineKeyboardButton("➖ Remove Admin", callback_data="admin_remove_admin"),
        types.InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_settings"),
    )
    kb.row(types.InlineKeyboardButton("🔙 User Menu", callback_data="main_menu"))
    return kb


@bot.callback_query_handler(func=lambda c: c.data == "admin_panel")
def admin_panel(call):
    if not is_admin(call.from_user.id):
        return
    send_page(
        call.message.chat.id,
        f'{PE["main"]} <b>ADMIN CONTROL PANEL</b>\n\n'
        "Manage keys, stock, wallets, users and bot settings.",
        admin_keyboard(),
    )


@bot.callback_query_handler(func=lambda c: c.data == "admin_dashboard")
def admin_dashboard(call):
    if not is_admin(call.from_user.id):
        return
    with db_lock:
        users = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        orders = db.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
        revenue = db.execute(
            "SELECT COALESCE(SUM(price_inr),0) AS s FROM orders WHERE status='Completed'"
        ).fetchone()["s"]
        stock = db.execute("SELECT COUNT(*) AS c FROM keys_stock WHERE used=0").fetchone()["c"]
        pending = db.execute("SELECT COUNT(*) AS c FROM deposits WHERE status='Pending'").fetchone()["c"]

    send_page(
        call.message.chat.id,
        f'{PE["stock"]} <b>ADMIN DASHBOARD</b>\n\n'
        f"Users: <b>{users}</b>\n"
        f"Orders: <b>{orders}</b>\n"
        f"Revenue: <b>₹{revenue}</b>\n"
        f"Available Keys: <b>{stock}</b>\n"
        f"Pending Payments: <b>{pending}</b>",
        back_button("admin_panel"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "admin_users")
def admin_users(call):
    if not is_admin(call.from_user.id):
        return
    with db_lock:
        rows = db.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 20").fetchall()
    body = "\n".join(
        f"• {html.escape(r['first_name'] or 'User')} — <code>{r['user_id']}</code> — ₹{r['balance']}"
        for r in rows
    ) or "No users found."

    send_page(
        call.message.chat.id,
        f'{PE["main"]} <b>LATEST USERS</b>\n\n{body}',
        back_button("admin_panel"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "admin_stock")
def admin_stock(call):
    if not is_admin(call.from_user.id):
        return
    menu_stock(call)


def product_selector(prefix: str, back: str = "admin_panel"):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for product_key, product in PRODUCTS.items():
        kb.add(
            types.InlineKeyboardButton(
                product["button"],
                callback_data=f"{prefix}|{product_key}",
            )
        )
    kb.row(types.InlineKeyboardButton("🔙 Back", callback_data=back))
    return kb


@bot.callback_query_handler(func=lambda c: c.data == "admin_add_keys")
def admin_add_keys(call):
    if not is_admin(call.from_user.id):
        return
    send_page(call.message.chat.id, f'{PE["success"]} <b>ADD KEYS</b>\n\nSelect a product.', product_selector("addkey_product"))


@bot.callback_query_handler(func=lambda c: c.data == "admin_remove_keys")
def admin_remove_keys(call):
    if not is_admin(call.from_user.id):
        return
    send_page(call.message.chat.id, f'{PE["warning"]} <b>REMOVE KEYS</b>\n\nSelect a product.', product_selector("removekey_product"))


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("addkey_product|")
    or c.data.startswith("removekey_product|")
)
def key_product(call):
    if not is_admin(call.from_user.id):
        return
    action, product_key = call.data.split("|", 1)
    product = PRODUCTS.get(product_key)
    if not product:
        return

    prefix = "addkey_duration" if action.startswith("addkey") else "removekey_duration"
    back = "admin_add_keys" if action.startswith("addkey") else "admin_remove_keys"

    kb = types.InlineKeyboardMarkup(row_width=2)
    for duration, plan in product["plans"].items():
        kb.add(
            types.InlineKeyboardButton(
                f"⏳ {plan['label']}",
                callback_data=f"{prefix}|{product_key}|{duration}",
            )
        )
    kb.row(types.InlineKeyboardButton("🔙 Back", callback_data=back))

    send_page(
        call.message.chat.id,
        f"<b>{html.escape(product['name'])}</b>\n\nSelect duration.",
        kb,
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("addkey_duration|")
    or c.data.startswith("removekey_duration|")
)
def key_duration(call):
    if not is_admin(call.from_user.id):
        return
    action, product_key, duration = call.data.split("|", 2)
    verb = "add" if action.startswith("addkey") else "remove"
    product = PRODUCTS[product_key]
    plan = product["plans"][duration]

    msg = bot.send_message(
        call.message.chat.id,
        f"Send keys to {verb} for:\n"
        f"<b>{html.escape(product['name'])} — {plan['label']}</b>\n\n"
        "One key per line.",
        reply_markup=types.ForceReply(selective=True),
    )
    bot.register_next_step_handler(msg, process_keys, verb, product_key, duration)


def process_keys(message, verb: str, product_key: str, duration: str):
    if not is_admin(message.from_user.id):
        return

    keys = [line.strip() for line in (message.text or "").splitlines() if line.strip()]
    product = PRODUCTS[product_key]
    plan = product["plans"][duration]
    success = 0
    failed = 0

    with db_lock:
        for key in keys:
            if verb == "add":
                try:
                    db.execute(
                        "INSERT INTO keys_stock(product_key,duration,key_value,created_at) VALUES(?,?,?,?)",
                        (product_key, duration, key, now()),
                    )
                    success += 1
                except sqlite3.IntegrityError:
                    failed += 1
            else:
                cursor = db.execute(
                    "DELETE FROM keys_stock WHERE product_key=? AND duration=? "
                    "AND key_value=? AND used=0",
                    (product_key, duration, key),
                )
                if cursor.rowcount:
                    success += 1
                else:
                    failed += 1
        db.commit()

    word = "Added" if verb == "add" else "Removed"
    send_page(
        message.chat.id,
        f'{PE["success"]} <b>KEYS {word.upper()}</b>\n\n'
        f"Product: {html.escape(product['name'])}\n"
        f"Duration: {plan['label']}\n"
        f"{word}: {success}\n"
        f"Skipped / Not Found: {failed}\n\n"
        "Live Stock updated automatically.",
        back_button("admin_panel"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "admin_wallet")
def admin_wallet(call):
    if not is_admin(call.from_user.id):
        return
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("➕ Add Balance", callback_data="wallet_admin_add"),
        types.InlineKeyboardButton("➖ Remove Balance", callback_data="wallet_admin_remove"),
    )
    kb.row(types.InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
    send_page(call.message.chat.id, f'{PE["gift"]} <b>WALLET MANAGER</b>\n\nUse User ID and amount.', kb)


@bot.callback_query_handler(func=lambda c: c.data in ("wallet_admin_add", "wallet_admin_remove"))
def admin_wallet_action(call):
    if not is_admin(call.from_user.id):
        return
    mode = "add" if call.data.endswith("_add") else "remove"
    msg = bot.send_message(
        call.message.chat.id,
        "Send: <code>USER_ID AMOUNT</code>\nExample: <code>123456789 500</code>",
        reply_markup=types.ForceReply(selective=True),
    )
    bot.register_next_step_handler(msg, process_wallet, mode)


def process_wallet(message, mode: str):
    if not is_admin(message.from_user.id):
        return
    try:
        user_id_text, amount_text = (message.text or "").split(maxsplit=1)
        user_id = int(user_id_text)
        amount = int(amount_text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "Invalid format.")
        return

    with db_lock:
        row = db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            bot.send_message(message.chat.id, "User not found.")
            return
        if mode == "remove" and row["balance"] < amount:
            bot.send_message(message.chat.id, "Insufficient user balance.")
            return

        operator = "+" if mode == "add" else "-"
        db.execute(
            f"UPDATE users SET balance=balance{operator}? WHERE user_id=?",
            (amount, user_id),
        )
        db.commit()
        new_balance = db.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()["balance"]

    bot.send_message(
        message.chat.id,
        f"Wallet updated.\nUser ID: <code>{user_id}</code>\nNew Balance: ₹{new_balance}",
    )


@bot.callback_query_handler(func=lambda c: c.data == "admin_broadcast")
def admin_broadcast(call):
    if not is_admin(call.from_user.id):
        return
    msg = bot.send_message(
        call.message.chat.id,
        "Send the broadcast message.",
        reply_markup=types.ForceReply(selective=True),
    )
    bot.register_next_step_handler(msg, process_broadcast)


def process_broadcast(message):
    if not is_admin(message.from_user.id):
        return
    with db_lock:
        users = [r["user_id"] for r in db.execute("SELECT user_id FROM users").fetchall()]

    sent = 0
    failed = 0
    for user_id in users:
        try:
            bot.copy_message(user_id, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1

    bot.send_message(message.chat.id, f"Broadcast completed.\nSent: {sent}\nFailed: {failed}")


@bot.callback_query_handler(func=lambda c: c.data == "admin_add_admin")
def admin_add_admin(call):
    if not is_admin(call.from_user.id):
        return
    msg = bot.send_message(
        call.message.chat.id,
        "Send User ID to add as admin.",
        reply_markup=types.ForceReply(selective=True),
    )
    bot.register_next_step_handler(msg, process_add_admin)


def process_add_admin(message):
    if not is_admin(message.from_user.id):
        return
    try:
        user_id = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "Invalid User ID.")
        return

    with db_lock:
        db.execute(
            "INSERT OR IGNORE INTO admins(user_id,added_by,created_at) VALUES(?,?,?)",
            (user_id, message.from_user.id, now()),
        )
        db.commit()

    bot.send_message(message.chat.id, f"Admin added: <code>{user_id}</code>")


@bot.callback_query_handler(func=lambda c: c.data == "admin_remove_admin")
def admin_remove_admin(call):
    if not is_admin(call.from_user.id):
        return
    msg = bot.send_message(
        call.message.chat.id,
        "Send User ID to remove from admins.",
        reply_markup=types.ForceReply(selective=True),
    )
    bot.register_next_step_handler(msg, process_remove_admin)


def process_remove_admin(message):
    if not is_admin(message.from_user.id):
        return
    try:
        user_id = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "Invalid User ID.")
        return

    if user_id == OWNER_ADMIN_ID:
        bot.send_message(message.chat.id, "Owner admin cannot be removed.")
        return

    with db_lock:
        db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        db.commit()

    bot.send_message(message.chat.id, f"Admin removed: <code>{user_id}</code>")


@bot.callback_query_handler(func=lambda c: c.data == "admin_settings")
def admin_settings(call):
    if not is_admin(call.from_user.id):
        return

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("🤖 Bot Name", callback_data="setting_bot_name"),
        types.InlineKeyboardButton("💬 Support", callback_data="setting_support"),
    )
    kb.row(
        types.InlineKeyboardButton("🖼️ Banner URL", callback_data="setting_banner"),
        types.InlineKeyboardButton("📱 QR URL", callback_data="setting_qr"),
    )
    kb.row(types.InlineKeyboardButton("🏦 UPI ID", callback_data="setting_upi"))
    kb.row(types.InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))

    send_page(
        call.message.chat.id,
        f'{PE["pc"]} <b>BOT SETTINGS</b>\n\nChange branding and payment details.',
        kb,
    )


SETTING_MAP = {
    "setting_bot_name": ("bot_name", "Send new bot name."),
    "setting_support": ("support_username", "Send support username."),
    "setting_banner": ("banner_url", "Send banner image URL."),
    "setting_qr": ("qr_url", "Send QR image URL."),
    "setting_upi": ("upi_id", "Send UPI ID."),
}


@bot.callback_query_handler(func=lambda c: c.data in SETTING_MAP)
def edit_setting(call):
    if not is_admin(call.from_user.id):
        return
    key, prompt = SETTING_MAP[call.data]
    msg = bot.send_message(
        call.message.chat.id,
        prompt,
        reply_markup=types.ForceReply(selective=True),
    )
    bot.register_next_step_handler(msg, save_setting, key)


def save_setting(message, key: str):
    if not is_admin(message.from_user.id):
        return
    value = (message.text or "").strip()
    if not value:
        bot.send_message(message.chat.id, "Value cannot be empty.")
        return
    set_setting(key, value)
    bot.send_message(message.chat.id, "Setting updated.")


# =========================================================
# RUN
# =========================================================

def setup_telegram_menu() -> None:
    """
    Shows Telegram's bottom-left Menu button and keeps only /start inside it.
    """
    try:
        bot.set_my_commands(
            [types.BotCommand("start", "Open AF8BP STORE BOT")]
        )
        bot.set_chat_menu_button(
            menu_button=types.MenuButtonCommands()
        )
    except Exception as error:
        print(f"Telegram menu setup error: {error}")


@bot.message_handler(func=lambda m: True, content_types=["text"])
def fallback(message):
    ensure_user(message.from_user)
    bot.send_message(message.chat.id, "Use /start to open AF8BP STORE BOT.")


if __name__ == "__main__":
    init_db()
    setup_telegram_menu()
    print("AF8BP STORE BOT is running...")
    bot.infinity_polling(
        skip_pending=True,
        timeout=35,
        long_polling_timeout=35,
        allowed_updates=["message", "callback_query"],
    )
