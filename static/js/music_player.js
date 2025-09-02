document.addEventListener("DOMContentLoaded", function () {
  const audio = document.getElementById("audio-element");
  const playBtn = document.getElementById("play-btn");
  const pauseBtn = document.getElementById("pause-btn");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const shuffleBtn = document.getElementById("shuffle-btn");

  let album = [];
  let currentIndex = 0;

  function loadTrack(index) {
    if (album.length === 0) return;
    audio.src = album[index];
    audio.play();
  }

  // Play buttons in the list
  document.querySelectorAll(".play-track").forEach((btn) => {
    btn.addEventListener("click", function () {
      const src = this.dataset.src;
      album = [src];
      currentIndex = 0;
      loadTrack(currentIndex);
    });
  });

  playBtn.addEventListener("click", () => audio.play());
  pauseBtn.addEventListener("click", () => audio.pause());
  nextBtn.addEventListener("click", () => {
    if (album.length === 0) return;
    currentIndex = (currentIndex + 1) % album.length;
    loadTrack(currentIndex);
  });
  prevBtn.addEventListener("click", () => {
    if (album.length === 0) return;
    currentIndex = (currentIndex - 1 + album.length) % album.length;
    loadTrack(currentIndex);
  });
  shuffleBtn.addEventListener("click", () => {
    if (album.length === 0) return;
    currentIndex = Math.floor(Math.random() * album.length);
    loadTrack(currentIndex);
  });
});
