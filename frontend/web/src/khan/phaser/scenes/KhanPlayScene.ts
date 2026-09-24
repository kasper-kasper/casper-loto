import Phaser from "phaser";
import type { KhanBridge } from "../../bridge/KhanBridge";
import type { KhanQuickQuantity, KhanSnapshot } from "../../bridge/contracts";
import { computeKhanLayout, type KhanLayout } from "../layout/KhanLayout";
import { addClassicConsoleShell } from "../objects/ClassicLotteryConsole";

const gold=0xe9b83f,ivory=0xfff6dc,navy=0x07183b;
const money=(value:number)=>`${value.toLocaleString("ru-RU")} CAS`;

export class KhanPlayScene extends Phaser.Scene {
  private bridge!:KhanBridge;
  private snapshot:KhanSnapshot|null=null;
  private unsubscribe:()=>void=()=>{};
  private signature="";
  private focusIndex=0;
  private newlySelected:number|null=null;
  private pointerX=0;
  private pointerY=0;

  constructor(){super("KhanPlay");}

  create(){
    this.bridge=this.registry.get("khanBridge") as KhanBridge;
    this.unsubscribe=this.bridge.subscribeSnapshot(snapshot=>this.apply(snapshot));
    this.scale.on("resize",this.redraw,this);
    this.input.keyboard?.on("keydown-TAB",(event:KeyboardEvent)=>{event.preventDefault();this.focusIndex=(this.focusIndex+(event.shiftKey?-1:1)+40)%40;this.redraw();});
    this.input.keyboard?.on("keydown-ENTER",()=>this.activateFocus());
    this.input.keyboard?.on("keydown-SPACE",(event:KeyboardEvent)=>{event.preventDefault();this.activateFocus();});
    this.input.on("pointermove",(pointer:Phaser.Input.Pointer)=>{this.pointerX=(pointer.x/Math.max(1,this.scale.width)-.5)*7;this.pointerY=(pointer.y/Math.max(1,this.scale.height)-.5)*4;});
    this.events.once(Phaser.Scenes.Events.SHUTDOWN,()=>{this.unsubscribe();this.scale.off("resize",this.redraw,this);});
  }

  update(){if(this.snapshot?.reducedMotion)return;this.cameras.main.scrollX=Phaser.Math.Linear(this.cameras.main.scrollX,this.pointerX,.025);this.cameras.main.scrollY=Phaser.Math.Linear(this.cameras.main.scrollY,this.pointerY,.025);}

  private activateFocus(){
    if(this.focusIndex<36)this.bridge.emitIntent({type:"TOGGLE_NUMBER",value:this.focusIndex+1});
    else if(this.focusIndex===36)this.bridge.emitIntent({type:"BUY_MANUAL"});
    else this.bridge.emitIntent({type:"BUY_QUICK",quantity:([1,5,25] as KhanQuickQuantity[])[this.focusIndex-37]});
  }

  private apply(snapshot:KhanSnapshot){
    const before=this.snapshot?.selectedNumbers??[];
    this.newlySelected=snapshot.selectedNumbers.find(value=>!before.includes(value))??null;
    this.snapshot=snapshot;
    const signature=JSON.stringify([snapshot.phase,snapshot.balance,snapshot.selectedNumbers,snapshot.purchase.status,snapshot.purchase.message,snapshot.lottery.draw_number,snapshot.lottery.jackpot,snapshot.salesOpen,this.scale.width,this.scale.height]);
    if(signature!==this.signature){this.signature=signature;this.redraw();}
  }

  private redraw(){
    const snapshot=this.snapshot;if(!snapshot)return;
    this.children.removeAll(true);this.tweens.killAll();
    const layout=computeKhanLayout(this.scale.width,this.scale.height);
    const bg=this.add.image(layout.width/2,layout.height/2,"khan-studio");
    bg.setScale(Math.max(layout.width/bg.width,layout.height/bg.height)).setDepth(-20);
    this.add.rectangle(layout.width/2,layout.height/2,layout.width,layout.height,0x03102e,.07).setDepth(-19);
    this.drawLights(layout,snapshot);
    if(layout.console)addClassicConsoleShell(this,layout.console);
    else this.drawMobileShell(layout);
    this.drawTicketRail(layout,snapshot);
    this.drawJackpot(layout,snapshot);
    this.drawBoard(layout,snapshot);
    this.drawDock(layout,snapshot);
    this.drawStatus(layout,snapshot);
    this.newlySelected=null;
  }

