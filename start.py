# TechVJ/start.py
# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import asyncio
import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.errors import (
    FloodWait, UserIsBlocked, InputUserDeactivated,
    UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied, RPCError
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM
from database.db import db
from TechVJ.strings import HELP_TXT
from user_client import TechVJUser

# Tunables via env (optional)
RATE_DELAY = float(os.environ.get("RATE_DELAY", "0.4"))            # delay after every API call
WAIT_BETWEEN_MSGS = float(os.environ.get("WAIT_BETWEEN_MSGS", "2.0"))  # batch pacing

class batch_temp:
    IS_BATCH = {}  # key per-user (PM) ya per-user (group), fallback chat id

async def safe_send(awaitable):
    while True:
        try:
            result = await awaitable
            await asyncio.sleep(RATE_DELAY)
            return result
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except RPCError:
            await asyncio.sleep(1.5)

async def downstatus(client, statusfile, message, chat):
    while not os.path.exists(statusfile):
        await asyncio.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as f:
            txt = f.read()
        try:
            await safe_send(client.edit_message_text(chat, message.id, f"**Downloaded:** **{txt}**"))
        except Exception:
            await asyncio.sleep(5)

async def upstatus(client, statusfile, message, chat):
    while not os.path.exists(statusfile):
        await asyncio.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as f:
            txt = f.read()
        try:
            await safe_send(client.edit_message_text(chat, message.id, f"**Uploaded:** **{txt}**"))
        except Exception:
            await asyncio.sleep(5)

def progress(current, total, message, type_):
    with open(f"{message.id}{type_}status.txt", "w") as f:
        f.write(f"{current * 100 / total:.1f}%")

@Client.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    # Group me /start aaye to bhi silent info ok
    if message.from_user:
        if not await db.is_user_exist(message.from_user.id):
            await db.add_user(message.from_user.id, message.from_user.first_name)

    buttons = [
        [InlineKeyboardButton("❣️ Developer", url="https://t.me/ig_magic")],
        [
            InlineKeyboardButton("🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ", url="https://t.me/sss_cgl"),
            InlineKeyboardButton("🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url="https://t.me/ssc_cgl_tg"),
        ],
    ]
    await safe_send(client.send_message(
        chat_id=message.chat.id,
        text=(
            f"<b>👋 Hi {message.from_user.mention if message.from_user else 'there'}, "
            f"I can fetch restricted content via its Telegram post link.\n\n"
            f"Private: just paste link.\n"
            f"Group: paste link (privacy disabled) or use /save <link>.\n\n"
            f"For restricted content with user sessions, use /login in PM.</b>"
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
        reply_to_message_id=message.id,
    ))

@Client.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    await safe_send(client.send_message(chat_id=message.chat.id, text=f"{HELP_TXT}"))

@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    user_key = (message.from_user.id if message.from_user else message.chat.id)
    batch_temp.IS_BATCH[user_key] = True
    await safe_send(client.send_message(chat_id=message.chat.id, text="**Batch Successfully Cancelled.**"))

# Group support: private OR group dono me chale
@Client.on_message(filters.text & (filters.private | filters.group))
async def save(client: Client, message: Message):
    # per-user batching key (group me bhi user-wise)
    sender_id = message.from_user.id if message.from_user else None
    user_key = sender_id if sender_id else message.chat.id

    # Anonymous admin case
    if not sender_id and message.chat.type in ("group", "supergroup"):
        # Ya to /save <link> use karen from user account OR PM me bhejein
        if "https://t.me/" in (message.text or ""):
            return await safe_send(message.reply("Anonymous admin se links process nahi ho sakte. Apne user account se bhejein ya PM me bhejein."))
        # warna ignore
        return

    text = message.text or ""

    # Global string-session user se join (sirf LOGIN_SYSTEM False hone par)
    if (("https://t.me/+" in text) or ("https://t.me/joinchat/" in text)) and LOGIN_SYSTEM is False:
        if TechVJUser is None:
            await safe_send(client.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id))
            return
        try:
            await TechVJUser.join_chat(text)
            await safe_send(client.send_message(message.chat.id, "**Chat Joined**", reply_to_message_id=message.id))
        except UserAlreadyParticipant:
            await safe_send(client.send_message(message.chat.id, "**Chat already Joined**", reply_to_message_id=message.id))
        except InviteHashExpired:
            await safe_send(client.send_message(message.chat.id, "**Invalid Link**", reply_to_message_id=message.id))
        except Exception as e:
            await safe_send(client.send_message(message.chat.id, f"**Error** : __{e}__", reply_to_message_id=message.id))
        return

    # Only handle t.me links
    if "https://t.me/" not in text:
        return

    if batch_temp.IS_BATCH.get(user_key) == False:
        return await safe_send(message.reply_text(
            "**One Task Is Already Processing. Wait For It To Complete. Use /cancel to stop.**"
        ))

    datas = text.split("/")
    temp = datas[-1].replace("?single", "").split("-")
    fromID = int(temp[0].strip())
    try:
        toID = int(temp[1].strip())
    except Exception:
        toID = fromID

    batch_temp.IS_BATCH[user_key] = False

    for msgid in range(fromID, toID + 1):
        if batch_temp.IS_BATCH.get(user_key):
            break

        # Choose which account fetches the restricted message
        if LOGIN_SYSTEM is True:
            user_data = await db.get_session(sender_id)
            if user_data is None:
                await safe_send(message.reply("**To download restricted content, please /login in PM first.**"))
                batch_temp.IS_BATCH[user_key] = True
                return
            try:
                acc = Client("saverestricted", session_string=user_data, api_hash=API_HASH, api_id=API_ID)
                await acc.start()
            except Exception:
                batch_temp.IS_BATCH[user_key] = True
                return await safe_send(message.reply("**Your Login Session Expired. /logout then /login again.**"))
        else:
            if TechVJUser is None:
                batch_temp.IS_BATCH[user_key] = True
                await safe_send(client.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id))
                return
            acc = TechVJUser

        # private (/c/) or bot (/b/) or public
        if "https://t.me/c/" in text:
            chatid = int("-100" + datas[4])
            try:
                await handle_private(client, acc, message, chatid, msgid, user_key)
            except Exception as e:
                if ERROR_MESSAGE is True:
                    await safe_send(client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id))

        elif "https://t.me/b/" in text:
            username = datas[4]
            try:
                await handle_private(client, acc, message, username, msgid, user_key)
            except Exception as e:
                if ERROR_MESSAGE is True:
                    await safe_send(client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id))

        else:
            username = datas[3]
            try:
                msg = await client.get_messages(username, msgid)  # get_messages rate-limits are lenient
            except UsernameNotOccupied:
                await safe_send(client.send_message(message.chat.id, "The username is not occupied by anyone", reply_to_message_id=message.id))
                return
            try:
                await safe_send(client.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id))
            except Exception:
                try:
                    await handle_private(client, acc, message, username, msgid, user_key)
                except Exception as e:
                    if ERROR_MESSAGE is True:
                        await safe_send(client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id))

        await asyncio.sleep(WAIT_BETWEEN_MSGS)

    batch_temp.IS_BATCH[user_key] = True

