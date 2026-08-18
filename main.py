import os
import json
import random
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
PORT = int(os.getenv("PORT", "8443"))
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set.")

if not CHANNEL_USERNAME:
    raise ValueError("CHANNEL_USERNAME is not set.")

if not ADMIN_ID_RAW:
    raise ValueError("ADMIN_ID is not set.")

ADMIN_ID = int(ADMIN_ID_RAW)

if not RENDER_EXTERNAL_HOSTNAME:
    raise ValueError("RENDER_EXTERNAL_HOSTNAME is not set.")


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# FILES
# =========================================================

USERS_FILE = "users.json"
BANNED_FILE = "banned.json"
STARTED_USERS_FILE = "started_users.json"


# =========================================================
# DEFAULT DATA
# =========================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


users = load_json(USERS_FILE, {})
banned_users = load_json(BANNED_FILE, {})
started_users = load_json(STARTED_USERS_FILE, {})


# =========================================================
# RUNTIME DATA
# =========================================================

bot_enabled = True

# user_id -> target_user_id
active_chats = {}

# admin_message_id -> user_id
message_map = {}

# user_id -> user_number
private_chat_users = {}


# =========================================================
# BAD WORDS
# =========================================================

bad_words = [
    "كسم",
    "زكمك",
    "يلعن بوك",
    "يلعن امك",
    "بغل",
    "زامل",
    "ميبون",
    "فانص",
    "فرواخ",
    "زبكم",
    "الزب",
    "الصب",
    "طيزك",
    "طيز",
    "طاقتك",
    "كسمك",
    "كس امك",
    "زك امك",
    "زبور",
    "زبوب",
    "عن دين امك",
    "عندينامك",
    "زك امك",
    "زب",
    "زبك",
    "fuck",
    "shit",
    "asshole",
    "bitch",
    "nigger",
    "dick",
    "pussy",
]


def contains_bad_words(text: str) -> bool:
    if not text:
        return False

    text = text.lower()

    return any(word.lower() in text for word in bad_words)


# =========================================================
# MESSAGES
# =========================================================

WELCOME_MSG = """نورت يا عسل 🌟

صل على النبي ❤️

بوت تواصل لـ Just for fun

🔽 اختر نوع الإرسال:

🟢 الوضع العام:
رسالتك تظهر في القناة.

🔒 الوضع الخاص:
رسالتك تصل فقط لـ عزو.

"""


COMMANDS_MSG = """📜 أوامر الأدمن:

/on - تشغيل البوت
/off - إيقاف الوضع العام
/ban [رقم] - حظر مستخدم
/unban [رمز] - فك الحظر
/users - مستخدمو الوضع الخاص
/chat [user_id] - بدء محادثة
/get_link - الحصول على رابط حسابك
"""


# =========================================================
# KEYBOARD
# =========================================================

def get_mode_buttons():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🟢 العام",
                callback_data="mode_public"
            )
        ],
        [
            InlineKeyboardButton(
                "🔒 الخاص",
                callback_data="mode_private"
            )
        ]
    ])


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id):

    return str(user_id) == str(ADMIN_ID)


# =========================================================
# BANNED CHECK
# =========================================================

def is_banned(user_id):

    user_id = str(user_id)

    for data in banned_users.values():

        if str(data.get("user_id")) == user_id:
            return True

    return False


# =========================================================
# USER NUMBER
# =========================================================

def get_user_number(user_id):

    user_id = str(user_id)

    if user_id not in users:

        numbers = [
            int(data["number"])
            for data in users.values()
            if "number" in data
        ]

        next_number = max(numbers, default=0) + 1

        users[user_id] = {
            "number": next_number,
            "messages": 0,
            "mode": None,
        }

        save_json(USERS_FILE, users)

    return int(users[user_id]["number"])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user:
        return

    user = update.effective_user
    user_id = str(user.id)

    started_users[user_id] = True
    save_json(STARTED_USERS_FILE, started_users)

    get_user_number(user_id)

    await update.message.reply_text(WELCOME_MSG)

    if is_admin(user.id):

        await update.message.reply_text(
            COMMANDS_MSG
        )

    await update.message.reply_text(
        "⬇️ اختر نوع الإرسال:",
        reply_markup=get_mode_buttons()
    )


