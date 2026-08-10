import Api from "../services/Api";
import { SEED_NPCS, ROLE_COLOR, POSTS } from "../config";

// Generates every texture at runtime from a colour — no image assets ship with the game —
// then fetches the live NPC roster before handing off to the Bank scene.
export class Boot extends Phaser.Scene {
  constructor() {
    super("Boot");
  }

  preload() {
    this.person(0x4da3ff, "player", "customer");
    Object.entries(ROLE_COLOR).forEach(([role, color]) => this.person(color, `npc-${role}`, role));
    this.shadow();
  }

  // A little top-down figure: head + torso, plus a small per-role accessory so the four
  // staff roles read apart at a glance. Drawn once and baked into a texture.
  person(color, key, role) {
    const w = 36;
    const h = 50;
    const g = this.make.graphics({ x: 0, y: 0, add: false });
    // torso
    g.fillStyle(color, 1);
    g.fillRoundedRect(6, 20, 24, 26, 8);
    // head
    g.fillStyle(0xf2d6b3, 1);
    g.fillCircle(18, 14, 10);
    // hair / cap
    g.fillStyle(color, 1);
    g.fillRoundedRect(8, 4, 20, 9, 5);

    if (role === "guard") {
      // peaked cap brim
      g.fillStyle(0x11151f, 1);
      g.fillRect(6, 11, 24, 4);
    } else if (role === "manager") {
      // necktie
      g.fillStyle(0xffd23f, 1);
      g.fillTriangle(18, 20, 14, 20, 18, 34);
      g.fillTriangle(18, 20, 22, 20, 18, 34);
    } else if (role === "loan_officer") {
      // glasses
      g.fillStyle(0x11151f, 1);
      g.fillRect(11, 13, 6, 3);
      g.fillRect(19, 13, 6, 3);
    } else if (role === "teller") {
      // name-badge dot
      g.fillStyle(0xffffff, 1);
      g.fillCircle(12, 27, 2.5);
    } else if (role === "compliance") {
      // clipboard held to the chest
      g.fillStyle(0xf4f4f5, 1);
      g.fillRoundedRect(12, 24, 12, 15, 2);
      g.fillStyle(0x11151f, 1);
      g.fillRect(14, 27, 8, 1.5);
      g.fillRect(14, 30, 8, 1.5);
      g.fillRect(14, 33, 6, 1.5);
    } else if (role === "advisor") {
      // pocket square + bow tie
      g.fillStyle(0xffffff, 1);
      g.fillRect(22, 24, 4, 4);
      g.fillStyle(0x11151f, 1);
      g.fillTriangle(18, 21, 14, 19, 14, 23);
      g.fillTriangle(18, 21, 22, 19, 22, 23);
    }

    g.lineStyle(2, 0x000000, 0.25);
    g.strokeRoundedRect(6, 20, 24, 26, 8);
    g.generateTexture(key, w, h);
    g.destroy();
  }

  shadow() {
    const g = this.make.graphics({ x: 0, y: 0, add: false });
    g.fillStyle(0x000000, 0.28);
    g.fillEllipse(16, 6, 30, 12);
    g.generateTexture("shadow", 32, 12);
    g.destroy();
  }

  async create() {
    let npcs = SEED_NPCS;
    try {
      const live = await Api.listNpcs();
      if (Array.isArray(live) && live.length) npcs = live;
    } catch (e) {
      console.warn("GET /npcs failed, using seed roster:", e.message);
    }
    // Keep every NPC whose role we can draw; give each a post, auto-placing any extras
    // along the lobby wall so nothing lands on top of another.
    let auto = 0;
    npcs = npcs
      .filter((n) => ROLE_COLOR[n.role])
      .map((n) => ({ ...n, post: POSTS[n.name] || { x: 120 + auto++ * 90, y: 700 } }));
    this.scene.start("Bank", { npcs });
  }
}
