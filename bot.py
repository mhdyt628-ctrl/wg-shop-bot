import logging
import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8838210157:AAGyT2CI1Un4z9ok_hicEWcxGANOvmkkZN0"
ADMIN_ID = 6825957050
ADMIN_USERNAME = "Khanmahdix"
BOT_USERNAME = "WG_SHEKAN_bot"
CHANNEL_LINK = "https://t.me/WGSHEKAN"
DB_FILE = "shop_data.json"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

def load_db():
    if not os.path.exists(DB_FILE):
        return {"services": [
            {"id": 1, "name": "خدمت نمونه ۱", "desc": "توضیحات اول", "price": 50000},
            {"id": 2, "name": "خدمت نمونه ۲", "desc": "توضیحات دوم", "price": 100000},
        ], "orders": [], "user_subscriptions": {}}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
carts = {}

def main_menu(uid):
    b = [
        [InlineKeyboardButton("🛒 خرید اشتراک", callback_data="services")],
        [InlineKeyboardButton("📋 اشتراک های من", callback_data="my_subs")],
        [InlineKeyboardButton("👥 معرفی به دوستان", callback_data="refer")],
        [InlineKeyboardButton("📢 کانال اطلاع رسانی", url=CHANNEL_LINK)],
    ]
    if uid == ADMIN_ID:
        b.append([InlineKeyboardButton("⚙️ مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(b)

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن خدمت", callback_data="admin_add")],
        [InlineKeyboardButton("📋 لیست خدمات", callback_data="admin_list")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back")],
    ])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    welcome = (
        f"سلام {name} عزیز! 👋\n"
        f"به فروشگاه رسمی WG SHEKAN خوش اومدی 🎮\n"
        f"اینجا می‌تونی اشتراک‌های خودت رو به راحتی خریداری کنی.\n"
        f"برای شروع از منوی پایین استفاده کن 👇"
    )
    await update.message.reply_text(welcome, reply_markup=main_menu(update.effective_user.id))

async def btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    d = q.data
    db = load_db()

    if d == "back":
        await q.edit_message_text("منوی اصلی:", reply_markup=main_menu(uid))

    elif d == "services":
        svcs = db["services"]
        if not svcs:
            await q.edit_message_text("خدمتی موجود نیست.", reply_markup=main_menu(uid))
            return
        text = "🛒 *خرید اشتراک:*\n\nیکی از سرویس‌های زیر رو انتخاب کن:"
        btns = [[InlineKeyboardButton(f"{s['name']} — {s['price']:,} تومان", callback_data=f"buy_{s['id']}")] for s in svcs]
        btns.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif d.startswith("buy_"):
        sid = int(d.split("_")[1])
        svc = next((s for s in db["services"] if s["id"] == sid), None)
        if svc:
            username = q.from_user.username or "بدون یوزرنیم"
            full_name = q.from_user.full_name
            text = (
                f"🔔 *درخواست خرید جدید!*\n\n"
                f"👤 نام: {full_name}\n"
                f"🆔 یوزرنیم: @{username}\n"
                f"📦 سرویس: {svc['name']}\n"
                f"💰 قیمت: {svc['price']:,} تومان\n"
                f"📝 توضیحات: {svc['desc']}"
            )
            try:
                await ctx.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="Markdown")
            except:
                pass
            await q.edit_message_text(
                f"✅ درخواست *{svc['name']}* ثبت شد!\n\n"
                f"ادمین به زودی باهات تماس می‌گیره و بعد از پرداخت سرویست فعال میشه.\n"
                f"📞 ارتباط با ادمین: @{ADMIN_USERNAME}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))

    elif d == "my_subs":
        db = load_db()
        subs = db.get("user_subscriptions", {}).get(str(uid), [])
        if not subs:
            await q.edit_message_text(
                "📋 *اشتراک های من*\n\nهنوز اشتراکی خریداری نکردی.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))
        else:
            text = "📋 *اشتراک های من:*\n\n" + "".join(f"✅ {s}\n" for s in subs)
            await q.edit_message_text(text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))

    elif d == "refer":
        link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
        await q.edit_message_text(
            f"👥 *معرفی به دوستان*\n\nلینک اختصاصی تو:\n`{link}`\n\nاین لینک رو برای دوستات بفرست!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))

    elif d == "admin" and uid == ADMIN_ID:
        await q.edit_message_text("⚙️ پنل مدیریت:", reply_markup=admin_menu())

    elif d == "admin_list" and uid == ADMIN_ID:
        text = "📋 *خدمات:*\n\n" + "".join(f"ID:{s['id']} | {s['name']} | {s['price']:,}\n" for s in db["services"])
        await q.edit_message_text(text or "خدمتی نیست.", parse_mode="Markdown", reply_markup=admin_menu())

    elif d == "admin_add" and uid == ADMIN_ID:
        ctx.user_data.update({"step": "name", "svc": {}})
        await q.edit_message_text("نام خدمت را بفرست:")

async def msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID or "step" not in ctx.user_data:
        return
    step = ctx.user_data["step"]
    svc = ctx.user_data["svc"]
    text = update.message.text
    if step == "name":
        svc["name"] = text
        ctx.user_data["step"] = "desc"
        await update.message.reply_text("توضیحات را بفرست:")
    elif step == "desc":
        svc["desc"] = text
        ctx.user_data["step"] = "price"
        await update.message.reply_text("قیمت (تومان) را بفرست:")
    elif step == "price":
        try:
            db = load_db()
            svc["id"] = max((s["id"] for s in db["services"]), default=0) + 1
            svc["price"] = int(text.replace(",","").replace("،",""))
            db["services"].append(svc)
            save_db(db)
            ctx.user_data.clear()
            await update.message.reply_text(f"✅ خدمت '{svc['name']}' اضافه شد!", reply_markup=admin_menu())
        except:
            await update.message.reply_text("قیمت باید عدد باشه.")

def main():
    threading.Thread(target=run_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(btn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))
    logger.info("ربات شروع شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