# =========================================================
# BUTTONS
# =========================================================

async def handle_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return

    user = query.from_user

    await query.answer()

    user_id = str(user.id)

    if user_id not in started_users:

        started_users[user_id] = True
        save_json(
            STARTED_USERS_FILE,
            started_users
        )

    # MODE
    if query.data.startswith("mode_"):

        mode = query.data.split("_", 1)[1]

        get_user_number(user_id)

        users[user_id]["mode"] = mode

        save_json(
            USERS_FILE,
            users
        )

        mode_name = (
            "العام 🟢"
            if mode == "public"
            else "الخاص 🔒"
        )

        await query.message.reply_text(
            f"✅ تم اختيار الوضع {mode_name}.\n\n"
            "📨 أرسل رسالتك الآن."
        )


# =========================================================
# ON
# =========================================================

async def enable_bot(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global bot_enabled

    if not is_admin(update.effective_user.id):
        return

    bot_enabled = True

    await update.message.reply_text(
        "✅ تم تفعيل استقبال الرسائل العامة."
    )


# =========================================================
# OFF
# =========================================================

async def disable_bot(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global bot_enabled

    if not is_admin(update.effective_user.id):
        return

    bot_enabled = False

    await update.message.reply_text(
        "⛔️ تم إيقاف استقبال الرسائل في الوضع العام.\n"
        "🔒 الوضع الخاص ما زال يعمل."
    )


# =========================================================
# BAN
# =========================================================

async def ban_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update.effective_user.id):
        return

    if not context.args:

        await update.message.reply_text(
            "❌ الاستخدام:\n"
            "/ban 01"
        )

        return

    try:

        target_number = int(
            context.args[0]
        )

    except ValueError:

        await update.message.reply_text(
            "❌ اكتب رقم المتابع بشكل صحيح."
        )

        return

    target_uid = None

    for uid, data in users.items():

        if int(data.get("number", 0)) == target_number:

            target_uid = uid
            break

    if not target_uid:

        await update.message.reply_text(
            "❌ لم يتم العثور على هذا المتابع."
        )

        return

    code = generate_unique_code()

    banned_users[code] = {
        "user_id": target_uid,
        "number": target_number,
    }

    save_json(
        BANNED_FILE,
        banned_users
    )

    await update.message.reply_text(
        f"🚫 تم حظر المتابع رقم {target_number:02d}\n\n"
        f"🔑 رمز الحظر: {code}"
    )


# =========================================================
# GENERATE BAN CODE
# =========================================================

def generate_unique_code():

    while True:

        code = f"{random.randint(0, 999):03d}"

        if code not in banned_users:

            return code


# =========================================================
# UNBAN
# =========================================================

async def unban_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update.effective_user.id):
        return

    if not context.args:

        await update.message.reply_text(
            "❌ الاستخدام:\n"
            "/unban 123"
        )

        return

    code = context.args[0].strip()

    if code not in banned_users:

        await update.message.reply_text(
            "❌ هذا الرمز غير موجود."
        )

        return

    del banned_users[code]

    save_json(
        BANNED_FILE,
        banned_users
    )

    await update.message.reply_text(
        f"✅ تم فك الحظر.\n"
        f"🔑 الرمز: {code}"
    )


# =========================================================
# SEND MESSAGE TO USER
# =========================================================

