(() => {
  const player = document.getElementById('bidstream-tutorial');
  if (!player) return;
  const chapters = [...document.querySelectorAll('[data-tutorial-time]')];
  const status = document.getElementById('tutorial-status');
  chapters.forEach(button => button.addEventListener('click', () => {
    const seek = () => {
      player.currentTime = Number(button.dataset.tutorialTime);
      player.play().catch(() => {
        status.textContent = 'Chapter selected. Press Play in the video player to begin.';
      });
    };
    if (player.readyState >= 1) seek();
    else {
      player.addEventListener('loadedmetadata', seek, {once:true});
      player.load();
    }
    player.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  }));
  player.addEventListener('timeupdate', () => {
    const active = Math.min(19, Math.floor(player.currentTime / 30));
    chapters.forEach((button,index) => {
      if (index === active) button.setAttribute('aria-current','true');
      else button.removeAttribute('aria-current');
    });
  });
  player.addEventListener('error', () => {
    status.textContent = 'The video could not load. Use the Download video link or read the transcript below.';
  });
})();
