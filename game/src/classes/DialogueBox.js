// Display-only dialogue panel with clipped, scrollable reply text.
export default class DialogueBox {
  constructor(scene) {
    const w = scene.scale.width;
    const h = scene.scale.height;
    const boxH = 170;
    const pad = 24;
    const top = h - boxH - pad;

    const headerH = 80;
    const bottomPad = 14;
    this.contentX = pad + 18;
    this.contentY = top + headerH;
    this.contentW = w - pad * 2 - 36;
    this.contentH = boxH - headerH - bottomPad;

    this.g = scene.add.graphics().setScrollFactor(0).setDepth(40);
    this.g.fillStyle(0x000000, 0.8);
    this.g.fillRoundedRect(pad, top, w - pad * 2, boxH, 10);
    this.g.lineStyle(2, 0x6933ff, 1);
    this.g.strokeRoundedRect(pad, top, w - pad * 2, boxH, 10);

    this.you = scene.add
      .text(pad + 18, top + 14, "", { font: "14px monospace", color: "#8b93a7", wordWrap: { width: w - pad * 2 - 36 } })
      .setScrollFactor(0)
      .setDepth(41);

    this.speaker = scene.add
      .text(pad + 18, top + 58, "", { font: "bold 14px monospace", color: "#9d7bff" })
      .setScrollFactor(0)
      .setDepth(41);

    this.text = scene.add
      .text(this.contentX, this.contentY, "", {
        font: "16px monospace",
        color: "#e7e9ee",
        wordWrap: { width: this.contentW },
        lineSpacing: 4,
      })
      .setScrollFactor(0)
      .setDepth(41);

    const maskShape = scene.make.graphics({}, false);
    maskShape.fillStyle(0xffffff);
    maskShape.fillRect(this.contentX, this.contentY, this.contentW, this.contentH);
    this.text.setMask(maskShape.createGeometryMask());

    this.hint = scene.add
      .text(w - pad - 8, top + boxH - 8, "↕ scroll for more", { font: "11px monospace", color: "#6d7690" })
      .setOrigin(1, 1)
      .setScrollFactor(0)
      .setDepth(41)
      .setVisible(false);

    this.scrollOffset = 0;
    this.pinnedToBottom = true;

    scene.input.on("wheel", (pointer, _objs, _dx, dy) => {
      if (!this._visible) return;
      if (pointer.x < pad || pointer.x > w - pad || pointer.y < top || pointer.y > top + boxH) return;
      const maxScroll = Math.max(0, this.text.height - this.contentH);
      this.scrollOffset = Phaser.Math.Clamp(this.scrollOffset + dy * 0.4, 0, maxScroll);
      this.pinnedToBottom = this.scrollOffset >= maxScroll - 1;
      this.applyScroll(maxScroll);
    });

    this.hide();
  }

  applyScroll(maxScroll) {
    this.text.y = this.contentY - this.scrollOffset;
    this.hint.setVisible(this._visible && maxScroll > 0);
  }

  // Preserve manual scroll position while streaming unless the view is pinned to the end.
  refreshScroll() {
    const maxScroll = Math.max(0, this.text.height - this.contentH);
    this.scrollOffset = this.pinnedToBottom ? maxScroll : Math.min(this.scrollOffset, maxScroll);
    this.applyScroll(maxScroll);
  }

  setYou(text) {
    this.you.setText(text);
  }

  show(speaker, message) {
    this.speaker.setText(speaker);
    this.text.setText(message);
    this.scrollOffset = 0;
    this.pinnedToBottom = true;
    this._visible = true;
    [this.g, this.you, this.speaker, this.text].forEach((o) => o.setVisible(true));
    this.refreshScroll();
  }

  setReply(message) {
    this.text.setText(message);
    this.refreshScroll();
  }

  hide() {
    this._visible = false;
    [this.g, this.you, this.speaker, this.text, this.hint].forEach((o) => o.setVisible(false));
  }

  isVisible() {
    return this._visible;
  }
}
