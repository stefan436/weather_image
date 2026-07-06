// ui.js

import { time_per_frame } from './config.js'

export function setupUI(appState, callbacks) {
//  document.getElementById("start").addEventListener("click", () => {
//    callbacks.onStart();
//  });

  document.getElementById("playPause").addEventListener("click", () => {
    const playBtn = document.getElementById("playPause");
    
    if (!appState.isPlaying) {
      appState.isPlaying = true;
      playBtn.textContent = "⏸️ Pause";
      
      appState.animationTimer = setInterval(() => {
        // Frame index hochzählen, bei Ende wieder auf 0
        appState.currentFrame = (appState.currentFrame + 1) % appState.frames.length;
        document.getElementById("frameSlider").value = appState.currentFrame;
        callbacks.onRenderFrame();
      }, time_per_frame);
      
    } else {
      appState.isPlaying = false;
      playBtn.textContent = "▶️ Play";
      clearInterval(appState.animationTimer);
    }
  });

  document.getElementById("frameSlider").addEventListener("input", (e) => {
    appState.currentFrame = parseInt(e.target.value, 10);
    callbacks.onRenderFrame();
  });
}