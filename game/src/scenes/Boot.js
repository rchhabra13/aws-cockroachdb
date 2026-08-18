import Api from "../services/Api";
import { SEED_NPCS, ROLE_COLOR, POSTS } from "../config";

// Character textures are generated at runtime; no image assets are loaded.
export class Boot extends Phaser.Scene {
  constructor() {
    super("Boot");
  }

  preload() {
    this.person(0x4da3ff, "player", "customer");
    Object.entries(ROLE_COLOR).forEach(([role, color]) => this.person(color, `npc-${role}`, role));
    this.shadow();
  }

  person(color, key, role) {
    const w = 36;
    const h = 50;
    const g = this.make.graphics({ x: 0, y: 0, add: false });
    g.fillStyle(color, 1);
    g.fillRoundedRect(6, 20, 24, 26, 8);
    g.fillStyle(0xf2d6b3, 1);
    g.fillCircle(18, 14, 10);
    g.fillStyle(color, 1);
    g.fillRoundedRect(8, 4, 20, 9, 5);

    if (role === "guard") {
      g.fillStyle(0x11151f, 1);
      g.fillRect(6, 11, 24, 4);
    } else if (role === "manager") {
      g.fillStyle(0xffd23f, 1);
      g.fillTriangle(18, 20, 14, 20, 18, 34);
      g.fillTriangle(18, 20, 22, 20, 18, 34);
    } else if (role === "loan_officer") {
      g.fillStyle(0x11151f, 1);
      g.fillRect(11, 13, 6, 3);
      g.fillRect(19, 13, 6, 3);
    } else if (role === "teller") {
      g.fillStyle(0xffffff, 1);
      g.fillCircle(12, 27, 2.5);
    } else if (role === "compliance") {
      g.fillStyle(0xf4f4f5, 1);
      g.fillRoundedRect(12, 24, 12, 15, 2);
      g.fillStyle(0x11151f, 1);
      g.fillRect(14, 27, 8, 1.5);
      g.fillRect(14, 30, 8, 1.5);
      g.fillRect(14, 33, 6, 1.5);
    } else if (role === "advisor") {
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
      await Api.ensurePlayer();
      const live = await Api.listNpcs();
      if (Array.isArray(live) && live.length) npcs = live;
    } catch (e) {
      console.warn("GET /npcs failed, using seed roster:", e.message);
    }
    // Ignore unsupported roles and place unconfigured characters along the lobby wall.
    let auto = 0;
    npcs = npcs
      .filter((n) => ROLE_COLOR[n.role])
      .map((n) => ({ ...n, post: POSTS[n.name] || { x: 120 + auto++ * 90, y: 700 } }));
    this.scene.start("Bank", { npcs });
  }
}
