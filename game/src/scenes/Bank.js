import Api from "../services/Api";
import Character from "../classes/Character";
import DialogueBox from "../classes/DialogueBox";
import * as Inspector from "../ui/Inspector";
import { persistentSessionEnabled, SCENARIOS, setPersistentSession } from "../config";

const W = 1024;
const H = 768;
const SPEED = 200;

export class Bank extends Phaser.Scene {
  constructor() {
    super("Bank");
    this.inDialogue = false;
    this.activeNpc = null;
    this.pending = false;
  }

  create({ npcs }) {
    this.walls = this.physics.add.staticGroup();
    this.drawFloor();
    this.drawFurniture();

    this.characters = npcs.map((n) => {
      const c = new Character(this, {
        id: n.id,
        name: n.name,
        role: n.role,
        x: n.post.x,
        y: n.post.y,
        textureKey: `npc-${n.role}`,
      });
      this.physics.add.collider(c.sprite, this.walls);
      return c;
    });

    this.playerShadow = this.add.image(620, 700, "shadow").setDepth(4);
    this.player = this.physics.add.sprite(620, 690, "player").setDepth(5);
    this.player.body.setSize(30, 30).setOffset(3, 14);
    // Scripted straight-line walks temporarily disable wall collisions.
    this.playerWallsCollider = this.physics.add.collider(this.player, this.walls);
    this.characters.forEach((c) => this.physics.add.collider(this.player, c.sprite));

    this.cursors = this.input.keyboard.createCursorKeys();
    this.wasd = this.input.keyboard.addKeys("W,A,S,D");
    // E leaves Space available to the message input; an event avoids missing quick taps.
    this.input.keyboard.on("keydown-E", (event) => {
      if (this.inDialogue) return;
      const near = this.nearestNpc();
      if (near) {
        // Prevent the interaction key from entering the newly focused input.
        event.preventDefault();
        this.openDialogue(near);
      }
    });

    // Phaser may observe these keys, but must not block them from the DOM input.
    this.input.keyboard.removeCapture("SPACE,UP,DOWN,LEFT,RIGHT,W,A,S,D,E");

    this.prompt = this.add
      .text(0, 0, "▲ E", { font: "12px monospace", color: "#9d7bff",
        backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 5, y: 2 } })
      .setOrigin(0.5, 1)
      .setDepth(25)
      .setVisible(false);

