import Phaser from "phaser";

export interface ClassicConsoleGeometry {
  centerX:number;
  centerY:number;
  width:number;
  height:number;
  left:number;
  top:number;
  ballRadius:number;
  ballPositions:{x:number;y:number}[];
  slotPositions:{x:number;y:number}[];
  actionPositions:{x:number;y:number}[];
  jackpot:{x:number;y:number;width:number;height:number};
}

const GRID_X=[.16,.27,.38,.49,.60,.69];
const GRID_Y=[.40,.48,.56,.64,.72,.80];
const SLOT_X=[.265,.33,.395,.46,.525,.59];
const ACTION_Y=[.395,.50,.61,.725];

export function computeClassicConsoleGeometry(viewWidth:number,viewHeight:number):ClassicConsoleGeometry {
  const width=Math.min(viewWidth*.94,viewHeight*1.68,1500),height=width/2;
  const centerX=viewWidth/2,centerY=viewHeight*1.03-height/2,left=centerX-width/2,top=centerY-height/2;
  const ballRadius=Math.max(14,Math.min(width*.0225,height*.038));
  const ballPositions=GRID_Y.flatMap(y=>GRID_X.map(x=>({x:left+width*x,y:top+height*y})));
  const slotPositions=SLOT_X.map(x=>({x:left+width*x,y:top+height*.215}));
  const actionPositions=ACTION_Y.map(y=>({x:left+width*.84,y:top+height*y}));
  return{centerX,centerY,width,height,left,top,ballRadius,ballPositions,slotPositions,actionPositions,jackpot:{x:left+width*.43,y:top+height*.315,width:Math.min(310,width*.27),height:Math.min(54,height*.088)}};
}

export function addClassicConsoleShell(scene:Phaser.Scene,geometry:ClassicConsoleGeometry,texture="classic-console-shell"){
  return scene.add.image(geometry.centerX,geometry.centerY,texture).setDisplaySize(geometry.width,geometry.height).setDepth(1);
}

