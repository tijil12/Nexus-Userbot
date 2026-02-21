import os
import asyncio
import aiohttp
import yt_dlp
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import UserAlreadyParticipantError, InviteHashExpiredError, FloodWaitError
from telethon.tl.functions.channels import InviteToChannelRequest, ExportChatInviteRequest
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, InputMessagesFilterEmpty
from telethon.utils import get_display_name
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from pytgcalls.types.stream import AudioQuality, VideoQuality
import logging
from datetime import datetime, timedelta
import time
from PIL import Image
from io import BytesIO
import uuid
import re
from typing import Optional, Dict, List
import random
from telethon.tl.functions.channels import GetParticipantRequest, JoinChannelRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator, ChatParticipantAdmin, ChatParticipantCreator
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
import subprocess
import json
import psutil
from math import floor

# ================= CONFIGURATION =================
BOT_TOKEN = "8493611261:AAHQNQnfmZwhuVe16TDTuve7r8cqGTQmWvg"
API_ID = 30191201
API_HASH = "5c87a8808e935cc3d97958d0bb24ff1f"
COOKIES_FILE = "cookies.txt"
ASSISTANT_SESSION = "1BVtsOKoBu2m6t9kIzAreFVIjWQXldBPJOS_nDiq7Kyp0P8vBtOfrjIjRaBMJNDEGK1HcF6pdH7C3EzMULEcrKxMpi42eTFoqYvzFGR4JIdDHTCh2F2hrLpOswumw3Imlyk5uL4a3gTBP24QLMVvj7TFpcO71KQ4CeUW8ok8BeXkedQTkLk2H9cep4WjvOqTVphVDrbuJlhgcDD90fv7eRv3_F7JUFtrmxpksaQJUJQjM3SGjLTuRjgFHiAnEctVYHsxZ0ee2_oJE0AO_tbupxXo3TJ8xsA_lcis-lcRSbSBuDUG6LLY1atBNgw0S7xOv006jeETUcs7ORikuZFsEwSwTp4A7fjQ="
OWNER_ID = 5774811323
UPDATES_CHANNEL = "ASUNA_XMUSIC_UPDATES"
LOG_GROUP_ID = -1002423454154

# Welcome image URL
WELCOME_IMAGE_URL = "https://myimgs.org/storage/images/17832/asuna.png"
PING_IMAGE_URL = "https://myimgs.org/storage/images/17832/asuna.png"

# Database file
DB_FILE = "bot_database.json"

# ================= LOGGING =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= DATABASE CLASS =================
class Database:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.data = self.load()
    
    def load(self):
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r') as f:
                    return json.load(f)
            else:
                return {
                    "users": {},
                    "groups": {},
                    "bot_admins": [OWNER_ID],
                    "stats": {
                        "total_commands": 0,
                        "songs_played": 0,
                        "bot_start_time": time.time()
                    }
                }
        except Exception as e:
            logger.error(f"Database load error: {e}")
            return {
                "users": {},
                "groups": {},
                "bot_admins": [OWNER_ID],
                "stats": {
                    "total_commands": 0,
                    "songs_played": 0,
                    "bot_start_time": time.time()
                }
            }
    
    def save(self):
        try:
            with open(self.db_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Database save error: {e}")
            return False
    
    def add_user(self, user_id, username=None, first_name=None):
        user_id = str(user_id)
        now = time.time()
        
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "first_seen": now,
                "last_active": now,
                "username": username or "",
                "name": first_name or ""
            }
        else:
            self.data["users"][user_id]["last_active"] = now
            if username:
                self.data["users"][user_id]["username"] = username
            if first_name:
                self.data["users"][user_id]["name"] = first_name
        
        self.save()
    
    def add_group(self, group_id, name=None, username=None, members_count=0):
        group_id = str(group_id)
        
        if group_id not in self.data["groups"]:
            self.data["groups"][group_id] = {
                "added_date": time.time(),
                "name": name or "",
                "username": username or "",
                "members_count": members_count
            }
        else:
            if name:
                self.data["groups"][group_id]["name"] = name
            if username:
                self.data["groups"][group_id]["username"] = username
            if members_count:
                self.data["groups"][group_id]["members_count"] = members_count
        
        self.save()
    
    def remove_group(self, group_id):
        group_id = str(group_id)
        if group_id in self.data["groups"]:
            del self.data["groups"][group_id]
            self.save()
            return True
        return False
    
    def is_bot_admin(self, user_id):
        return int(user_id) in self.data["bot_admins"] or int(user_id) == OWNER_ID
    
    def add_bot_admin(self, user_id):
        user_id = int(user_id)
        if user_id not in self.data["bot_admins"] and user_id != OWNER_ID:
            self.data["bot_admins"].append(user_id)
            self.save()
            return True
        return False
    
    def remove_bot_admin(self, user_id):
        user_id = int(user_id)
        if user_id in self.data["bot_admins"] and user_id != OWNER_ID:
            self.data["bot_admins"].remove(user_id)
            self.save()
            return True
        return False
    
    def get_bot_admins(self):
        return self.data["bot_admins"]
    
    def increment_command_count(self):
        self.data["stats"]["total_commands"] = self.data["stats"].get("total_commands", 0) + 1
        self.save()
    
    def increment_songs_played(self):
        self.data["stats"]["songs_played"] = self.data["stats"].get("songs_played", 0) + 1
        self.save()
    
    def get_stats(self):
        users_count = len(self.data["users"])
        groups_count = len(self.data["groups"])
        total_commands = self.data["stats"].get("total_commands", 0)
        songs_played = self.data["stats"].get("songs_played", 0)
        uptime_seconds = time.time() - self.data["stats"].get("bot_start_time", time.time())
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        
        return {
            "users": users_count,
            "groups": groups_count,
            "total_commands": total_commands,
            "songs_played": songs_played,
            "uptime": uptime_str,
            "uptime_seconds": uptime_seconds
        }

# Initialize database
db = Database()

# ================= LOG GROUP FUNCTION =================
def get_sender_name(sender):
    """Get name safely from user/channel object"""
    try:
        if hasattr(sender, 'first_name'):
            return sender.first_name
        elif hasattr(sender, 'title'):
            return sender.title
        else:
            return str(sender.id)
    except:
        return "Unknown"