    this.dialogueBox = new DialogueBox(this);
    this.bindComposer();
    this.bindResetButton();
    this.bindPersistentSession();
    this.bindScenarioButtons();
  }

  drawFloor() {
    const g = this.add.graphics().setDepth(0);
    const tile = 48;
    for (let y = 0; y < H; y += tile) {
      for (let x = 0; x < W; x += tile) {
        const alt = (x / tile + y / tile) % 2;
        g.fillStyle(alt ? 0x20242f : 0x1a1e27, 1);
        g.fillRect(x, y, tile, tile);
        g.fillStyle(0x2b3140, 0.25);
        g.fillRect(x, y, tile, 1);
        g.fillRect(x, y, 1, tile);
      }
    }
    g.fillStyle(0x24304a, 0.35);
    g.fillRect(540, 300, 160, H - 300);
  }

  block(x, y, w, h, color, label, labelColor = "#c6ccdb") {
    const r = this.add.rectangle(x, y, w, h, color).setDepth(2);
    this.walls.add(r);
    if (label) {
      this.add
        .text(x, y, label, { font: "bold 11px monospace", color: labelColor })
        .setOrigin(0.5)
        .setDepth(3);
    }
    return r;
  }

  sign(x, y, text, color = 0x9d7bff) {
    this.add.rectangle(x, y, text.length * 8 + 16, 18, 0x0d1017).setDepth(6)
      .setStrokeStyle(1, color, 0.5);
    this.add.text(x, y, text, { font: "bold 10px monospace", color: "#dfe3ec" })
      .setOrigin(0.5).setDepth(7);
  }

  drawFurniture() {
    const t = 12;
    this.block(W / 2, t / 2, W, t, 0x2b3242);
    this.block(W / 2, H - t / 2, W, t, 0x2b3242);
    this.block(t / 2, H / 2, t, H, 0x2b3242);
    this.block(W - t / 2, H / 2, t, H, 0x2b3242);

    this.block(400, 348, 360, 22, 0x6b5330, "TELLERS", "#f0e2c0");
    this.sign(400, 250, "TELLER  WINDOWS");

    this.block(720, 120, 12, 200, 0x2b3242);
    this.block(866, 314, 310, 12, 0x2b3242);
    this.block(812, 250, 150, 20, 0x6b5330, "MANAGER", "#f0e2c0");
    this.sign(812, 150, "BRANCH MANAGER");

    this.block(196, 484, 170, 20, 0x6b5330, "LOANS", "#f0e2c0");
    this.sign(196, 388, "LOAN  OFFICE");

    this.block(788, 440, 12, 150, 0x2b3242);
    this.block(840, 524, 150, 20, 0x14b8a6, "COMPLIANCE", "#eafffb");
    this.sign(858, 410, "COMPLIANCE");

    this.block(196, 664, 170, 20, 0xeab308, "WEALTH", "#3a2e05");
    this.sign(196, 560, "WEALTH  ADVISORY");

    this.block(96, 700, 150, 96, 0x11151f, "VAULT", "#8b93a7");
    this.add.circle(96, 700, 16, 0x2b3242).setDepth(3).setStrokeStyle(3, 0x4a5468);

    this.block(600, 636, 180, 14, 0x3a4256, "SECURITY");
    this.sign(600, 660, "SECURITY");

    this.drawDecor();
  }

  drawDecor() {
    const glass = this.add.graphics().setDepth(6);
    glass.fillStyle(0x9fd8ff, 0.14);
    glass.fillRect(408, 300, 4, 48);
    glass.fillRect(300, 300, 4, 48);
    glass.fillRect(516, 300, 4, 48);

    const atm = this.add.graphics().setDepth(2);
    atm.fillStyle(0x2d3446, 1);
    atm.fillRoundedRect(724, 700, 60, 56, 6);
    atm.fillStyle(0x35c48a, 0.85);
    atm.fillRect(736, 712, 36, 20);
    atm.fillStyle(0x11151f, 1);
    atm.fillRect(740, 738, 28, 6);
    this.add.text(754, 690, "ATM", { font: "bold 10px monospace", color: "#8b93a7" })
      .setOrigin(0.5).setDepth(3);

    const clock = this.add.graphics().setDepth(3);
    clock.fillStyle(0x0d1017, 1);
    clock.fillCircle(512, 40, 14);
    clock.lineStyle(2, 0x8b93a7, 1);
    clock.strokeCircle(512, 40, 14);
    clock.lineBetween(512, 40, 512, 32);
    clock.lineBetween(512, 40, 519, 43);

    this.add.rectangle(620, 748, 150, 34, 0x232a3a).setDepth(1)
      .setStrokeStyle(1, 0x3a4256);
    this.add.text(620, 748, "WELCOME", { font: "bold 9px monospace", color: "#5b6478" })
      .setOrigin(0.5).setDepth(2);

    const rope = this.add.graphics().setDepth(3);
    [460, 540, 620].forEach((x) => {
      rope.fillStyle(0x6b7488, 1);
      rope.fillCircle(x, 470, 4);
      rope.fillCircle(x, 540, 4);
    });
    rope.lineStyle(2, 0xd4af37, 0.6);
    rope.lineBetween(460, 470, 620, 470);
    rope.lineBetween(460, 540, 620, 540);

    const plant = (x, y) => {
      const g = this.add.graphics().setDepth(3);
      g.fillStyle(0x2a3550, 1);
      g.fillRoundedRect(x - 12, y - 6, 24, 16, 4);
      g.fillStyle(0x3f8f5c, 1);
      g.fillCircle(x, y - 10, 13);
      g.fillStyle(0x4fb56f, 1);
      g.fillCircle(x - 6, y - 14, 8);
      g.fillCircle(x + 7, y - 12, 7);
    };
    plant(60, 60);
    plant(964, 60);
    plant(964, 620);
  }

  bindComposer() {
    this.composerEl = document.getElementById("composer");
    this.msgEl = document.getElementById("msg");
    this.sendBtn = document.getElementById("send");

    this.sendBtn.addEventListener("click", () => this.sendMessage());
    this.msgEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        if (this.streamTimer && !this.msgEl.value.trim()) this.finishStream();
        else this.sendMessage();
      } else if (e.key === "Escape") this.closeDialogue();
    });
    // Escape must work even when the composer does not hold focus.
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.inDialogue) this.closeDialogue();
    });
  }

  // Inline confirmation works in hosts that suppress window.confirm().
  bindResetButton() {
    const btn = document.getElementById("reset-db");
    const label = btn.textContent;
    let armed = false;
    let armTimer = null;

    btn.addEventListener("click", async () => {
      if (!armed) {
        armed = true;
        btn.textContent = "Really clear?";
        armTimer = setTimeout(() => {
          armed = false;
          btn.textContent = label;
        }, 3000);
        return;
      }

      clearTimeout(armTimer);
      armed = false;
      btn.disabled = true;
      btn.textContent = "Clearing…";
      try {
        await Api.resetWorld();
        if (this.inDialogue) this.closeDialogue();
        Inspector.reset();
        btn.textContent = "Cleared";
      } catch (e) {
        btn.textContent = "Failed";
        console.error(e);
      } finally {
        setTimeout(() => {
          btn.textContent = label;
          btn.disabled = false;
        }, 1200);
      }
    });
  }

  bindPersistentSession() {
    const toggle = document.getElementById("remember-session");
    toggle.checked = persistentSessionEnabled();
    toggle.addEventListener("change", () => {
      if (!setPersistentSession(toggle.checked)) {
        toggle.checked = false;
        console.warn("Browser storage is unavailable; using an ephemeral session.");
      }
    });
  }

  bindScenarioButtons() {
    const bar = document.getElementById("scenario-bar");
    this.scenarioState = {};
    SCENARIOS.forEach((scenario, i) => {
      this.scenarioState[scenario.key] = 0;
      const btn = document.createElement("button");
      btn.className = "sc-btn";
      btn.id = `sc-${scenario.key}`;
      btn.title = scenario.title;
      btn.innerHTML = `<span class="num">${i + 1}</span>${scenario.label}`;
      btn.addEventListener("click", () => this.onScenarioClick(scenario, btn));
      bar.appendChild(btn);
    });
    this.bindModal();
  }

  bindModal() {
    this.modalEl = document.getElementById("modal");
    document.getElementById("modal-cancel").addEventListener("click", () => this.closeModal());
    this.modalEl.addEventListener("click", (e) => {
      if (e.target === this.modalEl) this.closeModal();
    });
    this.modalRunBtn = document.getElementById("modal-run");
  }

  onScenarioClick(scenario, btn) {
    if (this.pending || this.autoWalk) return;
    const step = this.scenarioState[scenario.key];
    if (step === 0 || step >= scenario.script.length) {
      this.scenarioState[scenario.key] = 0;
      this.openModal(scenario, btn);
      return;
    }
    this.advanceScenario(scenario, btn);
  }

  openModal(scenario, btn) {
    document.getElementById("modal-tag").textContent = scenario.tag;
    document.getElementById("modal-title").textContent = scenario.title;
    document.getElementById("modal-situation").textContent = scenario.situation;
    document.getElementById("modal-proves").textContent = scenario.proves;
    document.getElementById("modal-crdb").textContent = scenario.cockroach;
    document.getElementById("modal-watch").textContent = scenario.watch;
    // Cloning removes the previous scenario's click handler.
    const run = this.modalRunBtn.cloneNode(true);
    this.modalRunBtn.replaceWith(run);
    this.modalRunBtn = run;
    run.addEventListener("click", () => {
      this.closeModal();
      this.advanceScenario(scenario, btn);
    });
    this.modalEl.classList.add("on");
  }

  closeModal() {
    this.modalEl.classList.remove("on");
  }

  async advanceScenario(scenario, btn) {
    if (this.pending || this.autoWalk) return;
    const step = this.scenarioState[scenario.key];
    if (step >= scenario.script.length) return;

    const entry = scenario.script[step];
    const text = typeof entry === "string" ? entry : entry.text;
    const targetName = typeof entry === "string" ? scenario.target : entry.to;
    const target = this.characters.find((c) => c.name === targetName);
    if (!target) return;

    btn.disabled = true;
    if (!this.inDialogue || this.activeNpc !== target) {
      if (this.inDialogue) this.closeDialogue();
      btn.innerHTML = `<span class="num">→</span>walking to ${target.name.split(" ")[0]}…`;
      await this.walkTo(target);
      this.openDialogue(target);
    }

    this.msgEl.value = text;
    this.scenarioState[scenario.key] = step + 1;
    try {
      await this.sendMessage();
    } finally {
      btn.disabled = false;
      const done = this.scenarioState[scenario.key] >= scenario.script.length;
      const n = this.scenarioState[scenario.key];
      btn.innerHTML = done
        ? `<span class="num">↺</span>${scenario.label} · done`
        : `<span class="num">${n}/${scenario.script.length}</span>${scenario.label} · next`;
    }
  }

  // The deadline prevents scripted walks from hanging on scene geometry.
  walkTo(npc) {
    this.playerWallsCollider.active = false;
    return new Promise((resolve) => {
      this.autoWalk = {
        targetX: npc.sprite.x,
        targetY: npc.sprite.y + 54,
        deadline: this.time.now + 4000,
        resolve,
      };
    });
  }

  stepAutoWalk() {
    const { targetX, targetY, deadline, resolve } = this.autoWalk;
    const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, targetX, targetY);
    if (d < 6 || this.time.now > deadline) {
      this.player.setPosition(targetX, targetY);
      this.player.body.setVelocity(0);
      this.playerShadow.setPosition(targetX, targetY + 20);
      this.playerWallsCollider.active = true;
      this.autoWalk = null;
      resolve();
      return;
    }
    const angle = Phaser.Math.Angle.Between(this.player.x, this.player.y, targetX, targetY);
    this.player.body.setVelocity(Math.cos(angle) * SPEED, Math.sin(angle) * SPEED);
    this.player.setFlipX(Math.cos(angle) < 0);
    this.playerShadow.setPosition(this.player.x, this.player.y + 20);
  }

  openDialogue(npc) {
    this.inDialogue = true;
    this.activeNpc = npc;
    this.player.body.setVelocity(0);
    npc.facePlayer(this.player);

    Inspector.setNearby(npc.name, npc.role);
    Inspector.reset();
    this.dialogueBox.setYou("");
    this.dialogueBox.show(npc.name, `You approach ${npc.name}. Type below and hit Enter.`);

    this.composerEl.classList.add("on");
    this.msgEl.value = "";
    this.msgEl.focus();
  }

  async sendMessage() {
    if (this.pending || !this.activeNpc) return;
    const text = this.msgEl.value.trim();
    if (!text) return;

    const npc = this.activeNpc;
    this.pending = true;
    this.sendBtn.disabled = true;
    this.msgEl.value = "";
    this.dialogueBox.setYou(`You:  ${text}`);
    this.dialogueBox.show(npc.name, "");
    this.startThinking(npc.name);

    try {
      const resp = await Api.dialogue(npc.id, text);
      this.stopThinking();
      if (this.activeNpc !== npc) return; // player walked off mid-request
      Inspector.showTurn(resp);
      this.streamReply(npc.name, resp.reply);
    } catch (e) {
      this.stopThinking();
      this.dialogueBox.setReply(`(backend error: ${e.message})`);
    } finally {
      this.pending = false;
      this.sendBtn.disabled = false;
      this.msgEl.focus();
    }
  }

  startThinking(name) {
    let n = 0;
    this.dialogueBox.setReply(`${name} is thinking`);
    this.thinkTimer = this.time.addEvent({
      delay: 350,
      loop: true,
      callback: () => {
        n = (n + 1) % 4;
        this.dialogueBox.setReply(`${name} is thinking${".".repeat(n)}`);
      },
    });
  }

  stopThinking() {
    if (this.thinkTimer) {
      this.thinkTimer.remove();
      this.thinkTimer = null;
    }
  }

  streamReply(name, full) {
    if (this.streamTimer) this.streamTimer.remove();
    let i = 0;
    this.streamingFull = full;
    this.streamTimer = this.time.addEvent({
      delay: 12,
      loop: true,
      callback: () => {
        i += 2;
        this.dialogueBox.setReply(full.slice(0, i));
        if (i >= full.length) this.finishStream();
      },
    });
  }

  finishStream() {
    if (this.streamTimer) {
      this.streamTimer.remove();
      this.streamTimer = null;
    }
    if (this.streamingFull) this.dialogueBox.setReply(this.streamingFull);
  }

  closeDialogue() {
    this.inDialogue = false;
    this.activeNpc = null;
    this.stopThinking();
    this.finishStream();
    this.dialogueBox.hide();
    this.composerEl.classList.remove("on");
    this.msgEl.blur();
    Inspector.setNearby(null);
  }

  update() {
    if (this.autoWalk) {
      this.stepAutoWalk();
      return;
    }
    if (!this.inDialogue) {
      this.movePlayer();
      this.showPrompt(this.nearestNpc());
    }
  }

  movePlayer() {
    const b = this.player.body;
    b.setVelocity(0);
    const left = this.cursors.left.isDown || this.wasd.A.isDown;
    const right = this.cursors.right.isDown || this.wasd.D.isDown;
    const up = this.cursors.up.isDown || this.wasd.W.isDown;
    const down = this.cursors.down.isDown || this.wasd.S.isDown;

    if (left) b.setVelocityX(-SPEED);
    else if (right) b.setVelocityX(SPEED);
    if (up) b.setVelocityY(-SPEED);
    else if (down) b.setVelocityY(SPEED);
    b.velocity.normalize().scale(SPEED);
    if (left) this.player.setFlipX(true);
    if (right) this.player.setFlipX(false);
    this.playerShadow.setPosition(this.player.x, this.player.y + 20);
  }

  nearestNpc() {
    let best = null;
    let bestD = Infinity;
    for (const c of this.characters) {
      const d = c.distanceTo(this.player);
      if (d < 90 && d < bestD) {
        best = c;
        bestD = d;
      }
    }
    return best;
  }

  showPrompt(npc) {
    if (!npc) {
      this.prompt.setVisible(false);
      Inspector.setNearby(null);
      return;
    }
    this.prompt.setPosition(npc.sprite.x, npc.sprite.y - 78).setVisible(true);
    Inspector.setNearby(npc.name, npc.role);
  }
}
