class QueueManager {
  constructor() {
    this.tracks = [];
    this.currentIndex = 0;
    this._isPlaying = false;
    this._isPaused = false;
  }

  add(track) {
    this.tracks.push(track);
  }

  getCurrent() {
    return this.tracks[this.currentIndex] || null;
  }

  getAll() {
    return this.tracks.slice(this.currentIndex);
  }

  next() {
    this.currentIndex++;
    this._isPlaying = false;
  }

  skip() {
    this.currentIndex++;
    this._isPlaying = false;
    this._isPaused = false;
  }

  length() {
    return this.tracks.length - this.currentIndex;
  }

  clear() {
    this.tracks = [];
    this.currentIndex = 0;
    this._isPlaying = false;
    this._isPaused = false;
  }

  isPlaying() {
    return this._isPlaying;
  }

  setPlaying(val) {
    this._isPlaying = val;
  }

  pause() {
    if (!this._isPlaying) return false;
    this._isPaused = true;
    this._isPlaying = false;
    return true;
  }

  resume() {
    if (!this._isPaused) return false;
    this._isPaused = false;
    this._isPlaying = true;
    return true;
  }
}

module.exports = QueueManager;
