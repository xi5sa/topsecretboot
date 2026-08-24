import os
import json
import random
import logging
import re

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from telegram.error import TelegramError


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = int(
    os.getenv("ADMIN_ID", "123456789")
)

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME"
)

CHANNEL_INVITE_LINK = os.getenv(
    "CHANNEL_INVITE_LINK"
)

PORT = int(
    os.getenv("PORT", "8443")
)

RENDER_EXTERNAL_HOSTNAME = os.getenv(
    "RENDER_EXTERNAL_HOSTNAME"
)


if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN is not set."
    )

if not CHANNEL_USERNAME:
    raise ValueError(
        "CHANNEL_USERNAME is not set."
    )

if not CHANNEL_INVITE_LINK:
    raise ValueError(
        "CHANNEL_INVITE_LINK is not set."
    )

if not RENDER_EXTERNAL_HOSTNAME:
    raise ValueError(
        "RENDER_EXTERNAL_HOSTNAME is not set."
    )


# =========================================================
# DATA DIRECTORY
# =========================================================

DATA_DIR = os.getenv(
    "DATA_DIR",
    "."
)

os.makedirs(
    DATA_DIR,
    exist_ok=True
)


# =========================================================
# FILES
# =========================================================

USERS_FILE = os.path.join(
    DATA_DIR,
    "users.json"
)

BANNED_FILE = os.path.join(
    DATA_DIR,
    "banned.json"
)

STARTED_USERS_FILE = os.path.join(
    DATA_DIR,
    "started_users.json"
)

ALLOWED_USERS_FILE = os.path.join(
    DATA_DIR,
    "allowed_users.json"
)

BOT_STATE_FILE = os.path.join(
    DATA_DIR,
    "bot_state.json"
)

CHANNEL_MESSAGES_FILE = os.path.join(
    DATA_DIR,
    "channel_messages.json"
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# =========================================================
# JSON FUNCTIONS
# =========================================================

def load_json(
    filename,
    default
):

    if not os.path.exists(filename):
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        logger.error(
            f"Error loading {filename}: {e}"
        )

        return default


def save_json(
    filename,
    data
):

    try:

        temp_file = (
            filename + ".tmp"
        )

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_file,
            filename
        )

    except Exception as e:

        logger.error(
            f"Error saving {filename}: {e}"
        )


# =========================================================
# LOAD DATA
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

allowed_users = load_json(
    ALLOWED_USERS_FILE,
    {}
)

channel_messages = load_json(
    CHANNEL_MESSAGES_FILE,
    {}
)

bot_state = load_json(
    BOT_STATE_FILE,
    {}
)


# =========================================================
# BOT STATE
# =========================================================

# الحالة محفوظة من آخر تشغيل
bot_enabled = bot_state.get(
    "bot_enabled",
    True
)


def save_bot_state():

    bot_state["bot_enabled"] = (
        bot_enabled
    )

    save_json(
        BOT_STATE_FILE,
        bot_state
    )


# =========================================================
# RUNTIME DATA
# =========================================================

private_chat_users = {}

active_chats = {}

message_map = {}


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
    "pussy"
]


def contains_bad_words(
    text
):

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

بوت تواصل خاص بالقناة.

🔽 اختر نوع الإرسال:

🟢 الوضع العام:
رسالتك تظهر في القناة.

🔒 الوضع الخاص:
رسالتك تصل فقط للإدارة.

المطور: @UQ_Ov
"""


COMMANDS_MSG = """📜 أوامر الأدمن:

/start - بدء البوت
/on - تشغيل الوضع العام
/off - إيقاف الوضع العام
/state - معرفة حالة البوت
/ban [رقم] - حظر مستخدم
/unban [رمز] - فك الحظر
/users - مستخدمو الوضع الخاص
/chat [user_id] - بدء محادثة مع مستخدم
/get_link - الحصول على رابط حسابك
"""


# =========================================================
# SUBSCRIPTION
# =========================================================

SUBSCRIBE_MSG = """🔒 لا يمكنك استخدام البوت حاليًا.

لازم تكون مشترك في القناة أولًا.