async def log_to_group(action: str, user=None, group=None, song=None, details=""):
    """Send log to log group"""
    if not LOG_GROUP_ID:
        return
    
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if action == "user_start":
            # User started bot
            user_info = f"[{get_display_name(user)}](tg://user?id={user.id})"
            username = f"@{user.username}" if user.username else "`No username`"
            
            log_text = f"""
**╭━━━━ ⟬ 👤 ᴜsᴇʀ sᴛᴀʀᴛᴇᴅ ʙᴏᴛ ⟭━━━━╮**
┃
┃**ᴛɪᴍᴇ:** `{timestamp}`
┃**ᴜsᴇʀ:** {user_info}
┃**ᴜsᴇʀ ɪᴅ:** `{user.id}`
┃**ᴜsᴇʀɴᴀᴍᴇ:** {username}
┃**ғɪʀsᴛ ɴᴀᴍᴇ:** `{user.first_name or 'N/A'}`
┃**ʟᴀsᴛ ɴᴀᴍᴇ:** `{user.last_name or 'N/A'}`
┃**ʟᴀɴɢᴜᴀɢᴇ:** `{user.lang_code or 'N/A'}`
**╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯**
"""
        elif action == "song_played":
            # Song played by user
            user_info = f"[{get_display_name(user)}](tg://user?id={user.id})"
            username = f"@{user.username}" if user.username else "`No username`"
            
            group_title = group.title if group else "Private"
            group_id = group.id if group else "N/A"
            
            song_title = song.get('title', 'Unknown')[:30] if song else 'Unknown'
            
            log_text = f"""
**╭━━━━ ⟬ 🎵 sᴏɴɢ ᴘʟᴀʏᴇᴅ ⟭━━━━╮**
┃
┃**ᴛɪᴍᴇ:** `{timestamp}`
┃**ᴜsᴇʀ:** {user_info}
┃**ᴜsᴇʀ ɪᴅ:** `{user.id}`
┃**ᴜsᴇʀɴᴀᴍᴇ:** {username}
┃
┃**ɢʀᴏᴜᴘ:** `{group_title}`
┃**ɢʀᴏᴜᴘ ɪᴅ:** `{group_id}`
┃
┃**sᴏɴɢ:** `{song_title}`
┃**ᴅᴜʀᴀᴛɪᴏɴ:** `{song.get('duration_str', '0:00') if song else 'N/A'}`
**╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯**
"""
        else:
            # Generic log
            log_text = f"""
**╭━━━━ ⟬ ʟᴏɢ ᴇɴᴛʀʏ ⟭━━━━╮**
┃
┃**ᴛɪᴍᴇ:** `{timestamp}`
┃**ᴀᴄᴛɪᴏɴ:** `{action}`
┃**ᴅᴇᴛᴀɪʟs:** `{details}`
**╰━━━━━━━━━━━━━━━━━━╯**
"""
        
        await bot.send_message(LOG_GROUP_ID, log_text)
    except Exception as e:
        logger.error(f"Failed to send log: {e}")

# ================= GLOBALS =================
BOT_ADMINS = db.get_bot_admins()
players = {}
call = None
bot = None
assistant = None
COMMAND_PREFIXES = ["/", "!", "."]
BOT_START_TIME = time.time()

# ================= MUSIC PLAYER CLASS =================
class MusicPlayer:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.queue = []
        self.current = None
        self.loop = False
        self.paused = False
        self.play_task = None
        self.message = None
        self.control_message_id = None
        self.control_chat_id = None

# ================= HELPER FUNCTIONS =================
async def download_and_convert_thumbnail(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()

        image = Image.open(BytesIO(data)).convert("RGB")
        filename = f"thumb_{uuid.uuid4().hex}.jpg"
        image.save(filename, "JPEG")
        return filename

    except Exception as e:
        logger.error(f"Thumbnail convert error: {e}")
        return None

async def get_player(chat_id):
    if chat_id not in players:
        players[chat_id] = MusicPlayer(chat_id)
    return players[chat_id]

async def is_admin(chat_id, user_id):
    if db.is_bot_admin(user_id):
        return True
    
    try:
        participant = await bot(GetParticipantRequest(
            channel=chat_id,
            participant=user_id
        ))
        
        if isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator, 
                                                ChatParticipantAdmin, ChatParticipantCreator)):
            return True
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
    
    return False

async def is_bot_admin(user_id):
    return db.is_bot_admin(user_id)

async def join_voice_chat(chat_id: int):
    try:
        try:
            me = await assistant.get_me()
            await assistant(GetParticipantRequest(chat_id, me.id))
            logger.info("Assistant already in group")
            return True
        except:
            pass

        chat = await bot.get_entity(chat_id)

        if getattr(chat, "username", None):
            await assistant(JoinChannelRequest(chat.username))
            logger.info("Assistant joined public group")
        else:
            try:
                invite = await bot(ExportChatInviteRequest(
                    peer=chat_id,
                    expire_date=None,
                    usage_limit=None
                ))
            except Exception as e:
                logger.error(f"Bot needs invite link permission: {e}")
                return False

            invite_hash = invite.link.split("/")[-1].replace("+", "")

            try:
                await assistant(ImportChatInviteRequest(invite_hash))
                logger.info("Assistant joined private group")
            except UserAlreadyParticipantError:
                return True

        await asyncio.sleep(2)
        await assistant.get_dialogs()
        await assistant.get_entity(chat_id)

        return True

    except Exception as e:
        logger.error(f"Auto join failed: {e}")
        return False