async def send_to_user(
    context,
    target_uid,
    message
):

    if message.text:

        await context.bot.send_message(
            chat_id=int(target_uid),
            text=message.text
        )

    elif message.photo:

        await context.bot.send_photo(
            chat_id=int(target_uid),
            photo=message.photo[-1].file_id,
            caption=message.caption
        )

    elif message.video:

        await context.bot.send_video(
            chat_id=int(target_uid),
            video=message.video.file_id,
            caption=message.caption
        )

    elif message.voice:

        await context.bot.send_voice(
            chat_id=int(target_uid),
            voice=message.voice.file_id
        )

    elif message.audio:

        await context.bot.send_audio(
            chat_id=int(target_uid),
            audio=message.audio.file_id
        )

    elif message.document:

        await context.bot.send_document(
            chat_id=int(target_uid),
            document=message.document.file_id,
            caption=message.caption
        )

    else:

        raise ValueError(
            "نوع الرسالة غير مدعوم."
        )


# =========================================================
# HANDLE MESSAGES
# =========================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user or not update.message:
        return

    user = update.effective_user

    user_id = str(user.id)

    # =====================================================
    # ADMIN
    # =====================================================

    if is_admin(user.id):

        # Active private chat
        if user_id in active_chats:

            target_uid = active_chats[user_id]

            try:

                await send_to_user(
                    context,
                    target_uid,
                    update.message
                )

                await update.message.reply_text(
                    "✅ تم إرسال الرسالة."
                )

                return

            except Exception as e:

                await update.message.reply_text(
                    f"❌ تعذر إرسال الرسالة.\n\n{e}"
                )

                return

        # Reply to a private message
        if update.message.reply_to_message:

            replied_id = (
                update.message
                .reply_to_message
                .message_id
            )

            target_uid = message_map.get(
                replied_id
            )

            if target_uid:

                try:

                    await send_to_user(
                        context,
                        target_uid,
                        update.message
                    )

                    await update.message.reply_text(
                        "✅ تم إرسال الرد للمستخدم."
                    )

                    return

                except Exception as e:

                    await update.message.reply_text(
                        f"❌ تعذر إرسال الرد.\n\n{e}"
                    )

                    return

        await update.message.reply_text(
            "ℹ️ للرد على متابع، استخدم Reply على رسالته."
        )

        return

    # =====================================================
    # BANNED
    # =====================================================

    if is_banned(user_id):

        await update.message.reply_text(
            "🚫 أنت محظور من استخدام البوت."
        )

        return

    # =====================================================
    # STARTED
    # =====================================================

    started_users[user_id] = True

    save_json(
        STARTED_USERS_FILE,
        started_users
    )

    # =====================================================
    # USER NUMBER
    # =====================================================

    user_num = get_user_number(user_id)

    # =====================================================
    # MODE
    # =====================================================

    if (
        user_id not in users
        or not users[user_id].get("mode")
    ):

        await update.message.reply_text(
            "🔰 اختر نوع الإرسال أولًا:",
            reply_markup=get_mode_buttons()
        )

        return

    mode = users[user_id]["mode"]

    # =====================================================
    # GENERAL OFF
    # =====================================================

    if not bot_enabled and mode == "public":

        await update.message.reply_text(
            "⛔️ الوضع العام مغلق حاليًا.\n"
            "🔒 يمكنك استخدام الوضع الخاص."
        )

        return

    # =====================================================
    # BAD WORD FILTER
    # =====================================================

    text_to_check = (
        update.message.text
        or update.message.caption
        or ""
    )

    if contains_bad_words(text_to_check):

        await update.message.reply_text(
            "⚠️ رسالتك تحتوي على كلمات غير مسموحة وتم رفضها."
        )

        return

    # =====================================================
    # PUBLIC
    # =====================================================

    if mode == "public":

        if update.message.text:

            msg = (
                f"💌 رسالة من المتابع {user_num:02d}\n\n"
                f"{update.message.text}"
            )

            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=msg
            )

            await update.message.reply_text(
                "✅ تم إرسال رسالتك إلى القناة."
            )

            return

        # Public media not allowed
        await update.message.reply_text(
            "❌ في الوضع العام يسمح بإرسال النصوص فقط."
        )

        return

    # =====================================================
    # PRIVATE
    # =====================================================

    if mode == "private":

        tag = (
            f"👤 المتابع رقم {user_num:02d}\n"
            f"🆔 ID: {user_id}"
        )

        # TEXT
        if update.message.text:

            admin_msg = await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"{tag}\n\n"
                    f"💬 رسالة خاصة:\n\n"
                    f"{update.message.text}"
                )
            )

        # PHOTO
        elif update.message.photo:

            admin_msg = await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=update.message.photo[-1].file_id,
                caption=(
                    f"{tag}\n\n"
                    f"📷 صورة من المتابع"
                )
            )

        # VIDEO
        elif update.message.video:

            admin_msg = await context.bot.send_video(
                chat_id=ADMIN_ID,
                video=update.message.video.file_id,
                caption=(
                    f"{tag}\n\n"
                    f"🎥 فيديو من المتابع"
                )
            )

        # VOICE
        elif update.message.voice:

            admin_msg = await context.bot.send_voice(
                chat_id=ADMIN_ID,
                voice=update.message.voice.file_id,
                caption=tag
            )

        # AUDIO
        elif update.message.audio:

            admin_msg = await context.bot.send_audio(
                chat_id=ADMIN_ID,
                audio=update.message.audio.file_id,
                caption=tag
            )

        # DOCUMENT
        elif update.message.document:

            admin_msg = await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=update.message.document.file_id,
                caption=tag
            )

        else:

            await update.message.reply_text(
                "❌ نوع الرسالة غير مدعوم."
            )

            return

        # Save reply mapping
        message_map[
            admin_msg.message_id
        ] = user_id

        private_chat_users[
            user_id
        ] = user_num

        # Count message
        users[user_id]["messages"] = (
            users[user_id].get("messages", 0) + 1
        )

        save_json(
            USERS_FILE,
            users
        )

        await update.message.reply_text(
            "✅ تم إرسال رسالتك  ❤️"
        )


