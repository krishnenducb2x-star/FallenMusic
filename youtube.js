const yts = require("yt-search");
const ytdl = require("@distube/ytdl-core");

/**
 * YouTube-এ গান খোঁজো
 * @param {string} query - গানের নাম বা YouTube URL
 * @param {number} limit - কতটা result চাও
 */
async function searchYouTube(query, limit = 1) {
  // যদি YouTube URL হয়
  if (query.includes("youtube.com") || query.includes("youtu.be")) {
    const info = await ytdl.getBasicInfo(query);
    const details = info.videoDetails;
    return [
      {
        title: details.title,
        url: details.video_url,
        duration: formatSeconds(parseInt(details.lengthSeconds)),
        views: formatViews(details.viewCount),
        thumbnail: details.thumbnails?.[0]?.url || "",
      },
    ];
  }

  // সাধারণ search
  const result = await yts(query);
  const videos = result.videos.slice(0, limit);

  return videos.map((v) => ({
    title: v.title,
    url: v.url,
    duration: v.timestamp || "N/A",
    views: v.views ? formatViews(v.views) : "N/A",
    thumbnail: v.thumbnail || "",
  }));
}

/**
 * YouTube audio stream URL বের করো
 * @param {string} url - YouTube URL
 */
async function getYouTubeStream(url) {
  const info = await ytdl.getInfo(url);

  // সবচেয়ে ভালো audio format বেছে নাও
  const format = ytdl.chooseFormat(info.formats, {
    quality: "highestaudio",
    filter: "audioonly",
  });

  if (!format) throw new Error("Audio format পাওয়া যায়নি।");
  return format.url;
}

function formatSeconds(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${pad(m)}:${pad(s)}`;
  return `${m}:${pad(s)}`;
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function formatViews(views) {
  const n = parseInt(views);
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

module.exports = { searchYouTube, getYouTubeStream };
