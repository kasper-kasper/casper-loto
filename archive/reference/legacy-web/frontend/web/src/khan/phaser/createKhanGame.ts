import Phaser from "phaser";
import type { KhanBridge } from "../bridge/KhanBridge";
import { KhanBootScene } from "./scenes/KhanBootScene";
import { KhanOverlayScene } from "./scenes/KhanOverlayScene";
import { KhanPlayScene } from "./scenes/KhanPlayScene";
import { KhanPreloadScene } from "./scenes/KhanPreloadScene";

export function createKhanGame(parent:HTMLElement,bridge:KhanBridge){
  return new Phaser.Game({type:Phaser.AUTO,parent,width:parent.clientWidth,height:parent.clientHeight,backgroundColor:"#061435",antialias:true,pixelArt:false,scale:{mode:Phaser.Scale.RESIZE,autoCenter:Phaser.Scale.CENTER_BOTH},render:{powerPreference:"high-performance",antialias:true,roundPixels:false},callbacks:{preBoot:game=>{game.registry.set("khanBridge",bridge);}},scene:[KhanBootScene,KhanPreloadScene,KhanPlayScene,KhanOverlayScene]});
}