  private drawLights(layout:KhanLayout,snapshot:KhanSnapshot){
    const drumX=layout.width*.5,drumY=layout.height*.29;
    const aura=this.add.ellipse(drumX,drumY,Math.min(390,layout.width*.34),Math.min(310,layout.height*.43),0x78a8ff,.055).setBlendMode(Phaser.BlendModes.ADD).setDepth(-9);
    const halo=this.add.ellipse(drumX,drumY,Math.min(330,layout.width*.28),Math.min(270,layout.height*.37),0,0).setStrokeStyle(2,0xffd972,.20).setBlendMode(Phaser.BlendModes.ADD).setDepth(-8);
    const left=this.add.triangle(layout.width*.17,layout.height*.26,0,0,layout.width*.22,0,layout.width*.09,layout.height*.72,0x76a7ff,.04).setBlendMode(Phaser.BlendModes.ADD).setDepth(-7);
    const right=this.add.triangle(layout.width*.83,layout.height*.26,0,0,-layout.width*.22,0,-layout.width*.09,layout.height*.72,0xffd45f,.032).setBlendMode(Phaser.BlendModes.ADD).setDepth(-7);
    if(snapshot.reducedMotion)return;
    this.tweens.add({targets:aura,scale:{from:.96,to:1.06},alpha:{from:.035,to:.09},duration:2300,yoyo:true,repeat:-1,ease:"Sine.InOut"});
    this.tweens.add({targets:halo,angle:360,alpha:{from:.10,to:.26},duration:13000,repeat:-1,ease:"Linear"});
    this.tweens.add({targets:left,angle:{from:-4,to:5},alpha:{from:.02,to:.065},duration:5800,yoyo:true,repeat:-1,ease:"Sine.InOut"});
    this.tweens.add({targets:right,angle:{from:4,to:-5},alpha:{from:.018,to:.055},duration:6600,yoyo:true,repeat:-1,ease:"Sine.InOut"});
    for(let i=0;i<18;i++){const dust=this.add.circle((i*137)%layout.width,(i*83)%layout.height,1+i%2,0xffefc0,.10).setDepth(-4);this.tweens.add({targets:dust,y:dust.y-30-i%5*8,alpha:.015,duration:7000+i%6*700,yoyo:true,repeat:-1,delay:i*120});}
  }

  private drawMobileShell(layout:KhanLayout){
    const{x,y,w,h}={x:layout.boardX-layout.boardWidth/2,y:layout.boardY-layout.boardHeight/2,w:layout.boardWidth,h:layout.boardHeight};
    this.add.ellipse(layout.boardX,layout.boardY+h*.5+14,w*.9,h*.18,0x000000,.5).setDepth(0);
    const board=this.add.graphics().setDepth(1);
    board.fillStyle(0x061535,.96).lineStyle(5,0xbf8528,1).fillRoundedRect(x,y,w,h,Math.min(34,w*.04)).strokeRoundedRect(x,y,w,h,Math.min(34,w*.04));
    board.lineStyle(2,0xffd666,.78).strokeRoundedRect(x+8,y+8,w-16,h-16,Math.min(28,w*.035));
    board.lineStyle(1,0x8db8ff,.14);for(let i=1;i<6;i++)board.lineBetween(x+w*i/6,y+18,x+w*i/6,y+h-18);
  }

