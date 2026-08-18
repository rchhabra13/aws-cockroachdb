export default class Character {
  constructor(scene, { id, name, role, x, y, textureKey }) {
    this.scene = scene;
    this.id = id;
    this.name = name;
    this.role = role;

    this.shadow = scene.add.image(x, y + 20, "shadow").setDepth(4);
    this.sprite = scene.physics.add
      .sprite(x, y, textureKey)
      .setImmovable(true)
      .setDepth(5);
    this.sprite.body.setSize(30, 30).setOffset(3, 14);

    this.label = scene.add
      .text(x, y - 34, `${name}\n${role}`, {
        font: "12px monospace",
        color: "#ffffff",
        align: "center",
        backgroundColor: "rgba(0,0,0,0.55)",
        padding: { x: 5, y: 3 },
      })
      .setOrigin(0.5, 1)
      .setDepth(20);
  }

  distanceTo(player) {
    return Phaser.Math.Distance.Between(player.x, player.y, this.sprite.x, this.sprite.y);
  }

  isPlayerNearby(player, radius = 64) {
    return this.distanceTo(player) < radius;
  }

  facePlayer(player) {
    this.sprite.setFlipX(player.x < this.sprite.x);
  }
}
