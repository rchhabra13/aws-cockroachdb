import Api from "../services/Api";
import Character from "../classes/Character";
import DialogueBox from "../classes/DialogueBox";
import * as Inspector from "../ui/Inspector";

// The Meridian Street branch, drawn from rectangles: a lobby, a teller counter, a manager's
// office, a vault, a guard post. The player is a customer who walks up and talks; every reply
// comes from POST /dialogue and updates the memory inspector.
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
    this.physics.add.collider(this.player, this.walls);
    this.characters.forEach((c) => this.physics.add.collider(this.player, c.sprite));

    this.cursors = this.input.keyboard.createCursorKeys();
    this.wasd = this.input.keyboard.addKeys("W,A,S,D");
    // Interact on E, not Space: Space is a normal character the player needs to type into
    // the message box, and a captured Space key never reaches the DOM input. An event
    // listener rather than JustDown polling, so a fast tap between two update ticks
    // still opens the dialogue.
    this.input.keyboard.on("keydown-E", (event) => {
      if (this.inDialogue) return;
      const near = this.nearestNpc();
      if (near) {
        // The same keypress would otherwise insert an "e" into the freshly focused input.
        event.preventDefault();
        this.openDialogue(near);
      }
    });

    // Stop Phaser from calling preventDefault on the game keys. The scene still reads them
    // (movement is gated by inDialogue), but because they are no longer captured they
    // also reach the DOM message box, so the player can type freely while a dialogue is open.
    // This replaces toggling keyboard.enabled, which could strand the keyboard disabled if a
    // dialogue was left without pressing Escape.
    this.input.keyboard.removeCapture("SPACE,UP,DOWN,LEFT,RIGHT,W,A,S,D,E");

    this.prompt = this.add
      .text(0, 0, "▲ E", { font: "12px monospace", color: "#9d7bff",
        backgroundColor: "rgba(0,0,0,0.6)", padding: { x: 5, y: 2 } })
      .setOrigin(0.5, 1)
      .setDepth(25)
      .setVisible(false);

    this.dialogueBox = new DialogueBox(this);
    this.bindComposer();
  }

  // --- world drawing -------------------------------------------------------

  drawFloor() {
    const g = this.add.graphics().setDepth(0);
    const tile = 32;
    for (let y = 0; y < H; y += tile) {
      for (let x = 0; x < W; x += tile) {
        g.fillStyle((x / tile + y / tile) % 2 ? 0x1b2030 : 0x181c29, 1);
        g.fillRect(x, y, tile, tile);
      }
    }
  }

  // A solid, collidable block that is also drawn. label is optional floor text.
  block(x, y, w, h, color, label) {
    const r = this.add.rectangle(x, y, w, h, color).setDepth(2);
    this.walls.add(r);
    if (label) {
      this.add
        .text(x, y, label, { font: "12px monospace", color: "#c6ccdb" })
        .setOrigin(0.5)
        .setDepth(3);
    }
    return r;
  }

  drawFurniture() {
    const t = 12;
    // outer walls
    this.block(W / 2, t / 2, W, t, 0x2b3242);
    this.block(W / 2, H - t / 2, W, t, 0x2b3242);
    this.block(t / 2, H / 2, t, H, 0x2b3242);
    this.block(W - t / 2, H / 2, t, H, 0x2b3242);

    // teller counter — two windows, Marge and Omar stand behind it
    this.block(395, 360, 360, 26, 0x3a4256, "TELLERS");
    // manager office: corner walls plus a desk in front
    this.block(690, 120, 12, 210, 0x2b3242);
    this.block(840, 324, 300, 12, 0x2b3242);
    this.block(780, 272, 150, 22, 0x3a4256, "MANAGER");
    // loan desk, left side
    this.block(210, 488, 170, 22, 0x3a4256, "LOANS");
    // vault, bottom-left corner
    this.block(110, 675, 150, 80, 0x11151f, "VAULT");
    // security rail near the doors
    this.block(620, 604, 190, 14, 0x3a4256, "SECURITY");

    this.drawDecor();
  }

  // Non-colliding dressing: entrance mat and a couple of potted plants, so the lobby reads
  // as a room rather than a grid. Purely visual — not added to the walls group.
  drawDecor() {
    this.add.rectangle(620, 736, 140, 44, 0x232a3a).setDepth(1);
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
    plant(964, 700);
    plant(964, 60);
  }

  // --- dialogue ------------------------------------------------------------

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
    // Escape always leaves a dialogue, whatever holds focus, so the player can never get stuck.
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.inDialogue) this.closeDialogue();
    });
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

  // Animated "thinking" dots while Nova is generating, so a slow turn does not look frozen.
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

  // Reveal the reply a few characters at a time. Pressing Enter again finishes it instantly.
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

  // --- loop ----------------------------------------------------------------

  update() {
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
