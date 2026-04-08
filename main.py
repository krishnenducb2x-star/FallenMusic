import asyncio
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from pytgcalls.exceptions import NoActiveGroupCall
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
STRING_SESSION = os.environ.get("STRING_SESSION")

# Clients
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)
calls = PyTgCalls(user)

# Queue storage
queues = {}

def get_queue(chat_id):
    if chat_id not in queues:
        queues[chat_id] = []
    return queues[chat_id]

def search_youtube(query):
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        return {
            "title": info.get("title", "Unknown"),
            "url": info.get("webpage_url", ""),
            "stream_url": info.get("url", ""),
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
        }

def format_duration(seconds):
    if not seconds:
        return "N/A"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

async def play_next(chat_id):
    queue = get_queue(chat_id)
    if not queue:
        await app.send_message(chat_id, "✅ Queue is empty. Playback finished.")
        return

    track = queue[0]
    try:
        await calls.change_stream(chat_id, AudioPiped(track["stream_url"]))
    except Exception:
        try:
            await calls.join_group_call(chat_id, AudioPiped(track["stream_url"]))
        except NoActiveGroupCall:
            await app.send_message(chat_id, "❌ No active voice chat found. Please start a voice chat first.")
            return
        except Exception as e:
            await app.send_message(chat_id, f"❌ Error: {str(e)}")
            return

    await app.send_message(
        chat_id,
        f"▶️ **Now Playing:**\n\n"
        f"🎵 {track['title']}\n"
        f"⏱ {format_duration(track['duration'])}\n"
        f"🔗 {track['url']}\n\n"
        f"_Use /skip to skip, /stop to stop_"
    )

# ── /start ──────────────────────────────────────────────────────────────────
@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply(
        "🎵 **Welcome to VC Music Bot!**\n\n"
        "**Commands:**\n"
        "▶️ `/play <song name or URL>` — Play a song\n"
        "🔍 `/search <song name>` — Search for a song\n"
        "⏭ `/skip` — Skip current song\n"
        "⏹ `/stop` — Stop and leave VC\n"
        "📋 `/queue` — View queue\n"
        "🎶 `/nowplaying` — Currently playing\n"
        "🗑 `/clear` — Clear queue\n"
        "🔊 `/volume <1-200>` — Set volume\n"
        "⏸ `/pause` — Pause\n"
        "▶️ `/resume` — Resume\n"
    )

# ── /play ───────────────────────────────────────────────────────────────────
@app.on_message(filters.command("play"))
async def play(_, message: Message):
    chat_id = message.chat.id
    if len(message.command) < 2:
        await message.reply("❌ Usage: `/play <song name or URL>`")
        return

    query = " ".join(message.command[1:])
    loading = await message.reply(f"🔍 Searching for: **{query}**...")

    try:
        track = search_youtube(query)
    except Exception as e:
        await loading.edit(f"❌ Error: {str(e)}")
        return

    queue = get_queue(chat_id)
    queue.append(track)

    if len(queue) == 1:
        await loading.edit(f"✅ Added to queue: **{track['title']}**\nStarting playback...")
        await play_next(chat_id)
    else:
        await loading.edit(
            f"✅ Added to queue: **{track['title']}**\n"
            f"⏱ {format_duration(track['duration'])}\n"
            f"📋 Queue position: #{len(queue)}"
        )

