require("dotenv").config();
const TelegramBot = require("node-telegram-bot-api");
const { searchYouTube, getYouTubeStream } = require("./youtube");
const { searchSpotify, spotifyToYouTube } = require("./spotify");
const QueueManager = require("./queue");

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
if (!TOKEN) throw new Error("TELEGRAM_BOT_TOKEN missing in .env");

const bot = new TelegramBot(TOKEN, { polling: true });
const queues = new Map(); // chatId -> QueueManager

function getQueue(chatId) {
  if (!queues.has(chatId)) queues.set(chatId, new QueueManager());
  return queues.get(chatId);
}

// ─── /start ───────────────────────────────────────────────────────────────────
bot.onText(/\/start/, (msg) => {
  const name = msg.from.first_name || "বন্ধু";
  bot.sendMessage(
    msg.chat.id,
    `🎵 *হ্যালো ${name}! Music Bot-এ স্বাগতম!*\n\n` +
      `*Available Commands:*\n` +
      `▶️ /play \`<song name or URL>\` — গান বাজাও\n` +
      `🔍 /search \`<song name>\` — গান খোঁজো\n` +
      `⏹ /stop — বন্ধ করো\n` +
      `⏭ /skip — পরের গান\n` +
      `⏸ /pause — থামাও\n` +
      `▶️ /resume — আবার চালু করো\n` +
      `📋 /queue — queue দেখো\n` +
      `🎶 /nowplaying — এখন কোন গান চলছে\n` +
      `🗑 /clear — queue পরিষ্কার করো\n`,
    { parse_mode: "Markdown" }
  );
});

// ─── /play ────────────────────────────────────────────────────────────────────
bot.onText(/\/play (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const input = match[1].trim();
  const queue = getQueue(chatId);

  const loadingMsg = await bot.sendMessage(chatId, `🔍 খুঁজছি: *${input}*...`, {
    parse_mode: "Markdown",
  });

  try {
    let track;

    if (input.includes("spotify.com")) {
      // Spotify link
      const spotifyTrack = await spotifyToYouTube(input);
      if (!spotifyTrack) throw new Error("Spotify track খুঁজে পাওয়া যায়নি।");
      track = spotifyTrack;
    } else {
      // YouTube URL বা search query
      const results = await searchYouTube(input);
      if (!results || results.length === 0)
        throw new Error("কোনো গান খুঁজে পাওয়া যায়নি।");
      track = results[0];
    }

    queue.add(track);

    await bot.editMessageText(
      `✅ *Queue-এ যোগ হয়েছে:*\n🎵 ${track.title}\n⏱ ${track.duration}\n\n` +
        `Queue position: #${queue.length()}`,
      { chat_id: chatId, message_id: loadingMsg.message_id, parse_mode: "Markdown" }
    );

    // যদি এখন কিছু না বাজছে
    if (!queue.isPlaying()) {
      playNext(chatId);
    }
  } catch (err) {
    await bot.editMessageText(`❌ Error: ${err.message}`, {
      chat_id: chatId,
      message_id: loadingMsg.message_id,
    });
  }
});

// ─── /search ──────────────────────────────────────────────────────────────────
bot.onText(/\/search (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const query = match[1].trim();

  const loadingMsg = await bot.sendMessage(chatId, `🔍 *"${query}"* খুঁজছি...`, {
    parse_mode: "Markdown",
  });

  try {
    const results = await searchYouTube(query, 5);
    if (!results || results.length === 0)
      throw new Error("কোনো result পাওয়া যায়নি।");

    let text = `🎵 *"${query}" এর জন্য Results:*\n\n`;
    results.forEach((r, i) => {
      text += `${i + 1}. *${r.title}*\n   ⏱ ${r.duration} | 👁 ${r.views}\n   🔗 ${r.url}\n\n`;
    });
    text += `_/play <নাম বা URL> দিয়ে বাজাও_`;

    await bot.editMessageText(text, {
      chat_id: chatId,
      message_id: loadingMsg.message_id,
      parse_mode: "Markdown",
      disable_web_page_preview: true,
    });
  } catch (err) {
    await bot.editMessageText(`❌ Error: ${err.message}`, {
      chat_id: chatId,
      message_id: loadingMsg.message_id,
    });
  }
});