اشترك في القناة ثم اضغط:
«✅ تحقق من الاشتراك»
"""


def subscription_buttons():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📢 الاشتراك في القناة",
                url=CHANNEL_INVITE_LINK
            )
        ],

        [
            InlineKeyboardButton(
                "✅ تحقق من الاشتراك",
                callback_data="check_subscription"
            )
        ]

    ])


# =========================================================
# MODE BUTTONS
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

def is_admin(
    user_id
):

    return str(user_id) == str(
        ADMIN_ID
    )


# =========================================================
# ALLOWED USERS
# =========================================================

def add_allowed_user(
    user_id
):

    user_id = str(
        user_id
    )

    allowed_users[user_id] = {
        "user_id": user_id,
        "allowed": True
    }

    save_json(
        ALLOWED_USERS_FILE,
        allowed_users
    )


def remove_allowed_user(
    user_id
):

    user_id = str(
        user_id
    )

    if user_id in allowed_users:

        del allowed_users[user_id]

        save_json(
            ALLOWED_USERS_FILE,
            allowed_users
        )


# =========================================================
# SUBSCRIPTION CHECK
# =========================================================

async def check_subscription(
    context,
    user_id
):

    """
    تحقق صامت من اشتراك المستخدم.

    لا نرسل أي رسالة هنا.
    """

    try:

        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=int(user_id)
        )

        if member.status in (
            "member",
            "administrator",
            "creator"
        ):

            return True

        if (
            member.status == "restricted"
            and getattr(
                member,
                "is_member",
                False
            )
        ):

            return True

        return False

    except TelegramError as e:

        logger.warning(
            f"Subscription check failed "
            f"for {user_id}: {e}"
        )

        return False

    except Exception as e:

        logger.error(
            f"Subscription error: {e}"
        )

        return False


# =========================================================
# ENSURE SUBSCRIPTION
# =========================================================

async def ensure_subscription(
    update,
    context
):

    if not update.effective_user:
        return False

    user_id = str(
        update.effective_user.id
    )

    # الأدمن لا يحتاج اشتراك
    if is_admin(user_id):
        return True

    # -----------------------------------------------------
    # تحقق صامت
    # -----------------------------------------------------

    subscribed = await check_subscription(
        context,
        user_id
    )

    # -----------------------------------------------------
    # إذا مشترك
    # -----------------------------------------------------

    if subscribed:

        # يحفظ بصمت
        add_allowed_user(
            user_id
        )

        return True

    # -----------------------------------------------------
    # إذا غير مشترك
    # -----------------------------------------------------

    # نحذفه من قائمة المسموحين
    remove_allowed_user(
        user_id
    )

    # فقط هنا نعرض رسالة الاشتراك
    if update.message:

        await update.message.reply_text(
            SUBSCRIBE_MSG,
            reply_markup=subscription_buttons()
        )

    elif update.callback_query:

        await update.callback_query.message.reply_text(
            SUBSCRIBE_MSG,
            reply_markup=subscription_buttons()
        )

    return False


# =========================================================
# USER NUMBER
# =========================================================

def get_user_number(
    user_id
):

    user_id = str(
        user_id
    )

    if user_id not in users:

        numbers = []

        for data in users.values():

            try:

                numbers.append(
                    int(
                        data.get(
                            "number",
                            0
                        )
                    )
                )

            except:
                pass

        next_number = (
            max(
                numbers,
                default=0
            ) + 1
        )

        users[user_id] = {

            "number": next_number,

            "messages": 0,

            "public_messages": 0,

            "private_messages": 0,

            "mode": None
        }

        save_json(
            USERS_FILE,
            users
        )

    return int(
        users[user_id]["number"]
    )


# =========================================================
# BANNED
# =========================================================

def is_banned(
    user_id
):

    user_id = str(
        user_id
    )

    return any(
        str(data.get("user_id")) == user_id
        for data in banned_users.values()
    )


def generate_unique_code():

    while True:

        code = (
            f"{random.randint(0, 999):03d}"
        )

        if code not in banned_users:

            return code


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    # الاشتراك
    if not await ensure_subscription(
        update,
        context
    ):
        return

    user_id = str(
        update.effective_user.id
    )

    # حفظ أنه بدأ البوت
    started_users[user_id] = True

    save_json(
        STARTED_USERS_FILE,
        started_users
    )

    get_user_number(
        user_id
    )

    await update.message.reply_text(
        WELCOME_MSG
    )

    # أوامر الأدمن
    if is_admin(user_id):

        await update.message.reply_text(
            COMMANDS_MSG
        )

    await update.message.reply_text(
        "⬇️ اختر نوع الإرسال:",
        reply_markup=get_mode_buttons()
    )


# =========================================================
# BUTTON HANDLER
# =========================================================

async def handle_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return

    user_id = str(
        query.from_user.id
    )

    # =====================================================
    # CHECK SUBSCRIPTION BUTTON
    # =====================================================

    if query.data == "check_subscription":

        subscribed = await check_subscription(
            context,
            user_id
        )

        if subscribed:

            add_allowed_user(
                user_id
            )

            await query.answer(
                "✅ تم التحقق بنجاح"
            )

            await query.message.reply_text(
                "✅ تمام، تقدر تستخدم البوت الآن.",
                reply_markup=get_mode_buttons()
            )

        else:

            remove_allowed_user(
                user_id
            )

            await query.answer(
                "❌ لم يتم العثور على اشتراك",
                show_alert=True
            )

            await query.message.reply_text(
                SUBSCRIBE_MSG,
                reply_markup=subscription_buttons()
            )

        return

    # =====================================================
    # MODE
    # =====================================================

    if query.data.startswith(
        "mode_"
    ):

        # تحقق صامت
        if not await ensure_subscription(
            update,
            context
        ):
            return

        mode = query.data.split(
            "_",
            1
        )[1]

        get_user_number(
            user_id
        )

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

        await query.answer()


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

    # حفظ الحالة
    save_bot_state()

    await update.message.reply_text(
        "✅ تم تشغيل الوضع العام.\n\n"
        "💾 تم حفظ الحالة."
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

    # حفظ الحالة
    save_bot_state()

    await update.message.reply_text(
        "⛔️ تم إيقاف الوضع العام.\n\n"
        "💾 تم حفظ الحالة.\n\n"
        "🔒 الوضع الخاص ما زال يعمل."
    )


# =========================================================
# STATE
# =========================================================

async def state_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):
        return

    if bot_enabled:

        status = "🟢 الوضع العام يعمل"

    else:

        status = "🔴 الوضع العام متوقف"

    await update.message.reply_text(
        f"⚙️ حالة البوت:\n\n"
        f"{status}\n\n"
        f"👥 المسموح لهم حاليًا: "
        f"{len(allowed_users)}"
    )


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

    except:

        await update.message.reply_text(
            "❌ رقم غير صحيح."
        )

        return

    target_uid = None

    for uid, data in users.items():

        if int(
            data.get(
                "number",
                0
            )
        ) == target_number:

            target_uid = uid
            break

    if not target_uid:

        await update.message.reply_text(
            "❌ لم يتم العثور على المستخدم."
        )

        return

    code = generate_unique_code()

    banned_users[code] = {
        "user_id": target_uid,
        "number": target_number
    }

    save_json(
        BANNED_FILE,
        banned_users
    )

    # أيضًا نحذفه من المسموحين
    remove_allowed_user(
        target_uid
    )

    await update.message.reply_text(
        f"🚫 تم حظر المتابع "
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
            "/unban رمز"
        )

        return

    code = context.args[0]

    if code not in banned_users:

        await update.message.reply_text(
            "❌ الرمز غير موجود."
        )

        return

    del banned_users[code]

    save_json(
        BANNED_FILE,
        banned_users
    )

    await update.message.reply_text(
        "✅ تم فك الحظر."
    )


# =========================================================
# SEND TO USER
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
# NORMAL MESSAGE
# =========================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    if not update.message:
        return

    user_id = str(
        update.effective_user.id
    )

    # =====================================================
    # ADMIN
    # =====================================================

    if is_admin(user_id):

        # -----------------------------------------------
        # محادثة مباشرة
        # -----------------------------------------------

        if user_id in active_chats:

            target_uid = active_chats[
                user_id
            ]

            try:

                await send_to_user(
                    context,
                    target_uid,
                    update.message
                )

                await update.message.reply_text(
                    "✅ تم إرسال الرسالة."
                )

            except Exception as e:

                await update.message.reply_text(
                    f"❌ تعذر إرسال الرسالة.\n{e}"
                )

            return

        # -----------------------------------------------
        # الرد على رسالة مستخدم
        # -----------------------------------------------

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
                        "✅ تم إرسال الرد."
                    )

                except Exception as e:

                    await update.message.reply_text(
                        f"❌ تعذر إرسال الرد.\n{e}"
                    )

                return

        await update.message.reply_text(
            "❌ استخدم Reply على رسالة المتابع."
        )

        return

    # =====================================================
    # USER
    # =====================================================

    # تحقق صامت في الخلفية
    if not await ensure_subscription(
        update,
        context
    ):
        return

    # حظر
    if is_banned(user_id):

        return

    # رقم المستخدم
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
    # PUBLIC OFF
    # =====================================================

    if (
        mode == "public"
        and not bot_enabled
    ):

        await update.message.reply_text(
            "⛔️ الوضع العام مغلق حاليًا.\n\n"
            "🔒 يمكنك استخدام الوضع الخاص."
        )

        return

    # =====================================================
    # BAD WORDS
    # =====================================================

    text = (
        update.message.text
        or update.message.caption
        or ""
    )

    if contains_bad_words(text):

        await update.message.reply_text(
            "⚠️ تحتوي رسالتك على كلمات "
            "غير مسموحة وتم رفضها."
        )

        return

    # =====================================================
    # PUBLIC
    # =====================================================

    if mode == "public":

        if not update.message.text:

            await update.message.reply_text(
                "❌ الوضع العام يسمح "
                "حاليًا بإرسال النصوص فقط."
            )

            return

        msg = (
            f"💌 رسالة من المتابع "
            f"{user_num:02d}:\n\n"
            f"{update.message.text}"
        )

        try:

            channel_msg = (
                await context.bot.send_message(
                    chat_id=CHANNEL_USERNAME,
                    text=msg
                )
            )

            # حفظ رسالة القناة
            # لربط الرد بالمستخدم
            channel_messages[
                str(channel_msg.message_id)
            ] = user_id

            save_json(
                CHANNEL_MESSAGES_FILE,
                channel_messages
            )

            users[user_id][
                "messages"
            ] += 1

            users[user_id][
                "public_messages"
            ] += 1

            save_json(
                USERS_FILE,
                users
            )

            await update.message.reply_text(
                "✅ تم إرسال رسالتك للقناة."
            )

        except Exception as e:

            logger.exception(e)

            await update.message.reply_text(
                "❌ حدث خطأ أثناء إرسال الرسالة."
            )

        return

    # =====================================================
    # PRIVATE
    # =====================================================

    if mode == "private":

        tag = (
            f"👤 المتابع رقم "
            f"{user_num:02d}\n"
            f"🆔 ID: {user_id}"
        )

        try:

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

            elif update.message.voice:

                admin_msg = (
                    await context.bot.send_voice(
                        chat_id=ADMIN_ID,
                        voice=update.message.voice.file_id,
                        caption=tag
                    )
                )

            elif update.message.audio:

                admin_msg = (
                    await context.bot.send_audio(
                        chat_id=ADMIN_ID,
                        audio=update.message.audio.file_id,
                        caption=tag
                    )
                )

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

            # ربط رسالة الأدمن بالمستخدم
            message_map[
                admin_msg.message_id
            ] = user_id

            private_chat_users[
                user_id
            ] = user_num

            users[user_id][
                "messages"
            ] += 1

            users[user_id][
                "private_messages"
            ] += 1

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
                "❌ حدث خطأ أثناء إرسال الرسالة."
            )


# =========================================================
# MESSAGE ROUTER
# =========================================================

async def message_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    # الأدمن
    if is_admin(
        update.effective_user.id
    ):

        await handle_message(
            update,
            context
        )

        return

    # المستخدم:
    # تحقق صامت
    if not await ensure_subscription(
        update,
        context
    ):
        return

    await handle_message(
        update,
        context
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
            "لا يوجد مستخدمون في الوضع الخاص."
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

    # تحقق صامت من أنه لا يزال مشتركًا
    subscribed = await check_subscription(
        context,
        target_uid
    )

    if not subscribed:

        remove_allowed_user(
            target_uid
        )

        await update.message.reply_text(
            "❌ هذا المستخدم لم يعد مشتركًا "
            "في القناة."
        )

        return

    active_chats[
        str(ADMIN_ID)
    ] = target_uid

    await update.message.reply_text(
        f"✅ المحادثة مفتوحة مع:\n"
        f"{target_uid}\n\n"
        f"أرسل رسالتك الآن."
    )


# =========================================================
# CHAT CALLBACK
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

    target_uid = query.data.split(
        "_",
        1
    )[1]

    subscribed = await check_subscription(
        context,
        target_uid
    )

    if not subscribed:

        remove_allowed_user(
            target_uid
        )

        await query.answer(
            "❌ المستخدم لم يعد مشتركًا.",
            show_alert=True
        )

        return

    active_chats[
        str(ADMIN_ID)
    ] = target_uid

    await query.answer()

    await query.message.reply_text(
        f"✅ المحادثة مفتوحة مع {target_uid}."
    )


# =========================================================
# GET LINK
# =========================================================

async def get_user_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):
        return

    user = update.effective_user

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
# CHANNEL POST
# =========================================================

async def handle_channel_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.channel_post:
        return

    message = update.channel_post

    # فقط المنشورات التي تم حفظها
    # يمكن ربطها بالمستخدم
    if not message.reply_to_message:
        return

    original_id = (
        message
        .reply_to_message
        .message_id
    )

    target_uid = channel_messages.get(
        str(original_id)
    )

    if not target_uid:
        return

    try:

        if message.text:

            await context.bot.send_message(
                chat_id=int(target_uid),
                text=(
                    "📩 رد الإدارة:\n\n"
                    f"{message.text}"
                )
            )

        elif message.photo:

            await context.bot.send_photo(
                chat_id=int(target_uid),
                photo=message.photo[-1].file_id,
                caption=(
                    "📩 رد الإدارة"
                )
            )

        elif message.video:

            await context.bot.send_video(
                chat_id=int(target_uid),
                video=message.video.file_id,
                caption=(
                    "📩 رد الإدارة"
                )
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

    except Exception as e:

        logger.exception(
            f"Channel reply error: {e}"
        )


# =========================================================
# WEBHOOK
# =========================================================

async def post_init(
    application
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
        f"Webhook set: {webhook_url}"
    )

    logger.info(
        f"General mode: {bot_enabled}"
    )

    logger.info(
        f"Allowed users: "
        f"{len(allowed_users)}"
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # -----------------------------------------------------
    # Commands
    # -----------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "on",
            enable_bot
        )
    )

    app.add_handler(
        CommandHandler(
            "off",
            disable_bot
        )
    )

    app.add_handler(
        CommandHandler(
            "state",
            state_command
        )
    )

    app.add_handler(
        CommandHandler(
            "ban",
            ban_user
        )
    )

    app.add_handler(
        CommandHandler(
            "unban",
            unban_user
        )
    )

    app.add_handler(
        CommandHandler(
            "users",
            list_private_users
        )
    )

    app.add_handler(
        CommandHandler(
            "chat",
            start_chat
        )
    )

    app.add_handler(
        CommandHandler(
            "get_link",
            get_user_link
        )
    )

    # -----------------------------------------------------
    # Callbacks
    # -----------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            chat_callback,
            pattern=r"^chat_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            handle_button
        )
    )

    # -----------------------------------------------------
    # Channel posts
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POST,
            handle_channel_post
        )
    )

    # -----------------------------------------------------
    # Normal messages
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            message_router
        )
    )

    # -----------------------------------------------------
    # Webhook
    # -----------------------------------------------------

    print("🤖 البوت يعمل...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=(
            f"https://"
            f"{RENDER_EXTERNAL_HOSTNAME}/"
            f"{BOT_TOKEN}"
        )
    )
