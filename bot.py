"""
ربات فروشگاه خدمات تلگرام
نیازمندی‌ها: pip install python-telegram-bot requests
"""

import logging
import json
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = "8838210157:AAGyT2CI1Un4z9ok_hicEWcxGANOvmkkZN0"
ADMIN_ID   = 6825957050
ZARINPAL_MERCHANT = "YOUR-ZARINPAL-MERCHANT-ID"
BOT_USERNAME = "WG_SHEKAN_bot"

(
    MAIN_MENU, VIEW_SERVICES, VIEW_CART, CHECKOUT,
    ADMIN_MENU, ADMIN_ADD_NAME, ADMIN_ADD_DESC,
    ADMIN_ADD_PRICE, ADMIN_ADD_ID,
) = range(9)

DB_FILE = "shop_data.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {"services": [], "orders": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_db():
    if not os.path.exists(DB_FILE):
        data = {
            "services": [
                {"id": 1, "name": "خدمت نمونه ۱", "desc": "توضیحات خدمت اول", "price": 50000},
                {"id": 2, "name": "خدمت نمونه ۲", "desc": "توضیحات خدمت دوم", "price": 100000},
            ],
            "orders": []
        }
        save_db(data)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

carts: dict[int, list] = {}

def get_cart(user_id: int) -> list:
    return carts.get(user_id, [])

def add_to_cart(user_id: int, service: dict):
    if user_id not in carts:
        carts[user_id] = []
    carts[user_id].append(service)

def clear_cart(user_id: int):
    carts[user_id] = []

def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🛍 مشاهده خدمات", callback_data="services")],
        [InlineKeyboardButton("🛒 سبد خرید", callback_data="cart")],
        [InlineKeyboardButton("📦 سفارش‌های من", callback_data="my_orders")],
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(buttons)

def services_keyboard(services: list) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(
        f"{s['name']} — {s['price']:,} تومان",
        callback_data=f"buy_{s['id']}"
    )] for s in services]
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)

def cart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 پرداخت", callback_data="pay")],
        [InlineKeyboardButton("🗑 خالی کردن سبد", callback_data="clear_cart")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ])

