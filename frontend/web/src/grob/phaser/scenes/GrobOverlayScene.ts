import Phaser from "phaser";
import type { GrobBridge } from "../../bridge/GrobBridge";
import type { GrobSnapshot } from "../../bridge/contracts";

export class GrobOverlayScene extends Phaser.Scene {
  private bridge!:GrobBridge;private unsubscribe:()=>void=()=>{};private signature="";
  constructor(){super("GrobOverlay");}
  create(){this.bridge=this.registry.get("grobBridge") as GrobBridge;this.unsubscribe=this.bridge.subscribeSnapshot(s=>this.apply(s));this.scale.on("resize",()=>this.signature="");this.events.once(Phaser.Scenes.Events.SHUTDOWN,()=>this.unsubscribe());}
  private apply(s:GrobSnapshot){const signature=JSON.stringify([s.balance,s.lottery.jackpot,s.lottery.draw_number,s.muted,this.scale.width,this.scale.height]);if(signature===this.signature)return;this.signature=signature;this.children.removeAll(true);const w=this.scale.width,mobile=w<760;
    const back=this.add.container(mobile?34:54,mobile?34:48).setDepth(100);back.add([this.add.circle(0,0,22,0x17191b,.9).setStrokeStyle(2,0xa8874f),this.add.text(0,-1,"‹",{fontFamily:"Georgia",fontSize:"36px",color:"#dfcfad"}).setOrigin(.5)]);back.setSize(58,58).setInteractive({useHandCursor:true}).on("pointerdown",()=>this.bridge.emitIntent({type:"EXIT"}));
    const jackpotValue=`${s.lottery.jackpot.toLocaleString("ru-RU")} CAS`,jackpotGlow=this.add.text(w/2,mobile?25:30,jackpotValue,{fontFamily:"Georgia",fontSize:mobile?"19px":"26px",fontStyle:"bold",color:"#d28b39",stroke:"#d28b39",strokeThickness:8,letterSpacing:1}).setOrigin(.5).setAlpha(.14).setBlendMode(Phaser.BlendModes.ADD).setDepth(99);this.add.text(w/2,mobile?25:30,jackpotValue,{fontFamily:"Georgia",fontSize:mobile?"19px":"26px",fontStyle:"bold",color:"#ffe2a0",stroke:"#100d0b",strokeThickness:4,letterSpacing:1}).setOrigin(.5).setDepth(100);this.add.text(w/2,mobile?49:59,"ДЖЕКПОТ",{fontFamily:"Arial",fontSize:mobile?"10px":"11px",fontStyle:"bold",color:"#d7c7a5",stroke:"#0b0c0d",strokeThickness:3,letterSpacing:3}).setOrigin(.5).setDepth(100);if(!s.reducedMotion)this.tweens.add({targets:jackpotGlow,alpha:.30,scale:1.035,duration:1600,yoyo:true,repeat:-1,ease:"Sine.InOut"});
    this.add.text(w-(mobile?18:36),mobile?28:34,s.balance.toLocaleString("ru-RU")+" CAS",{fontFamily:"Georgia",fontSize:mobile?"12px":"16px",color:"#d8c9aa"}).setOrigin(1,.5).setDepth(100);
  }
}
