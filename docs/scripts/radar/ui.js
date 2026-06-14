//ui.js

// --- Event Listeners ---
export function setupUI(appState, callbacks) {
  document.getElementById("start").addEventListener("click", () => {
    callbacks.onStart();
  });

  document.getElementById("playPause").addEventListener("click", () => {
    if (!appState.isPlaying) {
      appState.isPlaying = true;
      document.getElementById("playPause").textContent = "⏸️ Pause";
      appState.animationTimer = setInterval(() => {
        appState.currentFrame = (appState.currentFrame + 1) % appState.preRenderedFrames.length;
        callbacks.onRenderFrame(appState.currentFrame);
        document.getElementById("frameSlider").value = appState.currentFrame;
      }, 500);
    } else {
      appState.isPlaying = false;
      document.getElementById("playPause").textContent = "▶️ Play";
      clearInterval(appState.animationTimer);
    }
  });

  document.getElementById("frameSlider").addEventListener("input", (e) => {
    const idx = parseInt(e.target.value);
    appState.currentFrame = idx;
    callbacks.onRenderFrame(appState.currentFrame);
  });
}