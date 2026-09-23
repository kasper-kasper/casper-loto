import Phaser from "phaser";
import cryptMatte from "../../assets/core/crypt-matte.webp";
import sarcophagusMachine from "../../assets/core/sarcophagus-machine-v2.webp";
import numberSeal from "../../assets/core/number-seal-v2.webp";
import quickFive from "../../assets/core/quick-five.webp";
import quickXxv from "../../assets/core/quick-xxv.webp";
import actionPlaque from "../../assets/core/action-plaque.webp";
import revealStele from "../../assets/live/reveal-stele.webp";

export class GrobPreloadScene extends Phaser.Scene {
  constructor(){super("GrobPreload");}
  preload(){
    const {width,height}=this.scale;
    const ring=this.add.graphics().lineStyle(2,0xb89a61,.8).strokeCircle(width/2,height/2,34);
    this.add.text(width/2,height/2+58,"КРИПТА ПРОСЫПАЕТСЯ",{fontFamily:"Georgia,serif",fontSize:"12px",color:"#d8c9aa",letterSpacing:3}).setOrigin(.5);
    this.tweens.add({targets:ring,angle:360,duration:1800,repeat:-1});
    this.load.image("grob-crypt-matte",cryptMatte);
    this.load.image("grob-sarcophagus-machine",sarcophagusMachine);
    this.load.image("grob-number-seal",numberSeal);
    this.load.image("grob-quick-five",quickFive);
    this.load.image("grob-quick-xxv",quickXxv);
    this.load.image("grob-action-plaque",actionPlaque);
    if(this.registry.get("grobMode")==="live")this.load.image("grob-reveal-stele",revealStele);
  }
  create(){if(this.registry.get("grobMode")==="live")this.scene.start("GrobLive");else{this.scene.start("GrobPlay");this.scene.launch("GrobOverlay");}}
}
