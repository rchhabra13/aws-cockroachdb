// In-canvas panel that shows the exchange: the player's line on top, then the character's
// spoken reply below. Player input is typed in the DOM composer; this box is display-only.
export default class DialogueBox {
  constructor(scene) {
    const w = scene.scale.width;
    const h = scene.scale.height;
    const boxH = 170;
    const pad = 24;
    const top = h - boxH - pad;

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
      .text(pad + 18, top + 80, "", {
        font: "16px monospace",
        color: "#e7e9ee",
        wordWrap: { width: w - pad * 2 - 36 },
        lineSpacing: 4,
      })
      .setScrollFactor(0)
      .setDepth(41);

    this.hide();
  }

  setYou(text) {
    this.you.setText(text);
  }

  show(speaker, message) {
    this.speaker.setText(speaker);
    this.text.setText(message);
    this._visible = true;
    [this.g, this.you, this.speaker, this.text].forEach((o) => o.setVisible(true));
  }

  setReply(message) {
    this.text.setText(message);
  }

  hide() {
    this._visible = false;
    [this.g, this.you, this.speaker, this.text].forEach((o) => o.setVisible(false));
  }

  isVisible() {
    return this._visible;
  }
}
