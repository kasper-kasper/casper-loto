import Phaser from "phaser";
import type { KhanBridge } from "../../bridge/KhanBridge";
import type { KhanSnapshot } from "../../bridge/contracts";

export class KhanOverlayScene extends Phaser.Scene {
  private bridge!:KhanBridge;
  private unsubscribe:()=>void=()=>{};
  private signature="";

  constructor(){super("KhanOverlay");}

  create(){this.bridge=this.registry.get("khanBridge") as KhanBridge;this.unsubscribe=this.bridge.subscribeSnapshot(snapshot=>this.draw(snapshot));this.scale.on("resize",()=>this.signature="");this.events.once(Phaser.Scenes.Events.SHUTDOWN,()=>this.unsubscribe());}

  private draw(snapshot:KhanSnapshot){
    const signature=JSON.stringify([snapshot.balance,snapshot.lottery.draw_number,this.scale.width,this.scale.height]);if(signature===this.signature)return;this.signature=signature;this.children.removeAll(true);
    const width=this.scale.width,mobile=width<760,logoX=mobile?93:132,logoY=mobile?33:39,logoW=mobile?108:150,logoH=mobile?36:50;
    const logoPlate=this.add.graphics().setDepth(100);logoPlate.fillStyle(0x061738,.88).lineStyle(1,0xd8a43b,.78).fillRoundedRect(logoX-logoW*.62,logoY-logoH*.53,logoW*1.24,logoH*1.06,14).strokeRoundedRect(logoX-logoW*.62,logoY-logoH*.53,logoW*1.24,logoH*1.06,14);logoPlate.lineStyle(1,0xffedb4,.18).strokeRoundedRect(logoX-logoW*.62+5,logoY-logoH*.53+5,logoW*1.24-10,logoH*1.06-10,10);
    this.add.image(logoX,logoY,"khan-logo").setDisplaySize(logoW,logoH).setDepth(101);
    const back=this.add.container(mobile?33:48,mobile?79:91).setDepth(101);back.add([this.add.circle(0,0,22,0x07183b,.96).setStrokeStyle(2,0xe9bd52),this.add.text(-1,-2,"‹",{fontFamily:"Georgia",fontSize:"35px",color:"#fff1bd"}).setOrigin(.5)]);back.setSize(56,56).setInteractive({useHandCursor:true}).on("pointerdown",()=>this.bridge.emitIntent({type:"EXIT"}));this.add.text(mobile?63:77,mobile?79:91,"НАЗАД",{fontFamily:"Arial",fontSize:"8px",fontStyle:"bold",color:"#dfc57f",stroke:"#07122d",strokeThickness:3,letterSpacing:2}).setOrigin(0,.5).setDepth(101);
    const panelW=mobile?142:166,panelH=mobile?43:48,panelX=width-(mobile?12:26),panelY=mobile?30:35,panel=this.add.graphics().setDepth(100);panel.fillStyle(0x061738,.93).lineStyle(1,0xe5b746,.90).fillRoundedRect(panelX-panelW,panelY-panelH/2,panelW,panelH,13).strokeRoundedRect(panelX-panelW,panelY-panelH/2,panelW,panelH,13);panel.lineStyle(1,0xffedb4,.16).strokeRoundedRect(panelX-panelW+5,panelY-panelH/2+5,panelW-10,panelH-10,9);
    this.add.text(panelX-panelW+14,panelY-9,"БАЛАНС",{fontFamily:"Arial",fontSize:"7px",fontStyle:"bold",color:"#9eb2dc",letterSpacing:1}).setOrigin(0,.5).setDepth(101);
    const balance=`${snapshot.balance.toLocaleString("ru-RU")} CAS`,fontSize=balance.length>16?10:mobile?11:12;this.add.text(panelX-12,panelY+7,balance,{fontFamily:"Arial",fontSize:`${fontSize}px`,fontStyle:"bold",color:"#fff0bd"}).setOrigin(1,.5).setDepth(101);
  }
}