# ── /search ─────────────────────────────────────────────────────────────────
@app.on_message(filters.command("search"))
async def search(_, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: `/search <song name>`")
        return

    query = " ".join(message.command[1:])
    loading = await message.reply(f"🔍 Searching for: **{query}**...")

    try:
        ydl_opts = {"quiet": True, "no_warnings": True, "default_search": "ytsearch5", "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get("entries", [info])[:5]

        text = f"🔍 **Search results for:** `{query}`\n\n"
        for i, e in enumerate(entries, 1):
            text += f"{i}. **{e.get('title', 'Unknown')}**\n"
            text += f"   ⏱ {format_duration(e.get('duration', 0))} | 🔗 {e.get('webpage_url', '')}\n\n"
        text += "_Use /play <name or URL> to play_"

        await loading.edit(text, disable_web_page_preview=True)
    except Exception as e:
        await loading.edit(f"❌ Error: {str(e)}")

# ── /skip ───────────────────────────────────────────────────────────────────
@app.on_message(filters.command("skip"))
async def skip(_, message: Message):
    chat_id = message.chat.id
    queue = get_queue(chat_id)
    if not queue:
        await message.reply("⏹ Nothing is playing.")
        return
    queue.pop(0)
    await message.reply("⏭ Skipped!")
    await play_next(chat_id)

# ── /stop ───────────────────────────────────────────────────────────────────
@app.on_message(filters.command("stop"))
async def stop(_, message: Message):
    chat_id = message.chat.id
    queues[chat_id] = []
    try:
        await calls.leave_group_call(chat_id)
    except Exception:
        pass
    await message.reply("⏹ Stopped and left voice chat.")

# ── /pause ──────────────────────────────────────────────────────────────────
@app.on_message(filters.command("pause"))
async def pause(_, message: Message):
    chat_id = message.chat.id
    try:
        await calls.pause_stream(chat_id)
        await message.reply("⏸ Paused.")
    except Exception:
        await message.reply("⚠️ Nothing is playing.")

# ── /resume ─────────────────────────────────────────────────────────────────
@app.on_message(filters.command("resume"))
async def resume(_, message: Message):
    chat_id = message.chat.id
    try:
        await calls.resume_stream(chat_id)
        await message.reply("▶️ Resumed.")
    except Exception:
        await message.reply("⚠️ Nothing is paused.")

# ── /queue ──────────────────────────────────────────────────────────────────
@app.on_message(filters.command("queue"))
async def queue_cmd(_, message: Message):
    chat_id = message.chat.id
    queue = get_queue(chat_id)
    if not queue:
        await message.reply("📋 Queue is empty.")
        return
    text = f"📋 **Queue ({len(queue)} songs):**\n\n"
    for i, t in enumerate(queue):
        prefix = "▶️" if i == 0 else f"{i + 1}."
        text += f"{prefix} **{t['title']}** — {format_duration(t['duration'])}\n"
    await message.reply(text)

# ── /nowplaying ──────────────────────────────────────────────────────────────
@app.on_message(filters.command("nowplaying"))
async def nowplaying(_, message: Message):
    chat_id = message.chat.id
    queue = get_queue(chat_id)
    if not queue:
        await message.reply("⏹ Nothing is playing.")
        return
    t = queue[0]
    await message.reply(
        f"🎶 **Now Playing:**\n\n"
        f"🎵 {t['title']}\n"
        f"⏱ {format_duration(t['duration'])}\n"
        f"🔗 {t['url']}",
        disable_web_page_preview=True
    )

# ── /clear ──────────────────────────────────────────────────────────────────
@app.on_message(filters.command("clear"))
async def clear(_, message: Message):
    chat_id = message.chat.id
    queues[chat_id] = []
    await message.reply("🗑 Queue cleared.")

# ── /volume ──────────────────────────────────────────────────────────────────
@app.on_message(filters.command("volume"))
async def volume(_, message: Message):
    chat_id = message.chat.id
    if len(message.command) < 2:
        await message.reply("❌ Usage: `/volume <1-200>`")
        return
    try:
        vol = int(message.command[1])
        if not 1 <= vol <= 200:
            raise ValueError
        await calls.change_volume_call(chat_id, vol)
        await message.reply(f"🔊 Volume set to {vol}%")
    except ValueError:
        await message.reply("❌ Please enter a number between 1 and 200.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

# ── Main ─────────────────────────────────────────────────────────────────────
async def main():
    await app.start()
    await user.start()
    await calls.start()
    print("🎵 VC Music Bot is running...")

    # Keep alive HTTP server for Render
    from aiohttp import web
    async def handle(request):
        return web.Response(text="VC Music Bot is running!")
    server = web.Application()
    server.router.add_get("/", handle)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()

    await asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    asyncio.run(main())