  private drawTicketRail(layout:KhanLayout,snapshot:KhanSnapshot){
    const positions=layout.slotPositions,r=layout.mode==="mobile"?19:layout.ballRadius*1.12,left=positions[0].x-r*1.7,right=positions[5].x+r*1.7,y=positions[0].y;
    if(!layout.console){const panel=this.add.graphics().setDepth(3);panel.fillStyle(0x061738,.96).lineStyle(3,gold,.95).fillRoundedRect(left,y-r*1.48,right-left,r*2.96,18).strokeRoundedRect(left,y-r*1.48,right-left,r*2.96,18);panel.lineStyle(1,0xffefb1,.38).strokeRoundedRect(left+6,y-r*1.48+6,right-left-12,r*2.96-12,13);}
    const labelY=layout.console?y-r*1.75:y-r*2.06,label=this.add.container((left+right)/2,labelY).setDepth(9),labelW=layout.mode==="mobile"?150:182,labelH=layout.mode==="mobile"?20:23,labelFace=this.add.graphics();labelFace.fillStyle(0x07183b,.94).lineStyle(1,0xd8a43b,.9).fillRoundedRect(-labelW/2,-labelH/2,labelW,labelH,7).strokeRoundedRect(-labelW/2,-labelH/2,labelW,labelH,7);label.add([labelFace,this.add.text(0,0,`ВАШ БИЛЕТ · ${snapshot.selectedNumbers.length}/6`,{fontFamily:"Arial",fontSize:layout.mode==="mobile"?"8px":"9px",fontStyle:"bold",color:"#ffe5a0",letterSpacing:1}).setOrigin(.5)]);
    positions.forEach((position,index)=>{const value=snapshot.selectedNumbers[index];if(!layout.console){this.add.circle(position.x,position.y,r,0x02091b,.86).setStrokeStyle(2,0xb78b32,.72).setDepth(4);this.add.circle(position.x,position.y,r*.72,0x1d315a,.32).setStrokeStyle(1,0xffe9a4,.18).setDepth(4);}if(value==null){if(!layout.console)this.add.text(position.x,position.y,"·",{fontFamily:"Georgia",fontSize:`${r*1.2}px`,color:"#907848"}).setOrigin(.5).setDepth(5);return;}const ball=this.makeBall(position.x,position.y,r*.92,value,true,8);if(value===this.newlySelected&&!snapshot.reducedMotion){const source=layout.ballPositions[value-1],curve=new Phaser.Curves.QuadraticBezier(new Phaser.Math.Vector2(source.x,source.y),new Phaser.Math.Vector2((source.x+position.x)/2,Math.min(source.y,position.y)-layout.height*.14),new Phaser.Math.Vector2(position.x,position.y)),point=new Phaser.Math.Vector2(),progress={value:0};ball.setPosition(source.x,source.y).setScale(.72);this.tweens.add({targets:progress,value:1,duration:480,ease:"Cubic.Out",onUpdate:()=>{curve.getPoint(progress.value,point);ball.setPosition(point.x,point.y);ball.setScale(.72+.28*progress.value);},onComplete:()=>{this.tweens.add({targets:ball,scale:1.08,duration:90,yoyo:true});this.spark(position.x,position.y,r*2.2);}});}if(snapshot.purchase.status==="success"&&!snapshot.reducedMotion)this.tweens.add({targets:ball,y:position.y-34,alpha:0,scale:.5,duration:620,delay:index*55,ease:"Cubic.In"});});
  }

  private drawJackpot(layout:KhanLayout,snapshot:KhanSnapshot){
    const plaque=layout.console?.jackpot??{x:layout.width/2,y:layout.height*.355,width:Math.min(220,layout.width*.56),height:36},g=this.add.graphics().setDepth(12);
    g.fillStyle(0x071632,.98).lineStyle(3,0xd89b28,1).fillRoundedRect(plaque.x-plaque.width/2,plaque.y-plaque.height/2,plaque.width,plaque.height,13).strokeRoundedRect(plaque.x-plaque.width/2,plaque.y-plaque.height/2,plaque.width,plaque.height,13);
    g.lineStyle(1,0xffe59a,.60).strokeRoundedRect(plaque.x-plaque.width/2+6,plaque.y-plaque.height/2+6,plaque.width-12,plaque.height-12,9);
    this.add.circle(plaque.x-plaque.width/2+17,plaque.y,5,0xf0bd4e,1).setStrokeStyle(2,0xffe9a2).setDepth(13);this.add.circle(plaque.x+plaque.width/2-17,plaque.y,5,0xf0bd4e,1).setStrokeStyle(2,0xffe9a2).setDepth(13);
    this.add.text(plaque.x,plaque.y-plaque.height*.17,"ДЖЕКПОТ",{fontFamily:"Arial",fontSize:"8px",fontStyle:"bold",color:"#d7b967",letterSpacing:2}).setOrigin(.5).setDepth(13);
    const value=`${snapshot.lottery.jackpot.toLocaleString("ru-RU")} CAS`,glow=this.add.text(plaque.x,plaque.y+plaque.height*.16,value,{fontFamily:"Georgia",fontSize:`${Math.max(13,plaque.height*.34)}px`,fontStyle:"bold",color:"#ffe9a0",stroke:"#8f5c12",strokeThickness:2}).setOrigin(.5).setDepth(13);
    if(!snapshot.reducedMotion)this.tweens.add({targets:glow,alpha:{from:.86,to:1},duration:1500,yoyo:true,repeat:-1,ease:"Sine.InOut"});
  }

