import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio
import yt_dlp
from aiohttp import web

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
STRING_SESSION = os.environ.get("STRING_SESSION")

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
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

def fmt(seconds):
    if not seconds:
        return "N/A"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

async def play_next(chat_id):
    queue = get_queue(chat_id)
    if not queue:
        await bot.send_message(chat_id, "✅ Queue finished.")
        return
    track = queue[0]
    try:
        await calls.change_stream(
            chat_id,
            AudioPiped(track["stream_url"], HighQualityAudio())
        )
    except Exception:
        try:
            await calls.join_group_call(
                chat_id,
                AudioPiped(track["stream_url"], HighQualityAudio())
            )
        except Exception as e:
            await bot.send_message(chat_id, f"❌ Error: {e}")
            return
    await bot.send_message(
        chat_id,
        f"▶️ **Now Playing:**\n🎵 {track['title']}\n⏱ {fmt(track['duration'])}\n🔗 {track['url']}\n\n_/skip to skip_"
    )

@bot.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply(
        "🎵 **VC Music Bot**\n\n"
        "▶️ `/play <name/URL>` — Play\n"
        "🔍 `/search <name>` — Search\n"
        "⏭ `/skip` — Skip\n"
        "⏹ `/stop` — Stop\n"
        "⏸ `/pause` — Pause\n"
        "▶️ `/resume` — Resume\n"
        "📋 `/queue` — Queue\n"
        "🎶 `/nowplaying` — Now Playing\n"
        "🗑 `/clear` — Clear Queue\n"
    )

@bot.on_message(filters.command("play"))
async def play(_, m: Message):
    chat_id = m.chat.id
    if len(m.command) < 2:
        return await m.reply("❌ Usage: `/play <song name or URL>`")
    query = " ".join(m.command[1:])
    msg = await m.reply(f"🔍 Searching: **{query}**...")
    try:
        track = search_youtube(query)
    except Exception as e:
        return await msg.edit(f"❌ Error: {e}")
    queue = get_queue(chat_id)
    queue.append(track)
    if len(queue) == 1:
        await msg.edit(f"✅ **{track['title']}**\nStarting...")
        await play_next(chat_id)
    else:
        await msg.edit(f"✅ Added: **{track['title']}**\n📋 #{len(queue)}")

@bot.on_message(filters.command("search"))
async def search(_, m: Message):
    if len(m.command) < 2:
        return await m.reply("❌ Usage: `/search <name>`")
    query = " ".join(m.command[1:])
    msg = await m.reply(f"🔍 Searching: **{query}**...")
    try:
        ydl_opts = {"quiet": True, "no_warnings": True, "default_search": "ytsearch5", "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get("entries", [info])[:5]
        text = f"🔍 **Results for** `{query}`:\n\n"
        for i, e in enumerate(entries, 1):
            text += f"{i}. **{e.get('title','?')}** — {fmt(e.get('duration',0))}\n{e.get('webpage_url','')}\n\n"
        await msg.edit(text, disable_web_page_preview=True)
    except Exception as e:
        await msg.edit(f"❌ Error: {e}")

@bot.on_message(filters.command("skip"))
async def skip(_, m: Message):
    queue = get_queue(m.chat.id)
    if not queue:
        return await m.reply("⏹ Nothing playing.")
    queue.pop(0)
    await m.reply("⏭ Skipped!")
    await play_next(m.chat.id)

@bot.on_message(filters.command("stop"))
async def stop(_, m: Message):
    queues[m.chat.id] = []
    try:
        await calls.leave_group_call(m.chat.id)
    except Exception:
        pass
    await m.reply("⏹ Stopped.")

@bot.on_message(filters.command("pause"))
async def pause(_, m: Message):
    try:
        await calls.pause_stream(m.chat.id)
        await m.reply("⏸ Paused.")
    except Exception:
        await m.reply("⚠️ Nothing playing.")

@bot.on_message(filters.command("resume"))
async def resume(_, m: Message):
    try:
        await calls.resume_stream(m.chat.id)
        await m.reply("▶️ Resumed.")
    except Exception:
        await m.reply("⚠️ Nothing paused.")

@bot.on_message(filters.command("queue"))
async def queue_cmd(_, m: Message):
    queue = get_queue(m.chat.id)
    if not queue:
        return await m.reply("📋 Queue is empty.")
    text = f"📋 **Queue ({len(queue)}):**\n\n"
    for i, t in enumerate(queue):
        text += f"{'▶️' if i==0 else f'{i+1}.'} **{t['title']}** — {fmt(t['duration'])}\n"
    await m.reply(text)

@bot.on_message(filters.command("nowplaying"))
async def nowplaying(_, m: Message):
    queue = get_queue(m.chat.id)
    if not queue:
        return await m.reply("⏹ Nothing playing.")
    t = queue[0]
    await m.reply(f"🎶 **Now Playing:**\n🎵 {t['title']}\n⏱ {fmt(t['duration'])}\n🔗 {t['url']}", disable_web_page_preview=True)

@bot.on_message(filters.command("clear"))
async def clear(_, m: Message):
    queues[m.chat.id] = []
    await m.reply("🗑 Queue cleared.")

async def main():
    await bot.start()
    await user.start()
    await calls.start()
    print("🎵 VC Music Bot is running!")
    runner = web.AppRunner(web.Application())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    asyncio.run(main())