async def handle_private(client: Client, acc, message: Message, chatid, msgid: int, user_key):
    msg: Message = await acc.get_messages(chatid, msgid)
    if msg.empty:
        return
    msg_type = get_message_type(msg)
    if not msg_type:
        return

    chat = message.chat.id
    if batch_temp.IS_BATCH.get(user_key):
        return

    if "Text" == msg_type:
        try:
            await safe_send(client.send_message(
                chat, msg.text, entities=msg.entities, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML
            ))
            return
        except Exception as e:
            if ERROR_MESSAGE is True:
                await safe_send(client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML))
            return

    smsg = await safe_send(client.send_message(message.chat.id, "**Downloading**", reply_to_message_id=message.id))
    asyncio.create_task(downstatus(client, f"{message.id}downstatus.txt", smsg, chat))
    try:
        file = await acc.download_media(msg, progress=progress, progress_args=[message, "down"])
        if os.path.exists(f"{message.id}downstatus.txt"):
            os.remove(f"{message.id}downstatus.txt")
    except Exception as e:
        if ERROR_MESSAGE is True:
            await safe_send(client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML))
        try:
            await safe_send(client.delete_messages(message.chat.id, [smsg.id]))
        except Exception:
            pass
        return

    if batch_temp.IS_BATCH.get(user_key):
        return
    asyncio.create_task(upstatus(client, f"{message.id}upstatus.txt", smsg, chat))

    caption = msg.caption if msg.caption else None
    if batch_temp.IS_BATCH.get(user_key):
        return

    try:
        if "Document" == msg_type:
            try:
                ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
            except Exception:
                ph_path = None
            await safe_send(client.send_document(
                chat, file, thumb=ph_path, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML,
                progress=progress, progress_args=[message, "up"]
            ))
            if ph_path: 
                try: os.remove(ph_path)
                except Exception: pass

        elif "Video" == msg_type:
            try:
                ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
            except Exception:
                ph_path = None
            await safe_send(client.send_video(
                chat, file, duration=msg.video.duration, width=msg.video.width, height=msg.video.height,
                thumb=ph_path, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML,
                progress=progress, progress_args=[message, "up"]
            ))
            if ph_path:
                try: os.remove(ph_path)
                except Exception: pass

        elif "Animation" == msg_type:
            await safe_send(client.send_animation(chat, file, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML))
        elif "Sticker" == msg_type:
            await safe_send(client.send_sticker(chat, file, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML))
        elif "Voice" == msg_type:
            await safe_send(client.send_voice(
                chat, file, caption=caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML, progress=progress, progress_args=[message, "up"]
            ))
        elif "Audio" == msg_type:
            try:
                ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
            except Exception:
                ph_path = None
            await safe_send(client.send_audio(
                chat, file, thumb=ph_path, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML,
                progress=progress, progress_args=[message, "up"]
            ))
            if ph_path:
                try: os.remove(ph_path)
                except Exception: pass
        elif "Photo" == msg_type:
            await safe_send(client.send_photo(chat, file, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML))
    except Exception as e:
        if ERROR_MESSAGE is True:
            await safe_send(client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML))

    if os.path.exists(f"{message.id}upstatus.txt"):
        try: os.remove(f"{message.id}upstatus.txt")
        except Exception: pass
        try: os.remove(file)
        except Exception: pass

    try:
        await safe_send(client.delete_messages(message.chat.id, [smsg.id]))
    except Exception:
        pass

def get_message_type(msg: pyrogram.types.messages_and_media.message.Message):
    try:
        msg.document.file_id
        return "Document"
    except Exception:
        pass
    try:
        msg.video.file_id
        return "Video"
    except Exception:
        pass
    try:
        msg.animation.file_id
        return "Animation"
    except Exception:
        pass
    try:
        msg.sticker.file_id
        return "Sticker"
    except Exception:
        pass
    try:
        msg.voice.file_id
        return "Voice"
    except Exception:
        pass
    try:
        msg.audio.file_id
        return "Audio"
    except Exception:
        pass
    try:
        msg.photo.file_id
        return "Photo"
    except Exception:
        pass
    try:
        msg.text
        return "Text"
    except Exception:
        pass
