import { Boot } from "./scenes/Boot";
import { Bank } from "./scenes/Bank";

const game = new Phaser.Game({
  type: Phaser.AUTO,
  width: 1024,
  height: 768,
  parent: "game-container",
  backgroundColor: "#0b0d12",
  pixelArt: false,
  physics: { default: "arcade", arcade: { gravity: { y: 0 } } },
  scene: [Boot, Bank],
});

if (process.env.NODE_ENV !== "production") window.__GAME__ = game;

export default game;
