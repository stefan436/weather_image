// ui.js

export function setupUI(appState, callbacks) {
  document.getElementById("start").addEventListener("click", () => {
    callbacks.onStart();
  });

  document.getElementById("playPause").addEventListener("click", () => {
    if (!appState.isPlaying) {
      appState.isPlaying = true;
      document.getElementById("playPause").textContent = "⏸️ Pause";
      appState.animationTimer = setInterval(() => {
        // Fixer Modulo 25 (Frames 0 bis 24)
        appState.currentFrame = (appState.currentFrame + 1) % 25;
        document.getElementById("frameSlider").value = appState.currentFrame;
        callbacks.onRenderFrame(appState.currentFrame);
      }, 1000); // 1000ms statt 500ms gibt dem Browser Zeit, das PNG zu laden
    } else {
      appState.isPlaying = false;
      document.getElementById("playPause").textContent = "▶️ Play";
      clearInterval(appState.animationTimer);
    }
  });

  document.getElementById("frameSlider").addEventListener("input", (e) => {
    const idx = parseInt(e.target.value);
    callbacks.onRenderFrame(idx);
  });
}