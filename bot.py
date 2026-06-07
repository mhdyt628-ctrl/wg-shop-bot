import logging
import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8838210157:AAGyT2CI1Un4z9ok_hicEWcxGANOvmkkZN0"
ADMIN_ID = 6825957050
ADMIN_USERNAME = "Khanmahdix"
BOT_USERNAME = "WG_SHEKAN_bot"
CHANNEL_LINK = "https://t.me/WGSHEKAN"
CARD_NUMBER = "6219 8619 2331 7340"
REFERRAL_BONUS = 10000
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
        return {
            "services": [
                {"id": 1, "name": "خدمت نمونه ۱", "price": 50000},
                {"id": 2, "name": "خدمت نمونه ۲", "price": 100000},
            ],
            "orders": [],
            "user_subscriptions": {},
            "wallets": {},
            "referred_users": [],
            "pending_receipts": {}
        }
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_wallet(db, uid):
    uid = str(uid)
    if uid not in db.get("wallets", {}):
        db.setdefault("wallets", {})[uid] = {"charged": 0, "spent": 0, "gift": 0}
    return db["wallets"][uid]

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def main_menu(uid):
    b = [
        [InlineKeyboardButton("🛒 خرید اشتراک", callback_data="services"),
         InlineKeyboardButton("📋 اشتراک های من", callback_data="my_subs")],
        [InlineKeyboardButton("👥 معرفی به دوستان", callback_data="refer"),
         InlineKeyboardButton("👛 کیف پول", callback_data="wallet")],
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
    await update.get_bot().set_my_commands([
        BotCommand("start", "شروع / منوی اصلی"),
    ])
    uid = update.effective_user.id
    name = update.effective_user.first_name
    db = load_db()

    args = ctx.args
    if args and args[0].startswith("ref_"):
        referrer_id = str(args[0].split("_")[1])
        referred = db.setdefault("referred_users", [])
        if str(uid) not in referred and referrer_id != str(uid):
            referred.append(str(uid))
            wallet = get_wallet(db, referrer_id)
            wallet["gift"] += REFERRAL_BONUS
            save_db(db)
            try:
                await ctx.bot.send_message(
                    chat_id=int(referrer_id),
                    text=f"🎉 یک نفر با لینک دعوت شما وارد ربات شد!\n💰 {REFERRAL_BONUS:,} تومان اعتبار هدیه به کیف پول شما اضافه شد."
                )
            except:
                pass

    welcome = (
        f"┌─────────────────────┐\n"
        f"⚡️ *فقط با ایرانسل و اپ اختصاصی ما*\n"
        f"└─────────────────────┘\n\n"
        f"سلام {name} عزیز! 👋\n"
        f"به فروشگاه رسمی WG SHEKAN خوش اومدی 🎮\n"
        f"اینجا می‌تونی اشتراک‌های خودت رو به راحتی خریداری کنی.\n"
        f"برای شروع از منوی پایین استفاده کن 👇"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=main_menu(uid))

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
        if not svc:
            return
        wallet = get_wallet(db, uid)
        total_balance = wallet["charged"] + wallet["gift"] - wallet["spent"]
        price = svc["price"]

        if total_balance >= price:
            btns = [
                [InlineKeyboardButton("✅ پرداخت با کیف پول", callback_data=f"paywallet_{sid}")],
                [InlineKeyboardButton("💳 پرداخت کارت به کارت", callback_data=f"paycard_{sid}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="services")],
            ]
            await q.edit_message_text(
                f"📦 *{svc['name']}*\n💰 قیمت: {price:,} تومان\n👛 موجودی کیف پول: {total_balance:,} تومان\n\nروش پرداخت رو انتخاب کن:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(btns))
        else:
            order_id = len(db.get("orders", [])) + 1
            db.setdefault("orders", []).append({"id": order_id, "uid": uid, "sid": sid, "status": "pending"})
            db.setdefault("pending_receipts", {})[str(order_id)] = {
                "uid": uid, "sid": sid, "svc_name": svc["name"], "price": price,
                "name": q.from_user.full_name,
                "username": q.from_user.username or "بدون یوزرنیم"
            }
            save_db(db)
            await q.edit_message_text(
                f"📦 *{svc['name']}*\n💰 قیمت: {price:,} تومان\n\n"
                f"💳 لطفاً مبلغ رو به شماره کارت زیر واریز کن:\n"
                f"`{CARD_NUMBER}`\n\n"
                f"📌 بعد از واریز دکمه زیر رو بزن 👇",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ واریز کردم، رسید می‌فرستم", callback_data=f"paid_{order_id}")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
                ])
            )
            try:
                await ctx.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=(
                        f"🔔 *سفارش جدید — منتظر رسید*\n\n"
                        f"👤 نام: {q.from_user.full_name}\n"
                        f"🆔 یوزرنیم: @{q.from_user.username or 'بدون یوزرنیم'}\n"
                        f"🆔 آیدی: {uid}\n"
                        f"📦 سرویس: {svc['name']}\n"
                        f"💰 قیمت: {price:,} تومان\n"
                        f"🔢 شماره سفارش: {order_id}"
                    ),
                    parse_mode="Markdown"
                )
            except:
                pass

    elif d.startswith("paid_"):
        order_id = d.split("_")[1]
        ctx.user_data["waiting_receipt_order"] = order_id
        await q.edit_message_text(
            "📎 خیلی خوب! حالا تصویر رسید واریز رو برام بفرست 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
            ])
        )

    elif d.startswith("paycard_"):
        sid = int(d.split("_")[1])
        svc = next((s for s in db["services"] if s["id"] == sid), None)
        if not svc:
            return
        order_id = len(db.get("orders", [])) + 1
        db.setdefault("orders", []).append({"id": order_id, "uid": uid, "sid": sid, "status": "pending"})
        db.setdefault("pending_receipts", {})[str(order_id)] = {
            "uid": uid, "sid": sid, "svc_name": svc["name"], "price": svc["price"],
            "name": q.from_user.full_name,
            "username": q.from_user.username or "بدون یوزرنیم"
        }
        save_db(db)
        await q.edit_message_text(
            f"💳 لطفاً مبلغ *{svc['price']:,} تومان* رو به شماره کارت زیر واریز کن:\n"
            f"`{CARD_NUMBER}`\n\n"
            f"📌 بعد از واریز دکمه زیر رو بزن 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ واریز کردم، رسید می‌فرستم", callback_data=f"paid_{order_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
            ])
        )

    elif d.startswith("paywallet_"):
        sid = int(d.split("_")[1])
        svc = next((s for s in db["services"] if s["id"] == sid), None)
        if not svc:
            return
        wallet = get_wallet(db, uid)
        gift = wallet["gift"]
        price = svc["price"]
        if gift >= price:
            wallet["gift"] -= price
        else:
            wallet["spent"] += price - gift
            wallet["gift"] = 0
        db.setdefault("user_subscriptions", {}).setdefault(str(uid), []).append(svc["name"])
        save_db(db)
        await q.edit_message_text(
            f"✅ پرداخت با کیف پول انجام شد!\n📦 سرویس *{svc['name']}* فعال شد.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))
        try:
            await ctx.bot.send_message(chat_id=ADMIN_ID,
                text=f"💳 پرداخت کیف پول:\n👤 {q.from_user.full_name}\n📦 {svc['name']}", parse_mode="Markdown")
        except:
            pass

    elif d.startswith("confirmorder_"):
        if uid != ADMIN_ID:
            return
        parts = d.split("_")
        order_id = parts[1]
        customer_uid = int(parts[2])
        amount = int(parts[3])
        db = load_db()
        wallet = get_wallet(db, customer_uid)
        wallet["charged"] += amount
        save_db(db)
        await q.edit_message_text(f"✅ پرداخت سفارش {order_id} تأیید شد.")
        ctx.user_data["pending_file_uid"] = customer_uid
        try:
            await ctx.bot.send_message(
                chat_id=customer_uid,
                text="✅ پرداخت شما تأیید شد!\n📦 سرویست در کمتر از ۳۰ دقیقه تا ۱ ساعت فعال میشه 🚀\nادمین به زودی فایل سرویس رو برات می‌فرسته.")
        except:
            pass
        await ctx.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📤 حالا فایل سرویس رو بفرست تا برای مشتری (آیدی: {customer_uid}) ارسال بشه.")

    elif d == "wallet":
        wallet = get_wallet(db, uid)
        total_balance = wallet["charged"] + wallet["gift"] - wallet["spent"]
        text = (
            f"👛 *کیف پول من*\n\n"
            f"💰 موجودی قابل استفاده: *{total_balance:,} تومان*\n\n"
            f"📥 کل شارژ: {wallet['charged']:,} تومان\n"
            f"📤 کل خرج: {wallet['spent']:,} تومان\n"
            f"🎁 اعتبار هدیه: {wallet['gift']:,} تومان"
        )
        await q.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))

    elif d == "my_subs":
        subs = db.get("user_subscriptions", {}).get(str(uid), [])
        if not subs:
            await q.edit_message_text("📋 *اشتراک های من*\n\nهنوز اشتراکی خریداری نکردی.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))
        else:
            text = "📋 *اشتراک های من:*\n\n" + "".join(f"✅ {s}\n" for s in subs)
            await q.edit_message_text(text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))

    elif d == "refer":
        link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
        await q.edit_message_text(
            f"👥 *معرفی به دوستان*\n\nبه ازای هر نفری که با لینک تو وارد بشه *{REFERRAL_BONUS:,} تومان* اعتبار هدیه می‌گیری! 🎁\n\nلینک اختصاصی تو:\n`{link}`",
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
    db = load_db()

    if uid == ADMIN_ID and "pending_file_uid" in ctx.user_data:
        customer_uid = ctx.user_data.pop("pending_file_uid")
        try:
            if update.message.document:
                await ctx.bot.send_document(chat_id=customer_uid,
                    document=update.message.document.file_id,
                    caption="📦 فایل سرویس شما آماده‌ست! 🚀")
            elif update.message.photo:
                await ctx.bot.send_photo(chat_id=customer_uid,
                    photo=update.message.photo[-1].file_id,
                    caption="📦 فایل سرویس شما آماده‌ست! 🚀")
            else:
                await ctx.bot.send_message(chat_id=customer_uid, text=update.message.text)
            await update.message.reply_text("✅ فایل با موفقیت برای مشتری ارسال شد.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در ارسال: {e}")
        return

    if "waiting_receipt_order" in ctx.user_data and update.message.photo:
        order_id = ctx.user_data.pop("waiting_receipt_order")
        pending = db.get("pending_receipts", {}).get(str(order_id), {})
        caption = (
            f"🧾 *رسید پرداخت جدید!*\n\n"
            f"👤 نام: {pending.get('name', '-')}\n"
            f"🆔 یوزرنیم: @{pending.get('username', '-')}\n"
            f"🆔 آیدی: {uid}\n"
            f"📦 سرویس: {pending.get('svc_name', '-')}\n"
            f"💰 قیمت: {pending.get('price', 0):,} تومان\n"
            f"🔢 شماره سفارش: {order_id}"
        )
        try:
            await ctx.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=update.message.photo[-1].file_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ تأیید پرداخت", callback_data=f"confirmorder_{order_id}_{uid}_{pending.get('price', 0)}")
                ]])
            )
            await update.message.reply_text("✅ رسید شما دریافت شد!\nبعد از تأیید ادمین، سرویست فعال میشه 🚀")
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {e}")
        return

    if uid == ADMIN_ID and "step" in ctx.user_data:
        step = ctx.user_data["step"]
        svc = ctx.user_data["svc"]
        text = update.message.text
        if not text:
            return
        if step == "name":
            svc["name"] = text
            ctx.user_data["step"] = "price"
            await update.message.reply_text("قیمت (تومان) را بفرست:")
        elif step == "price":
            try:
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
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, msg))
    logger.info("ربات شروع شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
