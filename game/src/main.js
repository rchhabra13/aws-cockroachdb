import { Boot } from "./scenes/Boot";
import { Bank } from "./scenes/Bank";
import Api from "./services/Api";

const game = new Phaser.Game({
  type: Phaser.AUTO,
  width: 1024,
  height: 768,
  parent: "game-container",
  backgroundColor: "#0b0d12",
  pixelArt: false,
  physics: { default: "arcade", arcade: { gravity: { y: 0 } } },
  scene: [Boot, Bank],
  // requestAnimationFrame stalls completely in a backgrounded/hidden tab, which would
  // freeze the whole game (movement, dialogue timers, even pending scene transitions) the
  // moment a player alt-tabs mid-conversation. setTimeout keeps ticking (throttled, but
  // never fully stopped), so the game degrades gracefully instead of hard-freezing.
  fps: { forceSetTimeOut: true },
});

if (process.env.NODE_ENV !== "production") window.__GAME__ = game;

// Drop this session's collection when the tab goes away. pagehide fires on close, reload,
// and mobile background/swipe-away (unlike unload, which is unreliable), and endSession uses
// a keepalive fetch so the delete still lands mid-teardown. A session that never spoke wrote
// no memory rows, so this is a cheap no-op for those.
window.addEventListener("pagehide", () => Api.endSession());

export default game;
