import os, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN","")
WEBAPP_URL = os.environ.get("WEBAPP_URL","https://seyedalimoosavi369.github.io/novaland_frontend")
ADMIN_ID = os.environ.get("ADMIN_ID","8030373785")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref = ctx.args[0] if ctx.args else None
    url = f"{WEBAPP_URL}{'?ref='+ref if ref else ''}"
    text = f"""🌌 *NOVA LAND METAVERSE*

سلام {user.first_name}! به دنیای متاورس TON خوش اومدی 🚀

🗺️ ۲۵۰۰ قطعه زمین دیجیتال روی TON
💚 بخر · بساز · بفروش · اجاره بده
📸 عکس بذار · درآمد بگیر
🏆 توی لیدربورد بدرخش

━━━━━━━━━━━━━━━
🎁 ایردراپ: ۱۰۰ نفر اول = ۱ زمین رایگان
👥 رفرال: هر ۱۰ نفر = ۱ زمین رایگان
💰 کمیسیون: فقط ۱۰٪
📊 هر ۱۰۰۰ بازدید = ۰.۰۱ TON"""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌌 ورود به NOVA LAND", web_app=WebAppInfo(url=url))],
        [InlineKeyboardButton("📊 آمار", callback_data="stats"),
         InlineKeyboardButton("🏆 لیدربورد", callback_data="lb")],
        [InlineKeyboardButton("🎁 ایردراپ", callback_data="airdrop"),
         InlineKeyboardButton("👥 دعوت", callback_data="ref")],
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def admin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ دسترسی ندارید"); return
    import aiohttp
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{WEBAPP_URL.replace('github.io/novaland_frontend','')}/api/admin/stats".replace("https://seyedalimoosavi369.github.io/novaland_frontend","https://novaland-production.up.railway.app")) as r:
                d = await r.json()
        text = f"""👑 *پنل ادمین NOVA LAND*

👥 کاربران: {d.get('total_users',0)}
🗺️ زمین فروخته: {d.get('sold_lands',0)}
💎 حجم: {d.get('total_volume',0)} TON
💰 کمیسیون من: {d.get('total_commission',0)} TON
🎁 ایردراپ: {d.get('airdrop_count',0)}/100"""
    except: text = "❌ خطا در اتصال"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 ارسال TON", callback_data="adm_send")],
        [InlineKeyboardButton("👥 کاربران", callback_data="adm_users")],
        [InlineKeyboardButton("🌌 ورود به پنل", web_app=WebAppInfo(url=f"{WEBAPP_URL}?admin=1"))],
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

API_URL = os.environ.get("API_URL","https://novaland-production.up.railway.app")

async def cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    user = q.from_user
    import aiohttp

    if q.data == "stats":
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{API_URL}/api/stats") as r: d = await r.json()
            text = f"📊 *آمار NOVA LAND*\n\n🗺️ فروخته: {d['sold_lands']}\n🟢 موجود: {d['available']}\n👥 کاربران: {d['total_users']}\n💎 حجم: {d['total_volume']} TON\n🎁 ایردراپ: {d['airdrop_count']}/100 ({d['airdrop_left']} مونده)"
        except: text = "❌ خطا"
        await q.edit_message_text(text, parse_mode="Markdown")

    elif q.data == "lb":
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{API_URL}/api/leaderboard?type=lands") as r: d = await r.json()
            medals = ['🥇','🥈','🥉','4️⃣','5️⃣']
            text = "🏆 *لیدربورد NOVA LAND*\n\n"
            for i,u in enumerate(d['data'][:5]):
                text += f"{medals[i]} {u.get('first_name') or u.get('username','ناشناس')} — {u['score']} زمین\n"
        except: text = "❌ خطا"
        await q.edit_message_text(text, parse_mode="Markdown")

    elif q.data == "airdrop":
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(f"{API_URL}/api/airdrop",json={"telegram_id":user.id}) as r: d = await r.json()
            text = f"{'✅' if d.get('success') else '❌'} {d.get('message','خطا')}"
        except: text = "❌ خطا"
        await q.edit_message_text(text)

    elif q.data == "ref":
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{API_URL}/api/profile?id={user.id}") as r: d = await r.json()
            code = d.get('user',{}).get('referral_code','')
            link = f"https://t.me/{(await ctx.bot.get_me()).username}?start={code}"
            text = f"👥 *لینک دعوت:*\n\n`{link}`\n\n🎁 هر ۱۰ نفر = ۱ زمین رایگان\n📊 دعوتی‌ها: {d.get('user',{}).get('ref_count',0)}"
        except: text = "❌ خطا"
        await q.edit_message_text(text, parse_mode="Markdown")

    elif q.data == "adm_send" and str(user.id) == ADMIN_ID:
        ctx.user_data['action'] = 'send'
        await q.edit_message_text("💸 آیدی و مقدار TON:\nمثال: `123456789 0.5`", parse_mode="Markdown")

    elif q.data == "adm_users" and str(user.id) == ADMIN_ID:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{API_URL}/api/admin/users") as r: d = await r.json()
            text = "👥 *آخرین کاربران:*\n\n"
            for u in d.get('users',[])[:5]:
                text += f"• {u.get('first_name','ناشناس')} | {u['telegram_id']} | {u.get('lc',0)} زمین\n"
        except: text = "❌ خطا"
        await q.edit_message_text(text, parse_mode="Markdown")

async def msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if str(user.id) == ADMIN_ID and ctx.user_data.get('action') == 'send':
        try:
            import aiohttp
            parts = update.message.text.split()
            to_id, amount = parts[0], float(parts[1])
            async with aiohttp.ClientSession() as s:
                async with s.post(f"{API_URL}/api/admin/send",json={"to_id":to_id,"amount":amount,"note":"ادمین"}) as r: d = await r.json()
            await update.message.reply_text(f"✅ {amount} TON به {to_id} ارسال شد")
            ctx.user_data.pop('action',None)
        except: await update.message.reply_text("❌ فرمت اشتباه\nمثال: `123456789 0.5`", parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))
    print("🚀 NOVA LAND Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