// ─── /nowplaying ──────────────────────────────────────────────────────────────
bot.onText(/\/nowplaying/, (msg) => {
  const chatId = msg.chat.id;
  const queue = getQueue(chatId);
  const current = queue.getCurrent();

  if (!current) {
    bot.sendMessage(chatId, "⏹ এখন কোনো গান বাজছে না।");
    return;
  }

  bot.sendMessage(
    chatId,
    `🎶 *এখন বাজছে:*\n\n🎵 ${current.title}\n⏱ ${current.duration}\n🔗 ${current.url}`,
    { parse_mode: "Markdown", disable_web_page_preview: true }
  );
});

// ─── /queue ───────────────────────────────────────────────────────────────────
bot.onText(/\/queue/, (msg) => {
  const chatId = msg.chat.id;
  const queue = getQueue(chatId);
  const list = queue.getAll();

  if (list.length === 0) {
    bot.sendMessage(chatId, "📋 Queue খালি।");
    return;
  }

  let text = `📋 *Queue (${list.length} টি গান):*\n\n`;
  list.forEach((track, i) => {
    const prefix = i === 0 ? "▶️" : `${i + 1}.`;
    text += `${prefix} *${track.title}* — ${track.duration}\n`;
  });

  bot.sendMessage(chatId, text, { parse_mode: "Markdown" });
});

// ─── /skip ────────────────────────────────────────────────────────────────────
bot.onText(/\/skip/, (msg) => {
  const chatId = msg.chat.id;
  const queue = getQueue(chatId);

  if (!queue.getCurrent()) {
    bot.sendMessage(chatId, "⏹ এখন কোনো গান বাজছে না।");
    return;
  }

  bot.sendMessage(chatId, "⏭ Skip করা হয়েছে।");
  queue.skip();
  playNext(chatId);
});

// ─── /stop ────────────────────────────────────────────────────────────────────
bot.onText(/\/stop/, (msg) => {
  const chatId = msg.chat.id;
  const queue = getQueue(chatId);
  queue.clear();
  bot.sendMessage(chatId, "⏹ বন্ধ করা হয়েছে এবং queue পরিষ্কার।");
});

// ─── /pause ───────────────────────────────────────────────────────────────────
bot.onText(/\/pause/, (msg) => {
  const chatId = msg.chat.id;
  const queue = getQueue(chatId);
  if (queue.pause()) {
    bot.sendMessage(chatId, "⏸ Paused।");
  } else {
    bot.sendMessage(chatId, "⚠️ এখন কিছু বাজছে না।");
  }
});

// ─── /resume ──────────────────────────────────────────────────────────────────
bot.onText(/\/resume/, (msg) => {
  const chatId = msg.chat.id;
  const queue = getQueue(chatId);
  if (queue.resume()) {
    bot.sendMessage(chatId, "▶️ Resume করা হয়েছে।");
  } else {
    bot.sendMessage(chatId, "⚠️ Pause করা নেই।");
  }
});

// ─── /clear ───────────────────────────────────────────────────────────────────
bot.onText(/\/clear/, (msg) => {
  const chatId = msg.chat.id;
  getQueue(chatId).clear();
  bot.sendMessage(chatId, "🗑 Queue পরিষ্কার করা হয়েছে।");
});

// ─── Play Next Helper ─────────────────────────────────────────────────────────
async function playNext(chatId) {
  const queue = getQueue(chatId);
  const track = queue.getCurrent();

  if (!track) {
    bot.sendMessage(chatId, "✅ Queue শেষ হয়ে গেছে।");
    return;
  }

  queue.setPlaying(true);

  try {
    const streamUrl = await getYouTubeStream(track.url);

    await bot.sendMessage(
      chatId,
      `▶️ *এখন বাজছে:*\n\n🎵 ${track.title}\n⏱ ${track.duration}\n\n` +
        `🔊 [Audio Stream Link](${streamUrl})\n\n` +
        `_পরের গানের জন্য /skip করো_`,
      { parse_mode: "Markdown", disable_web_page_preview: false }
    );

    // Auto-skip simulation (duration-based)
    const durationSec = parseDuration(track.duration);
    setTimeout(() => {
      if (queue.getCurrent() === track) {
        queue.next();
        playNext(chatId);
      }
    }, durationSec * 1000);
  } catch (err) {
    bot.sendMessage(chatId, `❌ Stream error: ${err.message}\n⏭ পরের গানে যাচ্ছি...`);
    queue.next();
    playNext(chatId);
  }
}

function parseDuration(duration) {
  if (!duration) return 240;
  const parts = duration.split(":").map(Number);
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return 240;
}

console.log("🎵 Telegram Music Bot চালু হয়েছে...");