  private drawBoard(layout:KhanLayout,snapshot:KhanSnapshot){
    layout.ballPositions.forEach((position,index)=>{const value=index+1,selected=snapshot.selectedNumbers.includes(value),disabled=!snapshot.salesOpen||snapshot.purchase.status==="pending",ball=this.makeBall(position.x,position.y,layout.ballRadius,value,selected,5);if(this.focusIndex===index)this.add.circle(position.x,position.y,layout.ballRadius*1.30,0x000000,0).setStrokeStyle(3,0xffffff,1).setDepth(9);if(disabled)ball.setAlpha(.48);else ball.setSize(layout.ballRadius*2.55,layout.ballRadius*2.55).setInteractive({useHandCursor:true}).on("pointerover",()=>{if(!snapshot.reducedMotion)this.tweens.add({targets:ball,scale:1.12,y:position.y-5,duration:140,ease:"Back.Out"});}).on("pointerout",()=>this.tweens.add({targets:ball,scale:1,y:position.y,duration:110})).on("pointerdown",()=>{if(!snapshot.reducedMotion)this.tweens.add({targets:ball,scale:.90,duration:65,yoyo:true});this.bridge.emitIntent({type:"TOGGLE_NUMBER",value});});});
  }

  private drawDock(layout:KhanLayout,snapshot:KhanSnapshot){
    const price=snapshot.lottery.ticket_price??0;
    if(layout.console){
      const positions=layout.console.actionPositions,tabletTitleY=positions[0].y-layout.console.height*.073;
      this.add.text(positions[0].x,tabletTitleY,"БЫСТРАЯ ИГРА",{fontFamily:"Arial",fontSize:"9px",fontStyle:"bold",color:"#ffe1a0",stroke:"#08142d",strokeThickness:3,letterSpacing:2}).setOrigin(.5).setDepth(10);
      ([1,5,25] as KhanQuickQuantity[]).forEach((quantity,index)=>{const position=positions[index],active=snapshot.salesOpen&&snapshot.purchase.status!=="pending"&&snapshot.balance>=price*quantity,bw=layout.console!.width*.17,bh=layout.console!.height*.075,button=this.add.container(position.x,position.y).setDepth(10),hover=this.add.graphics();hover.fillStyle(0x2855a0,.001).lineStyle(1,active?0xffdfa0:0x72798a,.55).fillRoundedRect(-bw/2,-bh/2,bw,bh,12).strokeRoundedRect(-bw/2,-bh/2,bw,bh,12);const label=this.add.text(0,-4,quantity===1?"СЛУЧАЙНЫЙ":`×${quantity}`,{fontFamily:"Arial",fontSize:quantity===25?"16px":"13px",fontStyle:"bold",color:active?"#fff0bd":"#777f94"}).setOrigin(.5),cost=this.add.text(0,12,money(price*quantity),{fontFamily:"Arial",fontSize:"7px",fontStyle:"bold",color:active?"#8fa4d2":"#666c7a"}).setOrigin(.5);button.add([hover,label,cost]).setAlpha(active?1:.52).setSize(bw,bh);if(active)button.setInteractive({useHandCursor:true}).on("pointerover",()=>{hover.clear().fillStyle(0x315fa3,.22).lineStyle(2,0xffdc82,.95).fillRoundedRect(-bw/2,-bh/2,bw,bh,12).strokeRoundedRect(-bw/2,-bh/2,bw,bh,12);}).on("pointerout",()=>{hover.clear().fillStyle(0x2855a0,.001).lineStyle(1,0xffdfa0,.55).fillRoundedRect(-bw/2,-bh/2,bw,bh,12).strokeRoundedRect(-bw/2,-bh/2,bw,bh,12);}).on("pointerdown",()=>{this.bridge.emitIntent({type:"BUY_QUICK",quantity});if(!snapshot.reducedMotion)this.tweens.add({targets:button,scale:.94,duration:70,yoyo:true});});if(this.focusIndex===37+index)button.add(this.add.rectangle(0,0,bw+7,bh+7,0,0).setStrokeStyle(2,ivory));});
      this.drawPurchaseButton(positions[3].x,positions[3].y,layout.console.width*.18,layout.console.height*.095,layout,snapshot,price);
      return;
    }
    const panelW=Math.min(layout.width*.9,560),panelH=68,panelX=layout.dockX-panelW/2,panelY=layout.dockY-panelH/2,panel=this.add.graphics().setDepth(8);panel.fillStyle(navy,.96).lineStyle(3,gold,.96).fillRoundedRect(panelX,panelY,panelW,panelH,25).strokeRoundedRect(panelX,panelY,panelW,panelH,25);panel.lineStyle(1,0xffecaa,.32).strokeRoundedRect(panelX+7,panelY+7,panelW-14,panelH-14,19);
    ([1,5,25] as KhanQuickQuantity[]).forEach((quantity,index)=>{const bx=panelX+panelW*(.14+index*.22),by=layout.dockY,active=snapshot.salesOpen&&snapshot.purchase.status!=="pending"&&snapshot.balance>=price*quantity,bw=Math.min(100,panelW*.18),bh=44,button=this.add.container(bx,by).setDepth(10),face=this.add.graphics();face.fillStyle(active?0x102657:0x10182a,.94).lineStyle(1,active?0xe7b94d:0x5d6070,.9).fillRoundedRect(-bw/2,-bh/2,bw,bh,13).strokeRoundedRect(-bw/2,-bh/2,bw,bh,13);button.add([face,this.add.text(0,0,quantity===1?"СЛУЧАЙНЫЙ":`×${quantity}`,{fontFamily:"Arial",fontSize:quantity===25?"17px":"13px",fontStyle:"bold",color:active?"#fff0bc":"#777f94"}).setOrigin(.5)]).setAlpha(active?1:.52).setSize(bw,bh);if(active)button.setInteractive({useHandCursor:true}).on("pointerdown",()=>this.bridge.emitIntent({type:"BUY_QUICK",quantity}));});
    this.drawPurchaseButton(panelX+panelW*.83,layout.dockY,Math.min(132,panelW*.25),48,layout,snapshot,price);
  }

