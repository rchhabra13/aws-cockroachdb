import { Boot } from "./scenes/Boot";
import { Bank } from "./scenes/Bank";
import Api from "./services/Api";
import { persistentSessionEnabled } from "./config";

const game = new Phaser.Game({
  type: Phaser.AUTO,
  width: 1024,
  height: 768,
  parent: "game-container",
  backgroundColor: "#0b0d12",
  pixelArt: false,
  physics: { default: "arcade", arcade: { gravity: { y: 0 } } },
  scene: [Boot, Bank],
  // Keep dialogue timers advancing while requestAnimationFrame is suspended.
  fps: { forceSetTimeOut: true },
});

if (process.env.NODE_ENV !== "production") window.__GAME__ = game;

// Ephemeral sessions are deleted during teardown; remembered sessions remain in CockroachDB.
window.addEventListener("pagehide", () => {
  if (!persistentSessionEnabled()) Api.endSession();
});

export default game;
