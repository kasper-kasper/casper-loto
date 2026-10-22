import Phaser from "phaser";

export class GrobBootScene extends Phaser.Scene {
  constructor(){super("GrobBoot");}
  create(){this.scene.start("GrobPreload");}
}