  private drawPurchaseButton(x:number,y:number,width:number,height:number,layout:KhanLayout,snapshot:KhanSnapshot,price:number){
    const canBuy=snapshot.selectedNumbers.length===6&&snapshot.salesOpen&&snapshot.purchase.status!=="pending"&&snapshot.balance>=price,buy=this.add.container(x,y).setDepth(12),face=this.add.graphics();face.fillStyle(canBuy?0xffe6a3:0x343d53,1).lineStyle(3,canBuy?0xffb72e:0x697083,1).fillRoundedRect(-width/2,-height/2,width,height,16).strokeRoundedRect(-width/2,-height/2,width,height,16);face.lineStyle(1,canBuy?0xffffff:0x858b99,.62).strokeRoundedRect(-width/2+5,-height/2+5,width-10,height-10,11);buy.add([face,this.add.text(0,-6,canBuy?"КУПИТЬ БИЛЕТ":"ВЫБЕРИТЕ 6",{fontFamily:"Arial",fontSize:layout.mode==="mobile"?"10px":"12px",fontStyle:"bold",color:canBuy?"#3b2200":"#a9afbb"}).setOrigin(.5),this.add.text(0,12,money(price),{fontFamily:"Arial",fontSize:"8px",fontStyle:"bold",color:canBuy?"#76500a":"#858b99"}).setOrigin(.5)]).setSize(width,height);if(canBuy)buy.setInteractive({useHandCursor:true}).on("pointerover",()=>{if(!snapshot.reducedMotion)this.tweens.add({targets:buy,scale:1.035,duration:120});}).on("pointerout",()=>this.tweens.add({targets:buy,scale:1,duration:100})).on("pointerdown",()=>{this.bridge.emitIntent({type:"BUY_MANUAL"});if(!snapshot.reducedMotion)this.tweens.add({targets:buy,scale:.94,duration:75,yoyo:true});});if(this.focusIndex===36)buy.add(this.add.rectangle(0,0,width+8,height+8,0,0).setStrokeStyle(2,ivory));
  }

