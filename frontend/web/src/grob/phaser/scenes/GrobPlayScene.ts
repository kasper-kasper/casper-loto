import Phaser from "phaser";
import type { GrobBridge } from "../../bridge/GrobBridge";
import type { GrobSnapshot, QuickQuantity } from "../../bridge/contracts";
import { computeGrobLayout } from "../layout/GrobLayout";

const bone=0xd8c9aa,brass=0xa8874f;
const money=(value:number)=>`${value.toLocaleString("ru-RU")} CAS`;

export class GrobPlayScene extends Phaser.Scene {
  private bridge!:GrobBridge; private snapshot:GrobSnapshot|null=null; private signature=""; private unsubscribe:()=>void=()=>{};
  private ambient:Phaser.GameObjects.Container|null=null; private focusIndex=0; private newlySelected:number|null=null; private newlyDeselected:{value:number;slot:number}|null=null;
  private pointerX=0;private pointerY=0;
  constructor(){super("GrobPlay");}
  create(){
    this.bridge=this.registry.get("grobBridge") as GrobBridge;
    this.unsubscribe=this.bridge.subscribeSnapshot(snapshot=>this.apply(snapshot));
    this.scale.on("resize",this.redraw,this);
    this.input.keyboard?.on("keydown-TAB",(event:KeyboardEvent)=>{event.preventDefault();this.focusIndex=(this.focusIndex+(event.shiftKey?-1:1)+20)%20;this.redraw();});
    this.input.keyboard?.on("keydown-ENTER",()=>this.activateFocus());
    this.input.keyboard?.on("keydown-SPACE",(event:KeyboardEvent)=>{event.preventDefault();this.activateFocus();});
    this.input.on("pointermove",(pointer:Phaser.Input.Pointer)=>{this.pointerX=(pointer.x/Math.max(1,this.scale.width)-.5)*8;this.pointerY=(pointer.y/Math.max(1,this.scale.height)-.5)*5;});
    this.events.once(Phaser.Scenes.Events.SHUTDOWN,()=>{this.unsubscribe();this.scale.off("resize",this.redraw,this);});
  }
  private activateFocus(){if(this.focusIndex<16)this.bridge.emitIntent({type:"TOGGLE_NUMBER",value:this.focusIndex+1});else if(this.focusIndex===16)this.bridge.emitIntent({type:"BUY_MANUAL"});else this.bridge.emitIntent({type:"BUY_QUICK",quantity:([1,5,25] as QuickQuantity[])[this.focusIndex-17]});}
  private apply(snapshot:GrobSnapshot){
    const before=this.snapshot?.selectedNumbers??[];
    this.newlySelected=snapshot.selectedNumbers.find(value=>!before.includes(value))??null;
    const removed=before.find(value=>!snapshot.selectedNumbers.includes(value));this.newlyDeselected=removed==null?null:{value:removed,slot:before.indexOf(removed)};
    this.snapshot=snapshot;
    const sig=JSON.stringify([snapshot.phase,snapshot.balance,snapshot.selectedNumbers,snapshot.purchase.status,snapshot.purchase.message,snapshot.lottery.purchase_available,snapshot.lottery.draw_number,snapshot.live.resultKind]);
    if(sig!==this.signature){this.signature=sig;this.redraw();}
    this.scene.setVisible(true);
  }
  update(){if(this.snapshot?.reducedMotion)return;const camera=this.cameras.main;camera.scrollX=Phaser.Math.Linear(camera.scrollX,this.pointerX,.035);camera.scrollY=Phaser.Math.Linear(camera.scrollY,this.pointerY,.035);}
  private redraw(){
    const s=this.snapshot;if(!s)return;
    this.children.removeAll(true);this.tweens.killAll();
    const l=computeGrobLayout(this.scale.width,this.scale.height);
    const bg=this.add.image(l.centerX,l.height/2,"grob-crypt-matte");bg.setScale(Math.max(l.width/bg.width,l.height/bg.height)).setDepth(-20);
    this.add.rectangle(l.centerX,l.height/2,l.width,l.height,0x05070a,.22).setDepth(-19);
    const world=this.add.container(0,0);this.ambient=world;
    const rose=this.add.graphics().lineStyle(1,brass,.28).strokeCircle(l.centerX,l.height*.18,Math.min(75,l.width*.1));
    for(let i=0;i<8;i++){const a=i*Math.PI/4;rose.lineBetween(l.centerX+Math.cos(a)*18,l.height*.18+Math.sin(a)*18,l.centerX+Math.cos(a)*Math.min(75,l.width*.1),l.height*.18+Math.sin(a)*Math.min(75,l.width*.1));}
    world.add(rose);
    const mistBack=this.add.ellipse(l.centerX,l.height*.59,l.width*.82,l.height*.12,0x6f7881,.035).setBlendMode(Phaser.BlendModes.ADD).setDepth(-8);world.add(mistBack);
    const mistFront=this.add.ellipse(l.centerX,l.height*.75,l.width*.96,l.height*.10,0x9aa0a4,.025).setBlendMode(Phaser.BlendModes.ADD).setDepth(9);world.add(mistFront);
    if(!s.reducedMotion){this.tweens.add({targets:mistBack,x:l.centerX+18,alpha:{from:.025,to:.055},duration:9000,yoyo:true,repeat:-1,ease:"Sine.InOut"});this.tweens.add({targets:mistFront,x:l.centerX-22,alpha:{from:.015,to:.04},duration:12000,yoyo:true,repeat:-1,ease:"Sine.InOut"});}
    if(!s.reducedMotion){for(let i=0;i<(l.mode==="mobile"?14:26);i++){const dot=this.add.circle((i*83)%l.width,(i*137)%l.height,1+(i%3),bone,.10+(i%4)*.035);world.add(dot);this.tweens.add({targets:dot,y:dot.y-45-(i%7)*9,x:dot.x+(i%2?12:-12),alpha:{from:dot.alpha,to:.02},duration:9000+(i%7)*1300,yoyo:true,repeat:-1,delay:i*180});}}
    this.drawSarcophagus(l,s);
    l.sealPositions.forEach((p,index)=>this.drawSeal(index+1,p.x,p.y,p.scale,s.selectedNumbers.includes(index+1),s));
    this.drawRail(l,s);
    this.newlySelected=null;this.newlyDeselected=null;
  }
  private drawSarcophagus(l:ReturnType<typeof computeGrobLayout>,s:GrobSnapshot){
    const x=l.centerX,y=l.sarcophagusY+(l.mode==="mobile"?4:10),displayWidth=Math.min(l.mode==="mobile"?l.width*.78:l.width*.68,720);
    const contactShadow=this.add.ellipse(x,y+displayWidth/1.5*.43,displayWidth*.78,displayWidth/1.5*.14,0x000000,.68).setDepth(2);this.add.ellipse(x,y+displayWidth/1.5*.425,displayWidth*.48,displayWidth/1.5*.055,0x511821,.12).setBlendMode(Phaser.BlendModes.ADD).setDepth(2);const machine=this.add.image(x,y,"grob-sarcophagus-machine").setDisplaySize(displayWidth,displayWidth/1.5).setDepth(3);void contactShadow;
    if(s.selectedNumbers.length===3&&!s.reducedMotion)this.tweens.add({targets:machine,scaleX:machine.scaleX*1.008,scaleY:machine.scaleY*1.008,duration:650,yoyo:true,repeat:-1,ease:"Sine.InOut"});
    const displayHeight=machine.displayHeight;
    const slots=[{x:x-displayWidth*.196,y:y-displayHeight*.186},{x:x+displayWidth*.20,y:y-displayHeight*.186},{x,y:y-displayHeight*.38}],purchasePoint={x,y:y-displayHeight*.25},canBuy=s.selectedNumbers.length===3&&s.salesOpen&&s.purchase.status!=="pending";
    this.drawEmberLinks(slots.slice(0,s.selectedNumbers.length),purchasePoint,s.selectedNumbers.length===3,s.reducedMotion);
    slots.forEach((slot,index)=>{const value=s.selectedNumbers[index];if(value==null)return;const insetY=slot.y+displayHeight*.012,seal=this.add.container(slot.x,insetY).setScale(.94).setDepth(7);const sprite=this.add.image(0,0,"grob-number-seal").setCrop(300,300,680,680).setDisplaySize(displayWidth*.09,displayWidth*.09);const label=this.add.text(0,0,String(value).padStart(2,"0"),{fontFamily:"Georgia,serif",fontSize:`${Math.max(23,displayWidth*.05)}px`,fontStyle:"bold",color:"#fff0c8",stroke:"#120d0b",strokeThickness:5}).setOrigin(.5);seal.add([sprite,label]);if(value===this.newlySelected&&!s.reducedMotion){const source=l.sealPositions[value-1],landingY=slot.y-displayHeight*.025,curve=new Phaser.Curves.QuadraticBezier(new Phaser.Math.Vector2(source.x,source.y),new Phaser.Math.Vector2((source.x+slot.x)/2,Math.min(source.y,slot.y)-displayHeight*.24),new Phaser.Math.Vector2(slot.x,landingY)),point=new Phaser.Math.Vector2(),progress={value:0};seal.setPosition(source.x,source.y).setScale(.78);this.tweens.add({targets:progress,value:1,duration:390,ease:"Cubic.Out",onUpdate:()=>{curve.getPoint(progress.value,point);seal.setPosition(point.x,point.y);seal.setScale(.78+.30*progress.value);},onComplete:()=>{this.tweens.add({targets:seal,y:insetY,scale:.94,duration:150,ease:"Cubic.In"});this.cameras.main.shake(70,.0015);this.burstDust(slot.x,insetY,displayWidth*.04);}});}if(s.purchase.status==="success"&&!s.reducedMotion)this.tweens.add({targets:seal,x:x+displayWidth*.39,y:y+displayHeight*.16,scale:.38,alpha:0,duration:620,delay:index*55,ease:"Cubic.In"});});
    const purchaseSeal=this.add.container(purchasePoint.x,purchasePoint.y).setDepth(9),sealRadius=displayWidth*.043,sealGlow=this.add.circle(0,0,sealRadius*(canBuy?1.7:1.15),canBuy?0xff5528:0x5b1615,canBuy?.34:.08).setBlendMode(Phaser.BlendModes.ADD),sealFace=this.add.circle(0,0,sealRadius,canBuy?0xb52920:0x5f2422,canBuy?.46:.18).setStrokeStyle(Math.max(2,displayWidth*.004),canBuy?0xffb45e:0x783c30,canBuy?1:.55),sealCore=this.add.circle(0,0,sealRadius*.42,canBuy?0xff6a32:0x6f2724,canBuy?.42:.12).setBlendMode(Phaser.BlendModes.ADD);purchaseSeal.add([sealGlow,sealFace,sealCore]).setSize(sealRadius*2.7,sealRadius*2.7);
    const purchaseInput=this.add.circle(purchasePoint.x,purchasePoint.y,sealRadius*1.7,0xffffff,.001).setDepth(20);if(canBuy)purchaseInput.setInteractive({useHandCursor:true}).on("pointerdown",()=>{if(!s.reducedMotion)this.tweens.add({targets:purchaseSeal,scale:.84,duration:75,yoyo:true});this.bridge.emitIntent({type:"BUY_MANUAL"});});
    if(this.focusIndex===16)purchaseSeal.add(this.add.circle(0,0,sealRadius*1.45,0x000000,0).setStrokeStyle(3,bone,1));
    if(canBuy&&!s.reducedMotion){this.tweens.add({targets:sealGlow,scale:1.38,alpha:.12,duration:540,yoyo:true,repeat:-1,ease:"Sine.InOut"});this.tweens.add({targets:sealCore,alpha:.75,duration:330,yoyo:true,repeat:-1,ease:"Sine.InOut"});}
    if(s.purchase.status==="success"&&!s.reducedMotion){this.tweens.add({targets:machine,y:y+5,duration:120,yoyo:true,repeat:1});const ring=this.add.circle(x,y-displayHeight*.12,displayWidth*.08,0xd5b36c,.18).setDepth(6).setBlendMode(Phaser.BlendModes.ADD);this.tweens.add({targets:ring,scale:4.2,alpha:0,duration:700,ease:"Cubic.Out"});this.burstDust(x,y-displayHeight*.05,displayWidth*.18);}
    this.add.image(x,y+displayHeight*.045,"grob-action-plaque").setDisplaySize(displayWidth*.50,displayHeight*.082).setDepth(7);this.add.text(x,y+displayHeight*.045,canBuy?`НАЖМИТЕ КРАСНУЮ ПЕЧАТЬ · ${money(s.lottery.ticket_price??0)}`:`ВЫБЕРИТЕ 3 ПЕЧАТИ · ${money(s.lottery.ticket_price??0)}`,{fontFamily:"Georgia,serif",fontSize:`${l.mode==="mobile"?9:12}px`,fontStyle:"bold",color:"#2a1609",stroke:"#e1b967",strokeThickness:1,letterSpacing:1}).setOrigin(.5).setDepth(8);
  }
  private drawSeal(value:number,x:number,y:number,scale:number,selected:boolean,s:GrobSnapshot){
    const size=(computeGrobLayout(this.scale.width,this.scale.height).mode==="mobile"?64:76)*scale,c=this.add.container(x,y).setDepth(2);
    const sprite=this.add.image(0,0,"grob-number-seal").setDisplaySize(size,size).setTint(selected?0x46383a:0xffffff).setAlpha(selected ? .44 : 1);const label=this.add.text(0,-1,selected?"":String(value).padStart(2,"0"),{fontFamily:"Georgia,serif",fontSize:`${Math.max(22,size*.42)}px`,fontStyle:"bold",color:"#fff0cc",stroke:"#120d0b",strokeThickness:5}).setOrigin(.5);c.add([sprite,label]);
    if(this.focusIndex===value-1)c.add(this.add.circle(0,0,size*.34,0x000000,0).setStrokeStyle(3,bone,1));
    const disabled=!s.salesOpen||s.purchase.status==="pending";if(disabled)c.setAlpha(.45);else c.setSize(Math.max(50,size),Math.max(50,size)).setInteractive({useHandCursor:true}).on("pointerover",()=>{if(!s.reducedMotion)this.tweens.add({targets:c,scale:1.08,y:y-5,duration:140});}).on("pointerout",()=>this.tweens.add({targets:c,scale:1,y,duration:120})).on("pointerdown",()=>{if(!s.reducedMotion)this.tweens.add({targets:c,scale:.94,duration:65,yoyo:true});this.bridge.emitIntent({type:"TOGGLE_NUMBER",value});});
    if(this.newlyDeselected?.value===value&&!s.reducedMotion){const displayWidth=Math.min(computeGrobLayout(this.scale.width,this.scale.height).mode==="mobile"?this.scale.width*.78:this.scale.width*.68,720),displayHeight=displayWidth/1.5,slot=this.newlyDeselected.slot===0?{x:this.scale.width/2-displayWidth*.196,y:computeGrobLayout(this.scale.width,this.scale.height).sarcophagusY-displayHeight*.186}:this.newlyDeselected.slot===1?{x:this.scale.width/2+displayWidth*.20,y:computeGrobLayout(this.scale.width,this.scale.height).sarcophagusY-displayHeight*.186}:{x:this.scale.width/2,y:computeGrobLayout(this.scale.width,this.scale.height).sarcophagusY-displayHeight*.38};c.setPosition(slot.x,slot.y).setScale(.86);this.tweens.add({targets:c,x,y,scale:1,duration:300,ease:"Cubic.Out"});}
  }
  private drawRail(l:ReturnType<typeof computeGrobLayout>,s:GrobSnapshot){
    const y=l.height-(l.mode==="mobile"?82:78);
    const price=s.lottery.ticket_price??0;
    const start=l.mode==="mobile"?l.width*.25:l.centerX-l.sarcophagusWidth*.02,gap=l.mode==="mobile"?l.width*.25:112;
    ([1,5,25] as QuickQuantity[]).forEach((quantity,index)=>{
      const x=start+index*gap,device=this.add.container(x,y).setDepth(10),active=s.purchase.status!=="pending"&&s.salesOpen&&balanceEnough(s,price*quantity);this.add.ellipse(x,y+17,86,18,0x050607,.7).setDepth(8);
      if(quantity===1){device.add([this.add.image(0,-8,"grob-number-seal").setCrop(220,220,820,820).setDisplaySize(60,60),this.add.text(0,-8,"1",{fontFamily:"Georgia",fontSize:"19px",color:"#e5d4af",stroke:"#15100e",strokeThickness:3}).setOrigin(.5)]);}else if(quantity===5){device.add(this.add.image(0,-11,"grob-quick-five").setDisplaySize(67,82));}else{device.add(this.add.image(0,-8,"grob-quick-xxv").setDisplaySize(92,69));}
      device.setAlpha(active?1:.42).setSize(78,66);if(active)device.setInteractive({useHandCursor:true}).on("pointerdown",()=>this.bridge.emitIntent({type:"BUY_QUICK",quantity}));
      if(s.purchase.mode==="quick"&&s.purchase.quantity===quantity){if(s.purchase.status==="pending")device.setY(4);if(s.purchase.status==="success"&&!s.reducedMotion)this.tweens.add({targets:device,scale:1.18,angle:quantity===25?3:-5,duration:170,yoyo:true,repeat:2,ease:"Back.Out"});}
      this.add.text(x,y+27,`${quantity===1?"1 БИЛЕТ":`${quantity} БИЛЕТОВ`}\n${money(price*quantity)}`,{fontFamily:"Arial",fontSize:l.mode==="mobile"?"8px":"10px",fontStyle:"bold",align:"center",color:"#e1d5bd",stroke:"#090a0b",strokeThickness:3,lineSpacing:2}).setOrigin(.5,0);
    });
    const status=s.purchase.message||(!s.salesOpen?"ПРОДАЖИ ЗАКРЫТЫ":"");
    const statusText=this.add.text(l.centerX,l.height-13,status,{fontFamily:"Georgia,serif",fontSize:l.mode==="mobile"?"11px":"14px",fontStyle:"bold",color:s.purchase.status==="error"||s.purchase.status==="uncertain"?"#e18b83":s.purchase.status==="success"?"#f2d38e":"#c7c3b9",stroke:"#090a0b",strokeThickness:3}).setOrigin(.5);
    if(s.purchase.status==="uncertain")statusText.setInteractive({useHandCursor:true}).on("pointerdown",()=>this.bridge.emitIntent({type:"RETRY_PURCHASE"}));
  }
  private drawEmberLinks(slots:{x:number;y:number}[],target:{x:number;y:number},ready:boolean,reduced:boolean){
    const glow=this.add.circle(target.x,target.y,ready?22:13,ready?0xcf4e27:0x7f291e,ready?.22:.10).setDepth(5).setBlendMode(Phaser.BlendModes.ADD);
    if(reduced)return;
    this.tweens.add({targets:glow,scale:ready?1.7:1.3,alpha:ready?.08:.03,duration:720,yoyo:true,repeat:-1,ease:"Sine.InOut"});
    slots.forEach((slot,index)=>{const curve=new Phaser.Curves.QuadraticBezier(new Phaser.Math.Vector2(slot.x,slot.y),new Phaser.Math.Vector2((slot.x+target.x)/2+(index-1)*8,Math.min(slot.y,target.y)-24),new Phaser.Math.Vector2(target.x,target.y));for(let sparkIndex=0;sparkIndex<5;sparkIndex++){const ember=this.add.circle(slot.x,slot.y,ready?2.6:2,ready?0xffb04d:0xc64b2f,.15).setDepth(6).setBlendMode(Phaser.BlendModes.ADD),point=new Phaser.Math.Vector2(),progress={value:sparkIndex/5};this.tweens.add({targets:progress,value:1+sparkIndex/5,duration:820+index*90,repeat:-1,delay:sparkIndex*95,onUpdate:()=>{const value=progress.value%1;curve.getPoint(value,point);ember.setPosition(point.x,point.y);ember.setAlpha(Math.sin(Math.PI*value)*(ready?.82:.48));ember.setScale(.7+Math.sin(Math.PI*value)*.8);}});}});
  }
  private burstDust(x:number,y:number,radius:number){if(this.snapshot?.reducedMotion)return;for(let i=0;i<10;i++){const angle=(Math.PI*2*i)/10,dot=this.add.circle(x,y,1+(i%3),0xc8b38e,.34).setDepth(12);this.tweens.add({targets:dot,x:x+Math.cos(angle)*radius*(.45+(i%4)*.15),y:y+Math.sin(angle)*radius*.55,alpha:0,duration:360+(i%3)*80,onComplete:()=>dot.destroy()});}}
}
function balanceEnough(s:GrobSnapshot,cost:number){return s.balance>=cost&&cost>0;}
