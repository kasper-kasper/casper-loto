import Phaser from "phaser";
export class KhanBootScene extends Phaser.Scene {constructor(){super("KhanBoot");}create(){this.scene.start("KhanPreload");}}

