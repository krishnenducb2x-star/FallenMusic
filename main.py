import asyncio
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
import yt_dlp
from aiohttp import web

logging.basicConfig(level=logging.INFO)

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
STRING_SESSION = os.environ.get("STRING_SESSION")

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)
calls = PyTgCalls(user)

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
        except Exception as e:
            await app.send_message(chat_id, f"❌ Error: {str(e)}")
            return
    await app.send_message(
        chat_id,
        f"▶️ **Now Playing:**\n\n🎵 {track['title']}\n⏱ {format_duration(track['duration'])}\n🔗 {track['url']}\n\n_Use /skip to skip_"
    )

@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply(
        "🎵 **Welcome to VC Music Bot!**\n\n"
        "▶️ `/play <song name or URL>` — Play\n"
        "🔍 `/search <song name>` — Search\n"
        "⏭ `/skip` — Skip\n"
        "⏹ `/stop` — Stop\n"
        "📋 `/queue` — Queue\n"
        "🎶 `/nowplaying` — Now Playing\n"
        "⏸ `/pause` — Pause\n"
        "▶️ `/resume` — Resume\n"
        "🗑 `/clear` — Clear Queue\n"
    )

@app.on_message(filters.command("play"))
async def play(_, message: Message):
    chat_id = message.chat.id
    if len(message.command) < 2:
        await message.reply("❌ Usage: `/play <song name or URL>`")
        return
    query = " ".join(message.command[1:])
    loading = await message.reply(f"🔍 Searching: **{query}**...")
    try:
        track = search_youtube(query)
    except Exception as e:
        await loading.edit(f"❌ Error: {str(e)}")
        return
    queue = get_queue(chat_id)
    queue.append(track)
    if len(queue) == 1:
        await loading.edit(f"✅ Added: **{track['title']}**\nStarting...")
        await play_next(chat_id)
    else:
        await loading.edit(f"✅ Added to queue: **{track['title']}**\n📋 Position: #{len(queue)}")

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

@app.on_message(filters.command("stop"))
async def stop(_, message: Message):
    chat_id = message.chat.id
    queues[chat_id] = []
    try:
        await calls.leave_group_call(chat_id)
    except Exception:
        pass
    await message.reply("⏹ Stopped.")

@app.on_message(filters.command("pause"))
async def pause(_, message: Message):
    try:
        await calls.pause_stream(message.chat.id)
        await message.reply("⏸ Paused.")
    except Exception:
        await message.reply("⚠️ Nothing is playing.")

@app.on_message(filters.command("resume"))
async def resume(_, message: Message):
    try:
        await calls.resume_stream(message.chat.id)
        await message.reply("▶️ Resumed.")
    except Exception:
        await message.reply("⚠️ Nothing is paused.")

@app.on_message(filters.command("queue"))
async def queue_cmd(_, message: Message):
    queue = get_queue(message.chat.id)
    if not queue:
        await message.reply("📋 Queue is empty.")
        return
    text = f"📋 **Queue ({len(queue)} songs):**\n\n"
    for i, t in enumerate(queue):
        prefix = "▶️" if i == 0 else f"{i+1}."
        text += f"{prefix} **{t['title']}** — {format_duration(t['duration'])}\n"
    await message.reply(text)

@app.on_message(filters.command("nowplaying"))
async def nowplaying(_, message: Message):
    queue = get_queue(message.chat.id)
    if not queue:
        await message.reply("⏹ Nothing is playing.")
        return
    t = queue[0]
    await message.reply(f"🎶 **Now Playing:**\n\n🎵 {t['title']}\n⏱ {format_duration(t['duration'])}\n🔗 {t['url']}", disable_web_page_preview=True)

@app.on_message(filters.command("clear"))
async def clear(_, message: Message):
    queues[message.chat.id] = []
    await message.reply("🗑 Queue cleared.")

@app.on_message(filters.command("search"))
async def search(_, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: `/search <song name>`")
        return
    query = " ".join(message.command[1:])
    loading = await message.reply(f"🔍 Searching: **{query}**...")
    try:
        ydl_opts = {"quiet": True, "no_warnings": True, "default_search": "ytsearch5", "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get("entries", [info])[:5]
        text = f"🔍 **Results for:** `{query}`\n\n"
        for i, e in enumerate(entries, 1):
            text += f"{i}. **{e.get('title','Unknown')}** — {format_duration(e.get('duration',0))}\n{e.get('webpage_url','')}\n\n"
        await loading.edit(text, disable_web_page_preview=True)
    except Exception as e:
        await loading.edit(f"❌ Error: {str(e)}")

async def main():
    await app.start()
    await user.start()
    await calls.start()
    print("🎵 VC Music Bot is running...")
    runner = web.AppRunner(web.Application())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    asyncio.run(main())