# =========================================================
# PRIVATE USERS
# =========================================================

async def list_private_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update.effective_user.id):
        return

    if not private_chat_users:

        await update.message.reply_text(
            "لا يوجد مستخدمون في الوضع الخاص حتى الآن."
        )

        return

    keyboard = []

    for uid, num in private_chat_users.items():

        keyboard.append([
            InlineKeyboardButton(
                f"👤 المتابع {num:02d}",
                callback_data=f"chat_{uid}"
            )
        ])

    await update.message.reply_text(
        "🧑‍💬 اختر المتابع:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# CHAT
# =========================================================

async def start_chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update.effective_user.id):
        return

    if not context.args:

        await update.message.reply_text(
            "❌ الاستخدام:\n"
            "/chat user_id"
        )

        return

    target_uid = context.args[0]

    if target_uid not in started_users:

        await update.message.reply_text(
            "❌ هذا المستخدم لم يبدأ البوت."
        )

        return

    active_chats[
        str(ADMIN_ID)
    ] = target_uid

    await update.message.reply_text(
        f"✅ المحادثة مفعلة مع المستخدم:\n"
        f"{target_uid}\n\n"
        "أرسل الآن أي رسالة وستصل إليه."
    )


# =========================================================
# CHAT BUTTON
# =========================================================

async def chat_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return

    if not is_admin(query.from_user.id):
        await query.answer()
        return

    if query.data.startswith("chat_"):

        target_uid = query.data.split(
            "_",
            1
        )[1]

        active_chats[
            str(ADMIN_ID)
        ] = target_uid

        await query.answer()

        await query.message.reply_text(
            f"✅ تم فتح المحادثة مع:\n"
            f"{target_uid}\n\n"
            "أرسل رسالتك الآن."
        )