  private drawStatus(layout:KhanLayout,snapshot:KhanSnapshot){
    const status=snapshot.purchase.message||(!snapshot.salesOpen?"ПРОДАЖИ ЗАКРЫТЫ":snapshot.selectedNumbers.length<6?"НАЖИМАЙТЕ НА ШАРЫ":"КОМБИНАЦИЯ ГОТОВА"),y=layout.console?Math.min(layout.height-13,layout.console.top+layout.console.height*.895):layout.height*.835,text=this.add.text(layout.console?layout.console.left+layout.console.width*.40:layout.width/2,y,status,{fontFamily:"Arial",fontSize:layout.mode==="mobile"?"9px":"10px",fontStyle:"bold",color:snapshot.purchase.status==="error"||snapshot.purchase.status==="uncertain"?"#ffb1a2":snapshot.purchase.status==="success"?"#fff0a8":"#c9d6f0",stroke:"#06122e",strokeThickness:4,letterSpacing:1}).setOrigin(.5).setDepth(20);if(snapshot.purchase.status==="uncertain")text.setInteractive({useHandCursor:true}).on("pointerdown",()=>this.bridge.emitIntent({type:"RETRY_PURCHASE"}));if(snapshot.purchase.status==="success"&&!snapshot.reducedMotion){const flash=this.add.ellipse(layout.boardX,layout.slotPositions[0].y,layout.boardWidth*.82,90,0xffd660,.24).setBlendMode(Phaser.BlendModes.ADD).setDepth(18);this.tweens.add({targets:flash,scale:1.5,alpha:0,duration:800});this.cameras.main.flash(180,255,224,128,false);}
  }

  private makeBall(x:number,y:number,radius:number,value:number,selected:boolean,depth:number){
    const container=this.add.container(x,y).setDepth(depth),glow=this.add.circle(0,0,radius*1.26,0xffcf48,selected?.30:.025).setBlendMode(Phaser.BlendModes.ADD),sprite=this.add.image(0,0,selected?"khan-ball-selected":"khan-ball").setDisplaySize(radius*2.34,radius*2.34),label=this.add.text(0,-radius*.04,String(value),{fontFamily:"Arial",fontSize:`${Math.max(13,radius*.82)}px`,fontStyle:"bold",color:"#121316",stroke:"#fff8e8",strokeThickness:1}).setOrigin(.5);container.add([glow,sprite,label]);if(selected&&!this.snapshot?.reducedMotion)this.tweens.add({targets:glow,scale:1.22,alpha:.12,duration:620,yoyo:true,repeat:-1});return container;
  }

  private spark(x:number,y:number,radius:number){for(let i=0;i<10;i++){const angle=Math.PI*2*i/10,dot=this.add.circle(x,y,1+i%2,0xffe28b,.8).setBlendMode(Phaser.BlendModes.ADD).setDepth(20);this.tweens.add({targets:dot,x:x+Math.cos(angle)*radius,y:y+Math.sin(angle)*radius*.55,alpha:0,duration:380+i%3*70,onComplete:()=>dot.destroy()});}}
}