def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن خدمت", callback_data="admin_add")],
        [InlineKeyboardButton("📋 لیست خدمات", callback_data="admin_list")],
        [InlineKeyboardButton("📊 سفارش‌ها", callback_data="admin_orders")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"سلام {user.first_name} عزیز! 👋\n\nبه فروشگاه ما خوش اومدی.",
        reply_markup=main_menu_keyboard(user.id)
    )

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    db = load_db()

    if data == "back_main":
        await query.edit_message_text(
            "منوی اصلی:", reply_markup=main_menu_keyboard(user_id)
        )

    elif data == "services":
        services = db["services"]
        if not services:
            await query.edit_message_text("❌ هیچ خدمتی موجود نیست.", reply_markup=main_menu_keyboard(user_id))
            return
        text = "🛍 *خدمات موجود:*\n\n"
        for s in services:
            text += f"• *{s['name']}*\n  {s['desc']}\n  💰 {s['price']:,} تومان\n\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=services_keyboard(services))

    elif data.startswith("buy_"):
        sid = int(data.split("_")[1])
        service = next((s for s in db["services"] if s["id"] == sid), None)
        if service:
            add_to_cart(user_id, service)
            await query.answer(f"✅ {service['name']} به سبد اضافه شد!", show_alert=True)
        else:
            await query.answer("❌ خدمت یافت نشد.", show_alert=True)

    elif data == "cart":
        cart = get_cart(user_id)
        if not cart:
            await query.edit_message_text("🛒 سبد خرید شما خالیه.", reply_markup=main_menu_keyboard(user_id))
            return
        text = "🛒 *سبد خرید:*\n\n"
        total = 0
        for item in cart:
            text += f"• {item['name']} — {item['price']:,} تومان\n"
            total += item["price"]
        text += f"\n💰 *جمع کل: {total:,} تومان*"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=cart_keyboard())

    elif data == "clear_cart":
        clear_cart(user_id)
        await query.edit_message_text("🗑 سبد خرید خالی شد.", reply_markup=main_menu_keyboard(user_id))

    elif data == "pay":
        cart = get_cart(user_id)
        if not cart:
            await query.edit_message_text("سبد خرید خالیه!", reply_markup=main_menu_keyboard(user_id))
            return
        total = sum(i["price"] for i in cart)
        pay_url = create_zarinpal_payment(total, user_id, query.from_user.username or str(user_id))
        if pay_url:
            await query.edit_message_text(
                f"💳 برای پرداخت {total:,} تومان روی لینک زیر کلیک کن:\n\n{pay_url}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 پرداخت آنلاین", url=pay_url)],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
                ])
            )
        else:
            await query.edit_message_text("❌ خطا در اتصال به درگاه پرداخت.", reply_markup=main_menu_keyboard(user_id))

    elif data == "my_orders":
        orders = [o for o in db["orders"] if o["user_id"] == user_id]
        if not orders:
            await query.edit_message_text("📦 هنوز سفارشی ثبت نکردی.", reply_markup=main_menu_keyboard(user_id))
            return
        text = "📦 *سفارش‌های شما:*\n\n"
        for o in orders[-10:]:
            text += f"• شناسه: `{o['id']}` | {o['total']:,} تومان | {o['status']}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard(user_id))

    elif data == "admin" and user_id == ADMIN_ID:
        await query.edit_message_text("⚙️ پنل مدیریت:", reply_markup=admin_keyboard())

    elif data == "admin_list" and user_id == ADMIN_ID:
        services = db["services"]
        text = "📋 *لیست خدمات:*\n\n"
        for s in services:
            text += f"🔹 ID:{s['id']} | {s['name']} | {s['price']:,} تومان\n  /del_{s['id']} برای حذف\n\n"
        await query.edit_message_text(text or "هیچ خدمتی وجود نداره.", parse_mode="Markdown", reply_markup=admin_keyboard())

    elif data == "admin_orders" and user_id == ADMIN_ID:
        orders = db["orders"][-20:]
        if not orders:
            await query.edit_message_text("هیچ سفارشی وجود نداره.", reply_markup=admin_keyboard())
            return
        text = "📊 *آخرین سفارش‌ها:*\n\n"
        for o in orders:
            text += f"👤 یوزر: {o['user_id']} | {o['total']:,} تومان | {o['status']}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_keyboard())

    elif data == "admin_add" and user_id == ADMIN_ID:
        ctx.user_data["adding_service"] = {}
        await query.edit_message_text("📝 نام خدمت را بفرست:")
        ctx.user_data["step"] = "name"

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text.startswith("/del_") and user_id == ADMIN_ID:
        try:
            sid = int(text.split("_")[1])
            db = load_db()
            db["services"] = [s for s in db["services"] if s["id"] != sid]
            save_db(db)
            await update.message.reply_text(f"✅ خدمت {sid} حذف شد.")
        except:
            await update.message.reply_text("❌ خطا در حذف.")
        return

    if user_id != ADMIN_ID or "step" not in ctx.user_data:
        return

    step = ctx.user_data["step"]
    svc = ctx.user_data.get("adding_service", {})

    if step == "name":
        svc["name"] = text
        ctx.user_data["adding_service"] = svc
        ctx.user_data["step"] = "desc"
        await update.message.reply_text("📝 توضیحات خدمت را بفرست:")

    elif step == "desc":
        svc["desc"] = text
        ctx.user_data["adding_service"] = svc
        ctx.user_data["step"] = "price"
        await update.message.reply_text("💰 قیمت (به تومان) را بفرست:")

    elif step == "price":
        try:
            price = int(text.replace(",", "").replace("،", ""))
            db = load_db()
            new_id = max((s["id"] for s in db["services"]), default=0) + 1
            svc["id"] = new_id
            svc["price"] = price
            db["services"].append(svc)
            save_db(db)
            ctx.user_data.pop("step", None)
            ctx.user_data.pop("adding_service", None)
            await update.message.reply_text(
                f"✅ خدمت اضافه شد!\n\n"
                f"📌 نام: {svc['name']}\n"
                f"📝 توضیحات: {svc['desc']}\n"
                f"💰 قیمت: {price:,} تومان",
                reply_markup=admin_keyboard()
            )
        except ValueError:
            await update.message.reply_text("❌ قیمت باید عدد باشه. دوباره بفرست:")

def create_zarinpal_payment(amount_toman: int, user_id: int, username: str) -> str | None:
    import requests
    try:
        res = requests.post(
            "https://api.zarinpal.com/pg/v4/payment/request.json",
            json={
                "merchant_id": ZARINPAL_MERCHANT,
                "amount": amount_toman * 10,
                "description": f"خرید خدمات - کاربر {username}",
                "callback_url": f"https://t.me/{BOT_USERNAME}",
                "metadata": {"user_id": user_id}
            },
            timeout=10
        )
        data = res.json()
        if data["data"]["code"] == 100:
            authority = data["data"]["authority"]
            return f"https://www.zarinpal.com/pg/StartPay/{authority}"
    except Exception as e:
        logger.error(f"ZarinPal error: {e}")
    return None

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("ربات شروع به کار کرد...")
    app.run_polling()

if __name__ == "__main__":
    main()
