const SpotifyWebApi = require("spotify-web-api-node");
const { searchYouTube } = require("./youtube");

const spotifyApi = new SpotifyWebApi({
  clientId: process.env.SPOTIFY_CLIENT_ID,
  clientSecret: process.env.SPOTIFY_CLIENT_SECRET,
});

let tokenExpiry = 0;

async function ensureToken() {
  if (Date.now() < tokenExpiry) return;
  const data = await spotifyApi.clientCredentialsGrant();
  spotifyApi.setAccessToken(data.body["access_token"]);
  tokenExpiry = Date.now() + data.body["expires_in"] * 1000 - 60000;
}

/**
 * Spotify link থেকে track info বের করে YouTube-এ খোঁজো
 */
async function spotifyToYouTube(spotifyUrl) {
  await ensureToken();

  let trackId;

  // URL থেকে track ID বের করো
  const match = spotifyUrl.match(/track\/([a-zA-Z0-9]+)/);
  if (!match) throw new Error("Valid Spotify track URL দাও।");
  trackId = match[1];

  const data = await spotifyApi.getTrack(trackId);
  const track = data.body;

  const artistName = track.artists.map((a) => a.name).join(", ");
  const trackName = track.name;
  const query = `${trackName} ${artistName}`;

  // YouTube-এ এই গান খোঁজো
  const results = await searchYouTube(query, 1);
  if (!results || results.length === 0)
    throw new Error("YouTube-এ গান খুঁজে পাওয়া যায়নি।");

  return {
    ...results[0],
    title: `${trackName} — ${artistName}`, // Spotify-র নাম ব্যবহার করো
  };
}

/**
 * Spotify-তে গান খোঁজো (future use)
 */
async function searchSpotify(query, limit = 5) {
  await ensureToken();
  const data = await spotifyApi.searchTracks(query, { limit });
  return data.body.tracks.items.map((t) => ({
    title: t.name,
    artist: t.artists.map((a) => a.name).join(", "),
    album: t.album.name,
    url: t.external_urls.spotify,
    preview: t.preview_url,
  }));
}

module.exports = { searchSpotify, spotifyToYouTube };
