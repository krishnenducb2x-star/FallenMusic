const yts = require("yt-search");
const { exec } = require("child_process");
const { promisify } = require("util");
const execAsync = promisify(exec);

async function searchYouTube(query, limit = 1) {
  if (query.includes("youtube.com") || query.includes("youtu.be")) {
    const videoId = query.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)?.[1];
    const result = await yts({ videoId });
    if (result) {
      return [{ title: result.title, url: `https://www.youtube.com/watch?v=${result.videoId}`, duration: result.timestamp || "N/A", views: "N/A", thumbnail: result.thumbnail || "" }];
    }
  }
  const result = await yts(query);
  return result.videos.slice(0, limit).map(v => ({ title: v.title, url: v.url, duration: v.timestamp || "N/A", views: v.views ? formatViews(v.views) : "N/A", thumbnail: v.thumbnail || "" }));
}

async function getYouTubeStream(url) {
  try {
    const { stdout } = await execAsync(`yt-dlp -f "bestaudio[ext=m4a]/bestaudio/best" --get-url --no-warnings "${url}"`);
    const streamUrl = stdout.trim().split("\n")[0];
    if (!streamUrl) throw new Error("Stream URL পাওয়া যায়নি।");
    return streamUrl;
  } catch (err) {
    const videoId = url.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)?.[1];
    if (videoId) return `https://inv.nadeko.net/latest_version?id=${videoId}&itag=140`;
    throw new Error("Audio stream পাওয়া যায়নি: " + err.message);
  }
}

function formatViews(views) {
  const n = parseInt(views);
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

module.exports = { searchYouTube, getYouTubeStream };
