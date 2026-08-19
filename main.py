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
CHANNEL_MESSAGES_FILE = "channel_messages.json"


# =========================================================
# JSON FUNCTIONS
# =========================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:

        logger.error(
            f"Failed to load {filename}: {e}"
        )

        return default


def save_json(filename, data):

    try:

        with open(filename, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

    except Exception as e:

        logger.error(
            f"Failed to save {filename}: {e}"
        )


# =========================================================
# DATA
# =========================================================

users = load_json(
    USERS_FILE,
    {}
)

banned_users = load_json(
    BANNED_FILE,
    {}
)

started_users = load_json(
    STARTED_USERS_FILE,
    {}
)

# channel message ID -> user ID
channel_messages = load_json(
    CHANNEL_MESSAGES_FILE,
    {}
)


# =========================================================
# RUNTIME DATA
# =========================================================

bot_enabled = True

# Admin active private chat
# ADMIN_ID -> USER_ID
active_chats = {}

# Admin message ID -> USER_ID
message_map = {}

# Users who used private mode
# USER_ID -> USER_NUMBER
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

    return any(
        word.lower() in text
        for word in bad_words
    )


# =========================================================
# MESSAGES
# =========================================================

WELCOME_MSG = """نورت يا عسل 🌟

صل على النبي ❤️

بوت تواصل مخصص للقناة.

🔽 اختر نوع الإرسال:

🟢 الوضع العام:
رسالتك تظهر في القناة.

🔒 الوضع الخاص:
رسالتك تصل فقط للإدارة.
"""


COMMANDS_MSG = """📜 أوامر الأدمن:

/on - تشغيل الوضع العام
/off - إيقاف الوضع العام
/ban [رقم] - حظر مستخدم
/unban [رمز] - فك الحظر
/users - مستخدمو الوضع الخاص
/chat [user_id] - بدء محادثة
/get_link - الحصول على رابط حسابك
"""


# =========================================================
# BUTTONS
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
# BAN CHECK
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

        numbers = []

        for data in users.values():

            if "number" in data:

                try:
                    numbers.append(
                        int(data["number"])
                    )

                except:
                    pass

        next_number = max(
            numbers,
            default=0
        ) + 1

        users[user_id] = {
            "number": next_number,
            "messages": 0,
            "public_messages": 0,
            "private_messages": 0,
            "mode": None,
        }

        save_json(
            USERS_FILE,
            users
        )

    return int(
        users[user_id]["number"]
    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    user = update.effective_user

    user_id = str(user.id)

    started_users[user_id] = True

    save_json(
        STARTED_USERS_FILE,
        started_users
    )

    get_user_number(user_id)

    await update.message.reply_text(
        WELCOME_MSG
    )

    if is_admin(user.id):

        await update.message.reply_text(
            COMMANDS_MSG
        )

    await update.message.reply_text(
        "⬇️ اختر نوع الإرسال:",
        reply_markup=get_mode_buttons()
    )


# =========================================================
# MODE BUTTON
# =========================================================

async def handle_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    user = query.from_user

    user_id = str(user.id)

    if query.data.startswith("mode_"):

        mode = query.data.split(
            "_",
            1
        )[1]

        get_user_number(user_id)

        users[user_id]["mode"] = mode

        save_json(
            USERS_FILE,
            users
        )

        if mode == "public":

            await query.message.reply_text(
                "✅ تم تفعيل 🟢 الوضع العام.\n\n"
                "📨 أرسل رسالتك الآن."
            )

        else:

            await query.message.reply_text(
                "✅ تم تفعيل 🔒 الوضع الخاص.\n\n"
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

    if not is_admin(
        update.effective_user.id
    ):
        return

    bot_enabled = True

    await update.message.reply_text(
        "✅ تم تفعيل الوضع العام."
    )


# =========================================================
# OFF
# =========================================================

async def disable_bot(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global bot_enabled

    if not is_admin(
        update.effective_user.id
    ):
        return

    bot_enabled = False

    await update.message.reply_text(
        "⛔️ تم إيقاف الوضع العام.\n"
        "🔒 الوضع الخاص ما زال يعمل."
    )


# =========================================================
# BAN CODE
# =========================================================

def generate_unique_code():

    while True:

        code = f"{random.randint(0, 999):03d}"

        if code not in banned_users:

            return code


# =========================================================
# BAN
# =========================================================

async def ban_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):
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

        if int(
            data.get("number", 0)
        ) == target_number:

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
        f"🚫 تم حظر المتابع رقم "
        f"{target_number:02d}\n\n"
        f"🔑 رمز الحظر: {code}"
    )


# =========================================================
# UNBAN
# =========================================================

async def unban_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):
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
# SEND ANY MESSAGE TO USER
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
# ADMIN REPLY TO CHANNEL MESSAGE
# =========================================================

async def handle_channel_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    """
    يتعامل مع المنشورات والردود داخل القناة.

    عندما يرد الأدمن على رسالة البوت في القناة:
    يبحث عن user_id المرتبط بالرسالة الأصلية
    ثم يرسل الرد للمستخدم في الخاص.
    """

    if not update.channel_post:
        return

    message = update.channel_post

    # لا يوجد Reply
    if not message.reply_to_message:
        return

    original_message_id = (
        message.reply_to_message.message_id
    )

    target_uid = channel_messages.get(
        str(original_message_id)
    )

    if not target_uid:
        logger.warning(
            "Channel reply received but "
            "original user was not found."
        )

        return

    try:

        # نص
        if message.text:

            await context.bot.send_message(
                chat_id=int(target_uid),
                text=(
                    "📩 رد الإدارة:\n\n"
                    f"{message.text}"
                )
            )

        # صورة
        elif message.photo:

            await context.bot.send_photo(
                chat_id=int(target_uid),
                photo=message.photo[-1].file_id,
                caption=(
                    "📩 رد الإدارة\n\n"
                    f"{message.caption or ''}"
                )
            )

        # فيديو
        elif message.video:

            await context.bot.send_video(
                chat_id=int(target_uid),
                video=message.video.file_id,
                caption=(
                    "📩 رد الإدارة\n\n"
                    f"{message.caption or ''}"
                )
            )

        # Voice
        elif message.voice:

            await context.bot.send_voice(
                chat_id=int(target_uid),
                voice=message.voice.file_id
            )

        # Audio
        elif message.audio:

            await context.bot.send_audio(
                chat_id=int(target_uid),
                audio=message.audio.file_id,
                caption=(
                    "📩 رد الإدارة\n\n"
                    f"{message.caption or ''}"
                )
            )

        # Document
        elif message.document:

            await context.bot.send_document(
                chat_id=int(target_uid),
                document=message.document.file_id,
                caption=(
                    "📩 رد الإدارة\n\n"
                    f"{message.caption or ''}"
                )
            )

        logger.info(
            f"Admin reply sent to user {target_uid}"
        )

    except Exception as e:

        logger.exception(
            f"Failed to send channel reply: {e}"
        )


# =========================================================
# HANDLE NORMAL MESSAGES
# =========================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    if not update.message:
        return

    user = update.effective_user

    user_id = str(user.id)

    # =====================================================
    # ADMIN
    # =====================================================

    if is_admin(user.id):

        # -------------------------------------------------
        # Active chat
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Reply to private message
        # -------------------------------------------------

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
            "ℹ️ للرد على متابع، استخدم Reply "
            "على رسالته."
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

    user_num = get_user_number(
        user_id
    )

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

    if (
        not bot_enabled
        and mode == "public"
    ):

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

    if contains_bad_words(
        text_to_check
    ):

        await update.message.reply_text(
            "⚠️ رسالتك تحتوي على كلمات "
            "غير مسموحة وتم رفضها."
        )

        return

    # =====================================================
    # PUBLIC MODE
    # =====================================================

    if mode == "public":

        # Currently text only
        if update.message.text:

            msg = (
                f"💌 رسالة من المتابع "
                f"{user_num:02d}\n\n"
                f"{update.message.text}"
            )

            try:

                channel_msg = (
                    await context.bot.send_message(
                        chat_id=CHANNEL_USERNAME,
                        text=msg
                    )
                )

                # -------------------------------------------------
                # IMPORTANT:
                # Save channel message ID -> user ID
                # -------------------------------------------------

                channel_messages[
                    str(channel_msg.message_id)
                ] = user_id

                save_json(
                    CHANNEL_MESSAGES_FILE,
                    channel_messages
                )

                # Count messages
                users[user_id][
                    "messages"
                ] = (
                    users[user_id]
                    .get("messages", 0)
                    + 1
                )

                users[user_id][
                    "public_messages"
                ] = (
                    users[user_id]
                    .get("public_messages", 0)
                    + 1
                )

                save_json(
                    USERS_FILE,
                    users
                )

                await update.message.reply_text(
                    "✅ تم إرسال رسالتك إلى القناة."
                )

            except Exception as e:

                logger.exception(e)

                await update.message.reply_text(
                    "❌ حدث خطأ أثناء إرسال "
                    "الرسالة إلى القناة."
                )

            return

        await update.message.reply_text(
            "❌ في الوضع العام يسمح "
            "حاليًا بإرسال النصوص فقط."
        )

        return

    # =====================================================
    # PRIVATE MODE
    # =====================================================

    if mode == "private":

        tag = (
            f"👤 المتابع رقم {user_num:02d}\n"
            f"🆔 ID: {user_id}"
        )

        try:

            # TEXT
            if update.message.text:

                admin_msg = (
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=(
                            f"{tag}\n\n"
                            f"💬 رسالة خاصة:\n\n"
                            f"{update.message.text}"
                        )
                    )
                )

            # PHOTO
            elif update.message.photo:

                admin_msg = (
                    await context.bot.send_photo(
                        chat_id=ADMIN_ID,
                        photo=update.message.photo[-1].file_id,
                        caption=(
                            f"{tag}\n\n"
                            "📷 صورة من المتابع"
                        )
                    )
                )

            # VIDEO
            elif update.message.video:

                admin_msg = (
                    await context.bot.send_video(
                        chat_id=ADMIN_ID,
                        video=update.message.video.file_id,
                        caption=(
                            f"{tag}\n\n"
                            "🎥 فيديو من المتابع"
                        )
                    )
                )

            # VOICE
            elif update.message.voice:

                admin_msg = (
                    await context.bot.send_voice(
                        chat_id=ADMIN_ID,
                        voice=update.message.voice.file_id,
                        caption=tag
                    )
                )

            # AUDIO
            elif update.message.audio:

                admin_msg = (
                    await context.bot.send_audio(
                        chat_id=ADMIN_ID,
                        audio=update.message.audio.file_id,
                        caption=tag
                    )
                )

            # DOCUMENT
            elif update.message.document:

                admin_msg = (
                    await context.bot.send_document(
                        chat_id=ADMIN_ID,
                        document=update.message.document.file_id,
                        caption=tag
                    )
                )

            else:

                await update.message.reply_text(
                    "❌ نوع الرسالة غير مدعوم."
                )

                return

            # -------------------------------------------------
            # Save admin message -> user
            # -------------------------------------------------

            message_map[
                admin_msg.message_id
            ] = user_id

            private_chat_users[
                user_id
            ] = user_num

            # -------------------------------------------------
            # Count messages
            # -------------------------------------------------

            users[user_id][
                "messages"
            ] = (
                users[user_id]
                .get("messages", 0)
                + 1
            )

            users[user_id][
                "private_messages"
            ] = (
                users[user_id]
                .get("private_messages", 0)
                + 1
            )

            save_json(
                USERS_FILE,
                users
            )

            await update.message.reply_text(
                "✅ تم إرسال رسالتك للإدارة ❤️"
            )

        except Exception as e:

            logger.exception(e)

            await update.message.reply_text(
                "❌ حدث خطأ أثناء إرسال "
                "الرسالة للإدارة."
            )


