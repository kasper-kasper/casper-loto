import Phaser from "phaser";
import type { GrobBridge } from "../bridge/GrobBridge";
import { GrobBootScene } from "./scenes/GrobBootScene";
import { GrobLiveScene } from "./scenes/GrobLiveScene";
import { GrobOverlayScene } from "./scenes/GrobOverlayScene";
import { GrobPlayScene } from "./scenes/GrobPlayScene";
import { GrobPreloadScene } from "./scenes/GrobPreloadScene";

export function createGrobGame(parent:HTMLElement,bridge:GrobBridge,mode:"play"|"live"="play"){
  return new Phaser.Game({type:Phaser.AUTO,parent,width:parent.clientWidth,height:parent.clientHeight,backgroundColor:"#050609",antialias:true,pixelArt:false,scale:{mode:Phaser.Scale.RESIZE,autoCenter:Phaser.Scale.CENTER_BOTH},render:{powerPreference:"high-performance",antialias:true,roundPixels:false},callbacks:{preBoot:game=>{game.registry.set("grobBridge",bridge);game.registry.set("grobMode",mode);}},scene:[GrobBootScene,GrobPreloadScene,GrobPlayScene,GrobLiveScene,GrobOverlayScene]});
}