# =========================================================
# GET USER LINK
# =========================================================

async def get_user_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    if not user.username:

        await update.message.reply_text(
            "❌ ليس لديك Username."
        )

        return

    await update.message.reply_text(
        f"🔗 رابط حسابك:\n"
        f"https://t.me/{user.username}"
    )


# =========================================================
# CHANNEL POST REPLY
# =========================================================

def extract_channel_message_id(text):

    if not text:
        return None

    pattern = rf"https://t\.me/{re.escape(CHANNEL_USERNAME.lstrip('@'))}/(\d+)"

    match = re.search(
        pattern,
        text
    )

    if not match:
        return None

    return int(match.group(1))


async def handle_channel_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return False

    if not update.message.text:
        return False

    message_text = update.message.text.strip()

    msg_id = extract_channel_message_id(
        message_text
    )

    if not msg_id:
        return False

    parts = message_text.split()

    link = None

    for part in parts:

        if f"t.me/{CHANNEL_USERNAME.lstrip('@')}/" in part:

            link = part
            break

    if not link:
        return False

    reply_text = message_text.replace(
        link,
        ""
    ).strip()

    if not reply_text:

        await update.message.reply_text(
            "❌ اكتب الرد مع رابط المنشور."
        )

        return True

    if contains_bad_words(reply_text):

        await update.message.reply_text(
            "⚠️ الرد يحتوي على كلمات غير مسموحة."
        )

        return True

    user_num = get_user_number(
        str(update.effective_user.id)
    )

    try:

        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=(
                f"💬 رد من المتابع {user_num:02d}\n\n"
                f"{reply_text}"
            ),
            reply_to_message_id=msg_id
        )

        await update.message.reply_text(
            "✅ تم نشر ردك على المنشور."
        )

    except Exception as e:

        logger.exception(e)

        await update.message.reply_text(
            "❌ تعذر نشر الرد على المنشور."
        )

    return True


# =========================================================
# MESSAGE ROUTER
# =========================================================

async def message_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    # Channel-link replies
    if not is_admin(update.effective_user.id):

        handled = await handle_channel_reply(
            update,
            context
        )

        if handled:
            return

    await handle_message(
        update,
        context
    )


# =========================================================
# HEALTH CHECK
# =========================================================

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🟢 البوت يعمل بشكل طبيعي."
    )


# =========================================================
# POST INIT
# =========================================================

async def post_init(
    application: Application
):

    webhook_url = (
        f"https://{RENDER_EXTERNAL_HOSTNAME}/"
        f"{BOT_TOKEN}"
    )

    await application.bot.set_webhook(
        url=webhook_url
    )

    logger.info(
        f"Webhook set: {webhook_url}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "on",
            enable_bot
        )
    )

    application.add_handler(
        CommandHandler(
            "off",
            disable_bot
        )
    )

    application.add_handler(
        CommandHandler(
            "ban",
            ban_user
        )
    )

    application.add_handler(
        CommandHandler(
            "unban",
            unban_user
        )
    )

    application.add_handler(
        CommandHandler(
            "users",
            list_private_users
        )
    )

    application.add_handler(
        CommandHandler(
            "chat",
            start_chat
        )
    )

    application.add_handler(
        CommandHandler(
            "get_link",
            get_user_link
        )
    )

    application.add_handler(
        CommandHandler(
            "health",
            health
        )
    )

    # Chat buttons FIRST
    application.add_handler(
        CallbackQueryHandler(
            chat_callback,
            pattern=r"^chat_"
        )
    )

    # Mode buttons
    application.add_handler(
        CallbackQueryHandler(
            handle_button,
            pattern=r"^mode_"
        )
    )

    # Messages
    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            message_router
        )
    )

    logger.info(
        "🤖 Bot is starting..."
    )

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=(
            f"https://{RENDER_EXTERNAL_HOSTNAME}/"
            f"{BOT_TOKEN}"
        )
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()