# =========================================================
# PRIVATE USERS
# =========================================================

async def list_private_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):
        return

    if not private_chat_users:

        await update.message.reply_text(
            "لا يوجد مستخدمون في الوضع "
            "الخاص حتى الآن."
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
# START CHAT
# =========================================================

async def start_chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):
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
        f"✅ تم فتح المحادثة مع المستخدم:\n"
        f"{target_uid}\n\n"
        "أرسل الآن."
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

    if not is_admin(
        query.from_user.id
    ):

        await query.answer()

        return

    if query.data.startswith(
        "chat_"
    ):

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
# GET LINK
# =========================================================

async def get_user_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    if not is_admin(user.id):

        return

    if not user.username:

        await update.message.reply_text(
            "❌ ليس لديك Username."
        )

        return

    await update.message.reply_text(
        "🔗 رابط حسابك:\n"
        f"https://t.me/{user.username}"
    )


# =========================================================
# USER REPLY TO CHANNEL POST BY LINK
# =========================================================

def extract_channel_message_id(
    text
):

    if not text:
        return None

    channel_name = (
        CHANNEL_USERNAME
        .lstrip("@")
    )

    pattern = (
        rf"https://t\.me/"
        rf"{re.escape(channel_name)}"
        rf"/(\d+)"
    )

    match = re.search(
        pattern,
        text
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


async def handle_channel_link_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return False

    if not update.message.text:
        return False

    text = update.message.text.strip()

    message_id = (
        extract_channel_message_id(
            text
        )
    )

    if not message_id:
        return False

    channel_name = (
        CHANNEL_USERNAME
        .lstrip("@")
    )

    link_pattern = (
        rf"https://t\.me/"
        rf"{re.escape(channel_name)}"
        rf"/\d+"
    )

    match = re.search(
        link_pattern,
        text
    )

    if not match:
        return False

    link = match.group(0)

    reply_text = text.replace(
        link,
        ""
    ).strip()

    if not reply_text:

        await update.message.reply_text(
            "❌ اكتب الرد مع رابط المنشور."
        )

        return True

    if contains_bad_words(
        reply_text
    ):

        await update.message.reply_text(
            "⚠️ الرد يحتوي على كلمات "
            "غير مسموحة."
        )

        return True

    user_num = get_user_number(
        str(update.effective_user.id)
    )

    try:

        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=(
                f"💬 رد من المتابع "
                f"{user_num:02d}\n\n"
                f"{reply_text}"
            ),
            reply_to_message_id=message_id
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

    # المستخدم يرسل ردًا على منشور بالقناة عبر الرابط
    if not is_admin(
        update.effective_user.id
    ):

        handled = (
            await handle_channel_link_reply(
                update,
                context
            )
        )

        if handled:
            return

    await handle_message(
        update,
        context
    )


# =========================================================
# HEALTH
# =========================================================

async def health(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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
        f"https://"
        f"{RENDER_EXTERNAL_HOSTNAME}/"
        f"{BOT_TOKEN}"
    )

    await application.bot.set_webhook(
        url=webhook_url
    )

    logger.info(
        f"✅ Webhook set: {webhook_url}"
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

    # =====================================================
    # COMMANDS
    # =====================================================

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

    # =====================================================
    # CALLBACKS
    # =====================================================

    # chat buttons MUST come before general callbacks
    application.add_handler(
        CallbackQueryHandler(
            chat_callback,
            pattern=r"^chat_"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            handle_button,
            pattern=r"^mode_"
        )
    )

    # =====================================================
    # CHANNEL POSTS
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POST,
            handle_channel_post
        )
    )

    # =====================================================
    # NORMAL MESSAGES
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            message_router
        )
    )

    # =====================================================
    # START
    # =====================================================

    logger.info(
        "🤖 Bot is starting..."
    )

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=(
            f"https://"
            f"{RENDER_EXTERNAL_HOSTNAME}/"
            f"{BOT_TOKEN}"
        )
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
