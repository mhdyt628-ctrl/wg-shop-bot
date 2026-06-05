import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8838210157:AAGyT2CI1Un4z9ok_hicEWcxGANOvmkkZN0"
ADMIN_ID = 6825957050
DB_FILE = "shop_data.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {"services": [
            {"id": 1, "name": "خدمت نمونه ۱", "desc": "توضیحات اول", "price": 50000},
            {"id": 2, "name": "خدمت نمونه ۲", "desc": "توضیحات دوم", "price": 100000},
        ], "orders": []}
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
        [InlineKeyboardButton("🛍 خدمات", callback_data="services")],
        [InlineKeyboardButton("🛒 سبد خرید", callback_data="cart")],
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
    await update.message.reply_text(
        f"سلام {update.effective_user.first_name}! 👋\nبه فروشگاه خوش اومدی.",
        reply_markup=main_menu(update.effective_user.id)
    )

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
        text = "🛍 *خدمات:*\n\n" + "".join(f"• *{s['name']}* — {s['price']:,} تومان\n  {s['desc']}\n\n" for s in svcs)
        btns = [[InlineKeyboardButton(f"خرید: {s['name']}", callback_data=f"buy_{s['id']}")] for s in svcs]
        btns.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))
    elif d.startswith("buy_"):
        sid = int(d.split("_")[1])
        svc = next((s for s in db["services"] if s["id"] == sid), None)
        if svc:
            carts.setdefault(uid, []).append(svc)
            await q.answer(f"✅ {svc['name']} اضافه شد!", show_alert=True)
    elif d == "cart":
        cart = carts.get(uid, [])
        if not cart:
            await q.edit_message_text("🛒 سبد خالیه.", reply_markup=main_menu(uid))
            return
        total = sum(i["price"] for i in cart)
        text = "🛒 *سبد خرید:*\n\n" + "".join(f"• {i['name']} — {i['price']:,} تومان\n" for i in cart)
        text += f"\n💰 *جمع: {total:,} تومان*"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 پرداخت", callback_data="pay")],
            [InlineKeyboardButton("🗑 خالی کردن", callback_data="clear")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")],
        ]))
    elif d == "clear":
        carts[uid] = []
        await q.edit_message_text("سبد خالی شد.", reply_markup=main_menu(uid))
    elif d == "pay":
        cart = carts.get(uid, [])
        if not cart:
            await q.edit_message_text("سبد خالیه!", reply_markup=main_menu(uid))
            return
        total = sum(i["price"] for i in cart)
        await q.edit_message_text(f"💳 مبلغ: {total:,} تومان\n\nبا ادمین تماس بگیرید.", reply_markup=main_menu(uid))
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
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(btn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))
    logger.info("ربات شروع شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
