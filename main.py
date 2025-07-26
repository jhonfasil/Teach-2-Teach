import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

REGISTER, TEACH_SUBJECT, LEARN_SUBJECT = range(3)
DB_FILE = "students.json"
subject_list = ["Math", "English", "Biology", "Chemistry", "Civics", "Physics"]

def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def calculate_avg(ratings):
    if not ratings:
        return 0
    return round(sum(ratings) / len(ratings), 2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to Teach2Teach!\nWhat's your full name?")
    return REGISTER

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    if not username:
        await update.message.reply_text("⚠️ Please set a Telegram username first.")
        return ConversationHandler.END

    context.user_data['name'] = update.message.text
    context.user_data['username'] = f"@{username}"
    reply_keyboard = [[s] for s in subject_list]
    await update.message.reply_text("✅ What subject can you TEACH?", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return TEACH_SUBJECT

async def select_teach_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['can_teach'] = update.message.text
    reply_keyboard = [[s] for s in subject_list if s != update.message.text]
    await update.message.reply_text("📘 What subject do you want to LEARN?", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return LEARN_SUBJECT

async def select_learn_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['want_to_learn'] = update.message.text
    user_id = str(update.effective_user.id)
    db = load_db()
    db[user_id] = {
        "name": context.user_data['name'],
        "username": context.user_data['username'],
        "can_teach": context.user_data['can_teach'],
        "want_to_learn": context.user_data['want_to_learn'],
        "ratings": []
    }
    save_db(db)
    await update.message.reply_text("🎉 Registered! Type /match to find a study partner.")
    return ConversationHandler.END

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    if user_id not in db:
        await update.message.reply_text("❗You need to register first using /start.")
        return

    user = db[user_id]
    matches = []
    for peer_id, peer in db.items():
        if peer_id != user_id:
            if user["want_to_learn"] == peer["can_teach"]:
                avg_rating = calculate_avg(peer.get("ratings", []))
                matches.append(f"- {peer['username']} teaches {peer['can_teach']} (⭐ {avg_rating}/5)")

    if matches:
        await update.message.reply_text("🎯 Matches found:\n" + "\n".join(matches))
    else:
        await update.message.reply_text("😔 No match found now. Try again later.")

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /rate @username 5")
        return

    target_username = args[0]
    try:
        rating = int(args[1])
        if rating < 1 or rating > 5:
            raise ValueError()
    except:
        await update.message.reply_text("Please enter a number from 1 to 5.")
        return

    found = False
    for user_id in db:
        if db[user_id]["username"] == target_username:
            db[user_id].setdefault("ratings", []).append(rating)
            save_db(db)
            found = True
            await update.message.reply_text(f"✅ Rated {target_username} with ⭐ {rating}/5")
            break

    if not found:
        await update.message.reply_text("❌ User not found.")

# ✅ YOUR BOT TOKEN HERE
app = ApplicationBuilder().token("7948565705:AAEjM4D2iCWbQ5wKRWKf7106tHduiJtIGds").build()

# Handlers
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
        TEACH_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_teach_subject)],
        LEARN_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_learn_subject)],
    },
    fallbacks=[]
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler("match", match))
app.add_handler(CommandHandler("rate", rate))

app.run_polling()