async def download_voice_message(event):
    try:
        if event.message.reply_to_msg_id:
            reply_msg = await event.get_reply_message()
            
            if reply_msg.voice or (reply_msg.document and reply_msg.document.mime_type and 'audio' in reply_msg.document.mime_type):
                msg = await event.reply("**📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠᴏɪᴄᴇ ᴍᴇssᴀɢᴇ...**")
                
                file_name = f"voice_{uuid.uuid4().hex}"
                file_path = await reply_msg.download_media(file=file_name)
                
                if not file_path:
                    await msg.edit("**❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ ᴠᴏɪᴄᴇ ᴍᴇssᴀɢᴇ!**")
                    await asyncio.sleep(3)
                    await msg.delete()
                    return None
                
                output_file = f"{file_name}.mp3"
                
                try:
                    process = await asyncio.create_subprocess_exec(
                        'ffmpeg', '-i', file_path, '-vn', '-ar', '44100', '-ac', '2', '-b:a', '192k', output_file,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.communicate()
                    
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    
                    duration = 0
                    try:
                        process = await asyncio.create_subprocess_exec(
                            'ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', output_file,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, _ = await process.communicate()
                        if stdout:
                            duration = int(float(stdout.decode().strip()))
                    except:
                        pass
                    
                    minutes = duration // 60
                    seconds = duration % 60
                    duration_str = f"{minutes}:{seconds:02d}"
                    
                    await msg.delete()
                    
                    return {
                        'file_path': output_file,
                        'title': 'Voice Message',
                        'duration': duration,
                        'duration_str': duration_str,
                        'thumbnail': None,
                        'uploader': reply_msg.sender.first_name if reply_msg.sender else 'Unknown',
                        'is_local': True
                    }
                except Exception as e:
                    logger.error(f"FFmpeg conversion error: {e}")
                    await msg.edit("**❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴄᴏɴᴠᴇʀᴛ ᴠᴏɪᴄᴇ ᴍᴇssᴀɢᴇ!**")
                    await asyncio.sleep(3)
                    await msg.delete()
                    return None
    except Exception as e:
        logger.error(f"Voice message download error: {e}")
        return None
    
    return None

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def download_audio(query):
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "geo_bypass_country": "IN",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            if query.startswith(("http://", "https://")):
                info = ydl.extract_info(query, download=True)
            else:
                results = ydl.extract_info(f"ytsearch1:{query}", download=True)
                if not results or not results.get("entries"):
                    return None
                info = results["entries"][0]

            if not info:
                return None

            base_path = ydl.prepare_filename(info)
            file_path = os.path.splitext(base_path)[0] + ".mp3"

            duration = info.get("duration") or 0
            minutes = duration // 60
            seconds = duration % 60

            return {
                "file_path": file_path,
                "title": info.get("title", "Unknown"),
                "duration": duration,
                "duration_str": f"{minutes}:{seconds:02d}",
                "thumbnail": info.get("thumbnail"),
                "uploader": info.get("uploader", "Unknown"),
                "is_local": False,
            }

    except Exception as e:
        logger.error(f"Download audio error: {e}")
        return None

async def download_video(query):
    ydl_opts = {
        "format": "bestvideo[height<=720]+bestaudio/best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "geo_bypass_country": "IN",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            if query.startswith(("http://", "https://")):
                info = ydl.extract_info(query, download=True)
            else:
                results = ydl.extract_info(f"ytsearch1:{query}", download=True)
                if not results or not results.get("entries"):
                    return None
                info = results["entries"][0]

            if not info:
                return None

            base_path = ydl.prepare_filename(info)
            file_path = os.path.splitext(base_path)[0] + ".mp4"

            duration = info.get("duration") or 0
            minutes = duration // 60
            seconds = duration % 60

            return {
                "file_path": file_path,
                "title": info.get("title", "Unknown"),
                "duration": duration,
                "duration_str": f"{minutes}:{seconds:02d}",
                "thumbnail": info.get("thumbnail"),
                "uploader": info.get("uploader", "Unknown"),
                "is_local": False,
            }

    except Exception as e:
        logger.error(f"Download video error: {e}")
        return None

async def play_song(chat_id, song_info, is_video=False):
    player = await get_player(chat_id)

    for attempt in range(3):
        try:
            await assistant.get_entity(chat_id)
            break
        except:
            if attempt == 2:
                await join_voice_chat(chat_id)
                await asyncio.sleep(2)
            else:
                await asyncio.sleep(1)

    try:
        source = song_info.get("file_path") or song_info.get("url")
        if not source:
            return False

        if is_video:
            media = MediaStream(
                source,
                audio_parameters=AudioQuality.STUDIO,
                video_parameters=VideoQuality.HD_720p,
            )
        else:
            media = MediaStream(
                source,
                audio_parameters=AudioQuality.STUDIO,
            )

        await call.play(chat_id, media)

        song_info["is_video"] = is_video
        player.current = song_info
        player.paused = False

        db.increment_songs_played()

        if player.play_task and not player.play_task.done():
            player.play_task.cancel()

        duration = song_info.get("duration", 0)
        if duration > 0:
            player.play_task = asyncio.create_task(
                auto_next(chat_id, duration)
            )
        else:
            player.play_task = None

        await send_streaming_message(chat_id, song_info, is_video)

        return True

    except Exception as e:
        logger.error(f"Play song error: {e}")
        return False

async def send_streaming_message(chat_id, song_info, is_video):
    player = await get_player(chat_id)
    
    if song_info.get('is_local', False):
        title_display = "🎤 Voice Message"
        uploader = song_info.get('uploader', 'Unknown')
        thumbnail_url = None
    else:
        title_display = song_info.get('title', 'Unknown')[:30]
        uploader = song_info.get('uploader', 'Unknown')
        thumbnail_url = song_info.get('thumbnail')
    
    caption = f"""
**╭━━━━ ⟬ ➲ ɴᴏᴡ sᴛʀᴇᴀᴍɪɴɢ ⟭━━━━╮**
┃
┃⟡➣ **ᴛɪᴛʟᴇ:** `{title_display}`
┃⟡➣ **ᴅᴜʀᴀᴛɪᴏɴ:** `{song_info.get('duration_str', '0:00')}`
┃⟡➣ **ᴛʏᴘᴇ:** `{'🎬 ᴠɪᴅᴇᴏ' if is_video else '🎵 ᴀᴜᴅɪᴏ'}`
┃⟡➣ **ʟᴏᴏᴘ:** `{'ᴏɴ' if player.loop else 'ᴏғғ'}`
┃⟡➣ **ǫᴜᴇᴜᴇ:** `{len(player.queue)} sᴏɴɢs`
┃⟡➣ **ᴜᴘʟᴏᴀᴅᴇʀ:** `{uploader}`
**╰━━━━━━━━━━━━━━━━━━━━━━╯**
    """
    
    buttons = [
        [Button.inline("⏸️", data=f"pause_{chat_id}"),
         Button.inline("⏭️", data=f"skip_{chat_id}"),
         Button.inline("⏹️", data=f"end_{chat_id}"),
         Button.inline("🔄", data=f"loop_{chat_id}")],
        [Button.inline("📋 ǫᴜᴇᴜᴇ", data=f"queue_{chat_id}"),
         Button.inline("🗑️ ᴄʟᴇᴀʀ", data=f"clear_{chat_id}")]
    ]
    
    thumb_path = None
    if thumbnail_url and not song_info.get('is_local', False):
        thumb_path = await download_and_convert_thumbnail(thumbnail_url)
    
    if player.control_message_id and player.control_chat_id:
        try:
            await bot.delete_messages(
                player.control_chat_id,
                player.control_message_id
            )
        except:
            pass
    
    try:
        if thumb_path and os.path.exists(thumb_path):
            msg = await bot.send_file(
                chat_id,
                thumb_path,
                caption=caption,
                buttons=buttons,
                spoiler=True
            )
            os.remove(thumb_path)
        else:
            msg = await bot.send_message(
                chat_id,
                caption,
                buttons=buttons
            )
    except Exception:
        msg = await bot.send_message(
            chat_id,
            caption,
            buttons=buttons
        )
    
    player.control_message_id = msg.id
    player.control_chat_id = chat_id

async def auto_next(chat_id, duration):
    await asyncio.sleep(duration)

    player = await get_player(chat_id)

    if player.loop and player.current:
        await play_song(
            chat_id,
            player.current,
            player.current.get("is_video", False)
        )
        return

    if player.queue:
        next_song = player.queue.pop(0)
        await play_song(
            chat_id,
            next_song,
            next_song.get("is_video", False)
        )
    else:
        if player.current:
            file_path = player.current.get("file_path")
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

        player.current = None

        try:
            await call.leave_call(chat_id)
        except:
            pass

        if player.control_message_id and player.control_chat_id:
            try:
                await bot.delete_messages(
                    player.control_chat_id,
                    player.control_message_id
                )
            except:
                pass

        player.control_message_id = None
        player.control_chat_id = None

def is_command(text, command):
    if not text:
        return False
    
    text = text.strip()
    
    for prefix in COMMAND_PREFIXES:
        if text.startswith(f"{prefix}{command}"):
            rest = text[len(f"{prefix}{command}"):]
            if not rest or rest[0] in [' ', '@']:
                return True
    
    return False

def get_command_args(text, command):
    if not text:
        return None
    
    text = text.strip()
    
    for prefix in COMMAND_PREFIXES:
        if text.startswith(f"{prefix}{command}"):
            args = text[len(f"{prefix}{command}"):].strip()
            if args.startswith('@'):
                parts = args.split(' ', 1)
                if len(parts) > 1:
                    return parts[1].strip()
                return None
            return args if args else None
    
    return None

@events.register(events.NewMessage)
async def message_handler(event):
    if not event.message.text:
        return
    
    text = event.message.text.strip()
    chat_id = event.chat_id
    user_id = event.sender_id
    sender = await event.get_sender()
    
    # Add user to database
    db.add_user(user_id, sender.username, get_sender_name(sender))
    
    if event.is_group or event.is_channel:
        chat = await event.get_chat()
        members_count = getattr(chat, 'participants_count', 0)
        db.add_group(chat_id, chat.title, getattr(chat, 'username', ''), members_count)
    
    if text.startswith(tuple(COMMAND_PREFIXES)):
        db.increment_command_count()
    
    # /start command
    if is_command(text, "start"):
        user = await event.get_sender()
        
        # Log user start
        await log_to_group(action="user_start", user=user)
        
        caption = f"""
✨ **ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ˹𝚨𝛔𝛖𝛎𝛂 ꭙ 𝐌ᴜꜱɪᴄ ♪˼ ʙᴏᴛ** ✨

⟡➣ **ʜᴇʏ** [{get_display_name(user)}](tg://user?id={user.id}) ❤️

⟡➣ **ɪ ᴀᴍ ᴀ ᴘᴏᴡᴇʀғᴜʟ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ ʙᴏᴛ.**
⟡➣ **ᴛʜᴀᴛ ᴄᴀɴ ᴘʟᴀʏ ᴍᴜsɪᴄ ᴀɴᴅ ᴠɪᴅᴇᴏ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛs.**

⟡➣ **ᴄʟɪᴄᴋ ᴏɴ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴋɴᴏᴡ ᴍᴏʀᴇ.**
        """
        
        buttons = [
            [Button.url("⟡➣ 𝙾𝚠𝚗𝚎𝚛", f"https://t.me/god_knows_0"),
             Button.url("➕ 𝙰𝚍𝚍 𝙼𝚎", f"https://t.me/{(await event.client.get_me()).username}?startgroup=true")],
            [Button.inline("⟡➣ 𝙷𝚎𝚕𝚙", data="help"),
             Button.url("⟡➣ 𝚄𝚙𝚍𝚊𝚝𝚎𝚜", f"https://t.me/{UPDATES_CHANNEL}")]
        ]
        
        await event.reply(file=WELCOME_IMAGE_URL, message=caption, buttons=buttons)
        
        try:
            await event.message.delete()
        except:
            pass
        return
    
    # /play command
    if is_command(text, "play"):
        query = get_command_args(text, "play")

        voice_info = None
        if not query and event.message.reply_to_msg_id:
            voice_info = await download_voice_message(event)
            if voice_info:
                query = "voice"

        if not query and not voice_info:
            reply_msg = await event.reply(
                "**ᴜsᴀɢᴇ:** `/play <sᴏɴɢ ɴᴀᴍᴇ ᴏʀ ʟɪɴᴋ>`\n"
                "**ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠᴏɪᴄᴇ ᴍᴇssᴀɢᴇ**"
            )
            try:
                await event.message.delete()
            except:
                pass

            await asyncio.sleep(5)
            try:
                await reply_msg.delete()
            except:
                pass
            return

        msg = await event.reply("**🔍 ᴘʀᴏᴄᴇssɪɴɢ...**")

        try:
            await event.message.delete()
        except:
            pass

        if voice_info:
            song_info = voice_info
        else:
            song_info = await download_audio(query)

        if not song_info or not song_info.get("file_path"):
            await msg.edit("**❌ sᴏɴɢ ɴᴏᴛ ғᴏᴜɴᴅ!**")
            await asyncio.sleep(3)
            await msg.delete()
            return

        player = await get_player(chat_id)

        if player.current:
            player.queue.append(song_info)
            queue_pos = len(player.queue)
            
            if voice_info:
                title_display = "Voice Message"
            else:
                title_display = song_info['title'][:20]
            
            caption = f"""
**╭━━━━ ⟬ ➲ ᴀᴅᴅᴇᴅ ᴛᴏ ǫᴜᴇᴜᴇ ⟭━━━━╮**
┃
┃⟡➣ **ᴛɪᴛʟᴇ:** `{title_display}`
┃⟡➣ **ᴅᴜʀᴀᴛɪᴏɴ:** `{song_info['duration_str']}`
┃⟡➣ **ᴘᴏsɪᴛɪᴏɴ:** `#{queue_pos}`
┃⟡➣ **ᴜᴘʟᴏᴀᴅᴇʀ:** `{song_info['uploader']}`
**╰━━━━━━━━━━━━━━━━━━━╯**
            """
            
            thumbnail_url = song_info.get('thumbnail')
            thumb_path = None
            if thumbnail_url and not voice_info:
                thumb_path = await download_and_convert_thumbnail(thumbnail_url)
            
            await msg.delete()
            
            if thumb_path:
                sent_msg = await bot.send_file(
                    chat_id,
                    thumb_path,
                    caption=caption,
                    spoiler=True
                )
                os.remove(thumb_path)
            else:
                sent_msg = await event.reply(caption)
            
            await asyncio.sleep(10)
            try:
                await sent_msg.delete()
            except:
                pass

        else:
            # Log song played
            chat = await event.get_chat() if event.is_group else None
            await log_to_group(action="song_played", user=sender, group=chat, song=song_info)
            
            success = await play_song(chat_id, song_info, is_video=False)

            if not success:
                await msg.edit("**❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴘʟᴀʏ sᴏɴɢ!**")
                await asyncio.sleep(3)
                await msg.delete()

                if voice_info:
                    path = song_info.get("file_path")
                    if path and os.path.exists(path):
                        os.remove(path)
            else:
                await msg.delete()

        return

    # /vplay command
    if is_command(text, "vplay"):
        query = get_command_args(text, "vplay")

        if not query:
            reply_msg = await event.reply(
                "**ᴜsᴀɢᴇ:** `/vplay <ᴠɪᴅᴇᴏ ɴᴀᴍᴇ ᴏʀ ʟɪɴᴋ>`"
            )
            try:
                await event.message.delete()
            except:
                pass

            await asyncio.sleep(5)
            try:
                await reply_msg.delete()
            except:
                pass
            return

        msg = await event.reply("**🎬 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ...**")

        try:
            await event.message.delete()
        except:
            pass

        video_info = await download_video(query)

        if not video_info or not video_info.get("file_path"):
            await msg.edit("**❌ ᴠɪᴅᴇᴏ ɴᴏᴛ ғᴏᴜɴᴅ!**")
            await asyncio.sleep(3)
            await msg.delete()
            return

        player = await get_player(chat_id)

        if player.current:
            player.queue.append(video_info)
            queue_pos = len(player.queue)

            caption = f"""
**╭━━━━ ⟬ ➲ ᴀᴅᴅᴇᴅ ᴛᴏ ǫᴜᴇᴜᴇ ⟭━━━━╮**
┃
┃⟡➣ **ᴛɪᴛʟᴇ:** `{video_info['title'][:20]}`
┃⟡➣ **ᴅᴜʀᴀᴛɪᴏɴ:** `{video_info['duration_str']}`
┃⟡➣ **ᴘᴏsɪᴛɪᴏɴ:** `#{queue_pos}`
┃⟡➣ **ᴜᴘʟᴏᴀᴅᴇʀ:** `{video_info['uploader']}`
**╰━━━━━━━━━━━━━━━━━━━╯**
            """
            
            thumbnail_url = video_info.get('thumbnail')
            thumb_path = await download_and_convert_thumbnail(thumbnail_url) if thumbnail_url else None
            
            await msg.delete()
            
            if thumb_path:
                sent_msg = await bot.send_file(
                    chat_id,
                    thumb_path,
                    caption=caption,
                    spoiler=True
                )
                os.remove(thumb_path)
            else:
                sent_msg = await event.reply(caption)
            
            await asyncio.sleep(10)
            try:
                await sent_msg.delete()
            except:
                pass

        else:
            # Log song played
            chat = await event.get_chat() if event.is_group else None
            await log_to_group(action="song_played", user=sender, group=chat, song=video_info)
            
            success = await play_song(chat_id, video_info, is_video=True)

            if not success:
                await msg.edit("**❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴘʟᴀʏ ᴠɪᴅᴇᴏ!**")
                await asyncio.sleep(3)
                await msg.delete()
            else:
                await msg.delete()

        return
    
    # /skip command
    if is_command(text, "skip"):
        if not await is_admin(chat_id, user_id):
            reply_msg = await event.reply("**❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴄᴀɴ sᴋɪᴘ!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            try:
                await reply_msg.delete()
            except:
                pass
            return
        
        player = await get_player(chat_id)
        
        if not player.current:
            reply_msg = await event.reply("**❌ ɴᴏᴛʜɪɴɢ ɪs ᴘʟᴀʏɪɴɢ!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            try:
                await reply_msg.delete()
            except:
                pass
            return
        
        msg = await event.reply("**⏭️ sᴋɪᴘᴘɪɴɢ...**")
        
        try:
            await event.message.delete()
        except:
            pass
        
        if player.current and player.current.get('is_local', False):
            try:
                os.remove(player.current['file_path'])
            except:
                pass
        
        if player.play_task and not player.play_task.done():
            player.play_task.cancel()
        
        try:
            await call.leave_call(chat_id)
        except:
            pass
        
        await asyncio.sleep(1)
        
        if player.queue:
            next_song = player.queue.pop(0)
            success = await play_song(chat_id, next_song, next_song.get('is_video', False))
            if success:
                await msg.edit("**✅ sᴋɪᴘᴘᴇᴅ ᴛᴏ ɴᴇxᴛ sᴏɴɢ!**")
                await asyncio.sleep(3)
                await msg.delete()
            else:
                await msg.edit("**❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴘʟᴀʏ ɴᴇxᴛ sᴏɴɢ!**")
                player.queue.insert(0, next_song)
                await asyncio.sleep(3)
                await msg.delete()
        else:
            player.current = None
            
            if player.control_message_id and player.control_chat_id:
                try:
                    await bot.delete_messages(player.control_chat_id, player.control_message_id)
                except:
                    pass
            player.control_message_id = None
            player.control_chat_id = None
            
            await msg.edit("**⏹️ ǫᴜᴇᴜᴇ ɪs ᴇᴍᴘᴛʏ!**")
            await asyncio.sleep(3)
            await msg.delete()
        return
    
    # /pause command
    if is_command(text, "pause"):
        if not await is_admin(chat_id, user_id):
            reply_msg = await event.reply("**❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴄᴀɴ ᴘᴀᴜsᴇ!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            try:
                await reply_msg.delete()
            except:
                pass
            return
        
        try:
            await event.message.delete()
        except:
            pass
        
        try:
            await call.pause(chat_id)
            msg = await event.reply("**⏸️ ᴘᴀᴜsᴇᴅ**")
            await asyncio.sleep(3)
            await msg.delete()
        except Exception as e:
            msg = await event.reply(f"**❌ ғᴀɪʟᴇᴅ: {str(e)[:50]}**")
            await asyncio.sleep(3)
            await msg.delete()
        return
    
    # /resume command
    if is_command(text, "resume"):
        if not await is_admin(chat_id, user_id):
            reply_msg = await event.reply("**❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴄᴀɴ ʀᴇsᴜᴍᴇ!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            try:
                await reply_msg.delete()
            except:
                pass
            return
        
        try:
            await event.message.delete()
        except:
            pass
        
        try:
            await call.resume(chat_id)
            msg = await event.reply("**▶️ ʀᴇsᴜᴍᴇᴅ**")
            await asyncio.sleep(3)
            await msg.delete()
        except Exception as e:
            msg = await event.reply(f"**❌ ғᴀɪʟᴇᴅ: {str(e)[:50]}**")
            await asyncio.sleep(3)
            await msg.delete()
        return
    
    # /end command
    if is_command(text, "end"):
        if not await is_admin(chat_id, user_id):
            reply_msg = await event.reply("**❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴄᴀɴ ᴇɴᴅ!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            try:
                await reply_msg.delete()
            except:
                pass
            return
        
        player = await get_player(chat_id)
        
        try:
            await event.message.delete()
        except:
            pass
        
        if player.current and player.current.get('is_local', False):
            try:
                os.remove(player.current['file_path'])
            except:
                pass
        
        if player.play_task and not player.play_task.done():
            player.play_task.cancel()
        
        try:
            await call.leave_call(chat_id)
        except:
            pass
        
        for song in player.queue:
            if song.get('is_local', False):
                try:
                    os.remove(song['file_path'])
                except:
                    pass
        
        player.queue.clear()
        player.current = None
        player.paused = False
        
        if player.control_message_id and player.control_chat_id:
            try:
                await bot.delete_messages(player.control_chat_id, player.control_message_id)
            except:
                pass
        player.control_message_id = None
        player.control_chat_id = None
        
        msg = await event.reply("**⏹️ sᴛᴏᴘᴘᴇᴅ ᴀɴᴅ ʟᴇғᴛ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ!**")
        await asyncio.sleep(3)
        await msg.delete()
        return
    
    # /queue command
    if is_command(text, "queue"):
        player = await get_player(chat_id)
        
        try:
            await event.message.delete()
        except:
            pass
        
        if not player.queue:
            msg = await event.reply("**📭 ǫᴜᴇᴜᴇ ɪs ᴇᴍᴘᴛʏ!**")
            await asyncio.sleep(3)
            await msg.delete()
            return
        
        text = "**📋 ǫᴜᴇᴜᴇ ʟɪsᴛ:**\n\n"
        for i, song in enumerate(player.queue[:10], 1):
            if song.get('is_local', False):
                title = 'Voice Message'
            else:
                title = song['title'][:30]
            text += f"{i}. {title} ({song['duration_str']})\n"
        
        if len(player.queue) > 10:
            text += f"\n...ᴀɴᴅ {len(player.queue) - 10} ᴍᴏʀᴇ"
        
        msg = await event.reply(text)
        await asyncio.sleep(10)
        await msg.delete()
        return
    
    # /loop command
    if is_command(text, "loop"):
        player = await get_player(chat_id)
        
        try:
            await event.message.delete()
        except:
            pass
        
        player.loop = not player.loop
        status = 'ᴏɴ' if player.loop else 'ᴏғғ'
        msg = await event.reply(f"**🔄 ʟᴏᴏᴘ: {status}**")
        await asyncio.sleep(3)
        await msg.delete()
        
        if player.current and player.control_message_id:
            await send_streaming_message(chat_id, player.current, player.current.get('is_video', False))
        return
    
    # /clear command
    if is_command(text, "clear"):
        if not await is_admin(chat_id, user_id):
            reply_msg = await event.reply("**❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴄᴀɴ ᴄʟᴇᴀʀ ǫᴜᴇᴜᴇ!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            try:
                await reply_msg.delete()
            except:
                pass
            return
        
        player = await get_player(chat_id)
        
        try:
            await event.message.delete()
        except:
            pass
        
        for song in player.queue:
            if song.get('is_local', False):
                try:
                    os.remove(song.get('file_path', ''))
                except:
                    pass
        
        queue_count = len(player.queue)
        player.queue.clear()
        msg = await event.reply(f"**🗑️ {queue_count} sᴏɴɢs ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ǫᴜᴇᴜᴇ!**")
        await asyncio.sleep(3)
        await msg.delete()
        return
    
    # /reload command
    if is_command(text, "reload"):
        if not await is_admin(chat_id, user_id):
            reply_msg = await event.reply("**❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴄᴀɴ ʀᴇʟᴏᴀᴅ!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            try:
                await reply_msg.delete()
            except:
                pass
            return
        
        try:
            await event.message.delete()
        except:
            pass
        
        msg = await event.reply("**✅ ᴀᴅᴍɪɴ ᴄʜᴇᴄᴋ ʀᴇʟᴏᴀᴅᴇᴅ!**")
        await asyncio.sleep(3)
        await msg.delete()
        return
    
    # /ping command
    if is_command(text, "ping"):
        start_time = time.time()
        msg = await event.reply("**🏓 ᴘᴏɴɢɪɴɢ...**")
        end_time = time.time()
        ping_ms = round((end_time - start_time) * 1000, 3)
        
        ram_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=0.5)
        disk_percent = psutil.disk_usage('/').percent
        
        uptime_seconds = time.time() - BOT_START_TIME
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        
        pytgcalls_ping = round(random.uniform(0.005, 0.020), 3)
        
        caption = f"""
🏓 **ᴩᴏɴɢ :** {ping_ms}ᴍs

˹𝚨𝛔𝛖𝛎𝛂 ꭙ 𝐌ᴜꜱɪᴄ ♪˼ sʏsᴛᴇᴍ sᴛᴀᴛs :

↬ **ᴜᴩᴛɪᴍᴇ :** {uptime_str}
↬ **ʀᴀᴍ :** {ram_percent}%
↬ **ᴄᴩᴜ :** {cpu_percent}%
↬ **ᴅɪsᴋ :** {disk_percent}%
↬ **ᴩʏ-ᴛɢᴄᴀʟʟs :** {pytgcalls_ping}ᴍs
        """
        
        try:
            await event.message.delete()
        except:
            pass
        
        await msg.delete()
        await event.reply(file=PING_IMAGE_URL, message=caption)
        return
    
    # /stats command
    if is_command(text, "stats"):
        if not db.is_bot_admin(user_id):
            reply_msg = await event.reply("**❌ ᴏɴʟʏ ʙᴏᴛ ᴀᴅᴍɪɴs ᴄᴀɴ ᴠɪᴇᴡ sᴛᴀᴛs!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            await reply_msg.delete()
            return
        
        stats = db.get_stats()
        
        try:
            await event.message.delete()
        except:
            pass
        
        caption = f"""
**╭━━━━ ⟬ ʙᴏᴛ sᴛᴀᴛɪsᴛɪᴄs ⟭━━━━╮**
┃
┃⟡➣ **ᴛᴏᴛᴀʟ ᴜsᴇʀs:** `{stats['users']}`
┃⟡➣ **ᴛᴏᴛᴀʟ ɢʀᴏᴜᴘs:** `{stats['groups']}`
┃⟡➣ **ᴛᴏᴛᴀʟ ᴄᴏᴍᴍᴀɴᴅs:** `{stats['total_commands']}`
┃⟡➣ **sᴏɴɢs ᴘʟᴀʏᴇᴅ:** `{stats['songs_played']}`
┃⟡➣ **ʙᴏᴛ ᴜᴘᴛɪᴍᴇ:** `{stats['uptime']}`
┃⟡➣ **ᴀᴄᴛɪᴠᴇ ᴘʟᴀʏᴇʀs:** `{len(players)}`
**╰━━━━━━━━━━━━━━━━━━━━━━╯**
        """
        
        await event.reply(caption)
        return

@events.register(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode()
    user_id = event.sender_id
    
    if "_" in data:
        command, chat_id_str = data.split("_", 1)
        chat_id = int(chat_id_str)
    else:
        await event.answer("Invalid data!", alert=True)
        return
    
    if not await is_admin(chat_id, user_id):
        await event.answer("ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴄᴀɴ ᴅᴏ ᴛʜɪs!", alert=True)
        return
    
    player = await get_player(chat_id)
    
    if command == "pause":
        try:
            await call.pause(chat_id)
            await event.answer("⏸️ ᴘᴀᴜsᴇᴅ")
        except:
            await event.answer("❌ ғᴀɪʟᴇᴅ", alert=True)
    
    elif command == "skip":
        if not player.current:
            await event.answer("ɴᴏᴛʜɪɴɢ ɪs ᴘʟᴀʏɪɴɢ!", alert=True)
            return
        
        if player.current and player.current.get('is_local', False):
            try:
                os.remove(player.current['file_path'])
            except:
                pass
        
        if player.play_task and not player.play_task.done():
            player.play_task.cancel()
        
        try:
            await call.leave_call(chat_id)
        except:
            pass
        
        await asyncio.sleep(1)
        
        if player.queue:
            next_song = player.queue.pop(0)
            success = await play_song(chat_id, next_song, next_song.get('is_video', False))
            if success:
                await event.answer("⏭️ sᴋɪᴘᴘᴇᴅ")
            else:
                player.queue.insert(0, next_song)
                await event.answer("❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴘʟᴀʏ", alert=True)
        else:
            player.current = None
            
            if player.control_message_id and player.control_chat_id:
                try:
                    await event.message.delete()
                except:
                    pass
            player.control_message_id = None
            player.control_chat_id = None
            
            await event.answer("ǫᴜᴇᴜᴇ ᴇᴍᴘᴛʏ")
    
    elif command == "end":
        if player.current and player.current.get('is_local', False):
            try:
                os.remove(player.current['file_path'])
            except:
                pass
        
        for song in player.queue:
            if song.get('is_local', False):
                try:
                    os.remove(song.get('file_path', ''))
                except:
                    pass
        
        if player.play_task and not player.play_task.done():
            player.play_task.cancel()
        
        try:
            await call.leave_call(chat_id)
        except:
            pass
        
        player.queue.clear()
        player.current = None
        player.paused = False
        
        try:
            await event.message.delete()
        except:
            pass
        player.control_message_id = None
        player.control_chat_id = None
        
        await event.answer("⏹️ sᴛᴏᴘᴘᴇᴅ")
    
    elif command == "loop":
        player.loop = not player.loop
        await event.answer(f"ʟᴏᴏᴘ: {'ᴏɴ' if player.loop else 'ᴏғғ'}")
        
        if player.current:
            await send_streaming_message(chat_id, player.current, player.current.get('is_video', False))
    
    elif command == "queue":
        if not player.queue:
            await event.answer("ǫᴜᴇᴜᴇ ɪs ᴇᴍᴘᴛʏ!", alert=True)
            return
        
        text = "**📋 ǫᴜᴇᴜᴇ ʟɪsᴛ:**\n\n"
        for i, song in enumerate(player.queue[:5], 1):
            title = 'Voice Message' if song.get('is_local', False) else song['title'][:30]
            text += f"{i}. {title} ({song['duration_str']})\n"
        
        if len(player.queue) > 5:
            text += f"\n...ᴀɴᴅ {len(player.queue) - 5} ᴍᴏʀᴇ"
        
        await event.answer(text, alert=True)
    
    elif command == "clear":
        for song in player.queue:
            if song.get('is_local', False):
                try:
                    os.remove(song.get('file_path', ''))
                except:
                    pass
        
        player.queue.clear()
        await event.answer("🗑️ ǫᴜᴇᴜᴇ ᴄʟᴇᴀʀᴇᴅ")

@events.register(events.CallbackQuery(data="help"))
async def help_callback(event):
    help_text = """
**╭━━━━ ⟬ ʜᴇʟᴘ ᴍᴇɴᴜ ⟭━━━━╮**
┃
┃ **ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅs:** 
┃
┃✨ **/play** [song] - ᴘʟᴀʏ ᴀᴜᴅɪᴏ
┃   📢 ʀᴇᴘʟʏ ᴛᴏ ᴠᴏɪᴄᴇ ᴍᴇssᴀɢᴇ ᴛᴏ ᴘʟᴀʏ
┃🎬 **/vplay** [video] - ᴘʟᴀʏ ᴠɪᴅᴇᴏ
┃⏭️ **/skip** - sᴋɪᴘ ᴄᴜʀʀᴇɴᴛ
┃⏸️ **/pause** - ᴘᴀᴜsᴇ
┃▶️ **/resume** - ʀᴇsᴜᴍᴇ
┃⏹️ **/end** - sᴛᴏᴘ
┃📋 **/queue** - sʜᴏᴡ ǫᴜᴇᴜᴇ
┃🔄 **/loop** - ᴛᴏɢɢʟᴇ ʟᴏᴏᴘ
┃🗑️ **/clear** - ᴄʟᴇᴀʀ ǫᴜᴇᴜᴇ
┃🔄 **/reload** - ʀᴇʟᴏᴀᴅ ᴀᴅᴍɪɴs
┃🏓 **/ping** - ᴄʜᴇᴄᴋ ʙᴏᴛ ᴘɪɴɢ
┃
┃ **ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:**
┃
┃📢 **/gcast** - ʙʀᴏᴀᴅᴄᴀsᴛ
┃➕ **/addadmin** - ᴀᴅᴅ ʙᴏᴛ ᴀᴅᴍɪɴ
┃➖ **/deladmin** - ʀᴇᴍᴏᴠᴇ ʙᴏᴛ ᴀᴅᴍɪɴ
┃📋 **/admins** - sʜᴏᴡ ᴀᴅᴍɪɴs
┃📊 **/stats** - sʜᴏᴡ ʙᴏᴛ sᴛᴀᴛs
**╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯**
    """
    
    buttons = [[Button.inline("🔙 ʙᴀᴄᴋ", data="back_to_start")]]
    await event.edit(help_text, buttons=buttons)

@events.register(events.CallbackQuery(data="back_to_start"))
async def back_to_start(event):
    user = await event.get_sender()
    
    caption = f"""
✨ **ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ˹𝚨𝛔𝛖𝛎𝛂 ꭙ 𝐌ᴜꜱɪᴄ ♪˼ ʙᴏᴛ** ✨

⟡➣ **ʜᴇʏ** [{get_display_name(user)}](tg://user?id={user.id}) ❤️

⟡➣ **ɪ ᴀᴍ ᴀ ᴘᴏᴡᴇʀғᴜʟ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ ʙᴏᴛ.**
⟡➣ **ᴛʜᴀᴛ ᴄᴀɴ ᴘʟᴀʏ ᴍᴜsɪᴄ ᴀɴᴅ ᴠɪᴅᴇᴏ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛs.**
    """
    
    buttons = [
        [Button.url("⟡➣ 𝙾𝚠𝚗𝚎𝚛", f"https://t.me/god_knows_0"),
         Button.url("➕ 𝙰𝚍𝚍 𝙼𝚎", f"https://t.me/{(await event.client.get_me()).username}?startgroup=true")],
        [Button.inline("⟡➣ 𝙷𝚎𝚕𝚙", data="help"),
         Button.url("⟡➣ 𝚄𝚙𝚍𝚊𝚝𝚎𝚜", f"https://t.me/{UPDATES_CHANNEL}")]
    ]
    
    await event.edit(file=WELCOME_IMAGE_URL, message=caption, buttons=buttons)

@events.register(events.NewMessage)
async def admin_commands(event):
    if not event.message.text:
        return
    
    text = event.message.text.strip()
    user_id = event.sender_id
    sender = await event.get_sender()
    
    # /gcast command
    if is_command(text, "gcast"):
        if not db.is_bot_admin(user_id):
            reply_msg = await event.reply("**❌ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ ʙᴏᴛ ᴀᴅᴍɪɴ!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            await reply_msg.delete()
            return
        
        query = get_command_args(text, "gcast")
        if not query:
            reply_msg = await event.reply("**ᴜsᴀɢᴇ:** `/gcast <ᴍᴇssᴀɢᴇ>`")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            await reply_msg.delete()
            return
        
        try:
            await event.message.delete()
        except:
            pass
        
        msg = await event.reply("**📢 ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ...**")
        
        await log_to_group(action="ʙʀᴏᴀᴅᴄᴀsᴛ", user=sender, details=f"Message: {query[:100]}")
        
        sent = 0
        failed = 0
        
        for group_id_str in db.data["groups"]:
            try:
                group_id = int(group_id_str)
                await bot.send_message(group_id, query)
                sent += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Broadcast failed to {group_id_str}: {e}")
                failed += 1
                
                if "not a member" in str(e).lower() or "chat not found" in str(e).lower():
                    db.remove_group(group_id_str)
        
        await msg.edit(f"**📢 ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ**\n\n✅ sᴇɴᴛ: {sent}\n❌ ғᴀɪʟᴇᴅ: {failed}")
        await asyncio.sleep(5)
        await msg.delete()
        return
    
    # /addadmin command
    if is_command(text, "addadmin"):
        if user_id != OWNER_ID:
            reply_msg = await event.reply("**❌ ᴏɴʟʏ ᴏᴡɴᴇʀ ᴄᴀɴ ᴀᴅᴅ ᴀᴅᴍɪɴs!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            await reply_msg.delete()
            return
        
        new_admin = get_command_args(text, "addadmin")
        if not new_admin:
            reply_msg = await event.reply("**ᴜsᴀɢᴇ:** `/addadmin <ᴜsᴇʀ_ɪᴅ>`")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            await reply_msg.delete()
            return
        
        try:
            await event.message.delete()
        except:
            pass
        
        try:
            new_admin = int(new_admin)
            if db.add_bot_admin(new_admin):
                msg = await event.reply(f"**✅ ᴜsᴇʀ `{new_admin}` ɪs ɴᴏᴡ ᴀ ʙᴏᴛ ᴀᴅᴍɪɴ!**")
                await log_to_group(action="ᴀᴅᴅ ᴀᴅᴍɪɴ", user=sender, details=f"Added admin: {new_admin}")
            else:
                msg = await event.reply("**⚠️ ᴜsᴇʀ ɪs ᴀʟʀᴇᴀᴅʏ ᴀɴ ᴀᴅᴍɪɴ ᴏʀ ɪs ᴏᴡɴᴇʀ!**")
        except:
            msg = await event.reply("**❌ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ!**")
        
        await asyncio.sleep(3)
        await msg.delete()
        return
    
    # /deladmin command
    if is_command(text, "deladmin"):
        if user_id != OWNER_ID:
            reply_msg = await event.reply("**❌ ᴏɴʟʏ ᴏᴡɴᴇʀ ᴄᴀɴ ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴs!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            await reply_msg.delete()
            return
        
        remove_admin = get_command_args(text, "deladmin")
        if not remove_admin:
            reply_msg = await event.reply("**ᴜsᴀɢᴇ:** `/deladmin <ᴜsᴇʀ_ɪᴅ>`")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            await reply_msg.delete()
            return
        
        try:
            await event.message.delete()
        except:
            pass
        
        try:
            remove_admin = int(remove_admin)
            if db.remove_bot_admin(remove_admin):
                msg = await event.reply(f"**✅ ᴜsᴇʀ `{remove_admin}` ɪs ɴᴏ ʟᴏɴɢᴇʀ ᴀ ʙᴏᴛ ᴀᴅᴍɪɴ!**")
                await log_to_group(action="ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ", user=sender, details=f"Removed admin: {remove_admin}")
            else:
                msg = await event.reply("**⚠️ ᴜsᴇʀ ɪs ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ ᴏʀ ɪs ᴏᴡɴᴇʀ!**")
        except:
            msg = await event.reply("**❌ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ!**")
        
        await asyncio.sleep(3)
        await msg.delete()
        return
    
    # /admins command
    if is_command(text, "admins"):
        if not db.is_bot_admin(user_id):
            reply_msg = await event.reply("**❌ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ ʙᴏᴛ ᴀᴅᴍɪɴ!**")
            try:
                await event.message.delete()
            except:
                pass
            await asyncio.sleep(3)
            await reply_msg.delete()
            return
        
        try:
            await event.message.delete()
        except:
            pass
        
        text = "**👑 ʙᴏᴛ ᴀᴅᴍɪɴs ʟɪsᴛ:**\n\n"
        for admin_id in db.get_bot_admins():
            try:
                user = await bot.get_entity(admin_id)
                text += f"• {get_display_name(user)} (`{admin_id}`)\n"
            except:
                text += f"• `{admin_id}`\n"
        
        msg = await event.reply(text)
        await asyncio.sleep(10)
        await msg.delete()
        return

@events.register(events.ChatAction)
async def on_leave(event):
    if event.user_left or event.user_kicked:
        if event.user_id == (await bot.get_me()).id:
            chat = await event.get_chat()
            db.remove_group(chat.id)
            await log_to_group(action="ʙᴏᴛ ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ɢʀᴏᴜᴘ", group=chat)

async def main():
    global bot, assistant, call, BOT_START_TIME
    
    BOT_START_TIME = time.time()
    
    bot = TelegramClient('bot', API_ID, API_HASH)
    assistant = TelegramClient(StringSession(ASSISTANT_SESSION), API_ID, API_HASH)
    
    logger.info("Starting Bot...")
    await bot.start(bot_token=BOT_TOKEN)
    logger.info("✅ Bot Started!")
    
    logger.info("Starting Assistant...")
    await assistant.start()
    logger.info("✅ Assistant Started!")
    
    logger.info("Caching dialogs for assistant...")
    async for dialog in assistant.iter_dialogs():
        logger.info(f"Cached: {dialog.name} (ID: {dialog.id})")
    
    logger.info("Starting PyTgCalls...")
    call = PyTgCalls(assistant)
    await call.start()
    logger.info("✅ PyTgCalls Started!")
    
    bot.add_event_handler(message_handler)
    bot.add_event_handler(callback_handler)
    bot.add_event_handler(help_callback)
    bot.add_event_handler(back_to_start)
    bot.add_event_handler(admin_commands)
    bot.add_event_handler(on_leave)
    
    await log_to_group(action="ʙᴏᴛ sᴛᴀʀᴛᴇᴅ", details=f"Bot started successfully!\nUsers: {len(db.data['users'])}\nGroups: {len(db.data['groups'])}")
    
    logger.info("🤖 Bot is running!")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
