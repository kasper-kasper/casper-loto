import { computeClassicConsoleGeometry, type ClassicConsoleGeometry } from "../objects/ClassicLotteryConsole";

export type KhanLayoutMode="wide"|"compact"|"mobile";
export interface KhanLayout {width:number;height:number;mode:KhanLayoutMode;boardX:number;boardY:number;boardWidth:number;boardHeight:number;ballRadius:number;ballPositions:{x:number;y:number}[];slotPositions:{x:number;y:number}[];dockX:number;dockY:number;console:ClassicConsoleGeometry|null;}

export function computeKhanLayout(width:number,height:number):KhanLayout {
  const mode:KhanLayoutMode=width<760?"mobile":width<900?"compact":"wide";
  if(mode!=="mobile"){
    const console=computeClassicConsoleGeometry(width,height);
    const boardPositions=console.ballPositions;
    const boardLeft=Math.min(...boardPositions.map(position=>position.x))-console.ballRadius*1.7;
    const boardRight=Math.max(...boardPositions.map(position=>position.x))+console.ballRadius*1.7;
    const boardTop=Math.min(...boardPositions.map(position=>position.y))-console.ballRadius*1.7;
    const boardBottom=Math.max(...boardPositions.map(position=>position.y))+console.ballRadius*1.7;
    return{width,height,mode,boardX:(boardLeft+boardRight)/2,boardY:(boardTop+boardBottom)/2,boardWidth:boardRight-boardLeft,boardHeight:boardBottom-boardTop,ballRadius:console.ballRadius,ballPositions:console.ballPositions,slotPositions:console.slotPositions,dockX:console.actionPositions[0].x,dockY:(console.actionPositions[0].y+console.actionPositions[3].y)/2,console};
  }
  const boardWidth=width*.94;
  const boardHeight=Math.min(height*.45,430);
  const boardX=width*.5,boardY=height*.60;
  const ballRadius=Math.max(14,Math.min(boardWidth/18,boardHeight/15,36));
  const usableW=boardWidth-ballRadius*3.1,usableH=boardHeight-ballRadius*3.25;
  const ballPositions=Array.from({length:36},(_,index)=>({x:boardX-usableW/2+(index%6)*(usableW/5),y:boardY-usableH/2+Math.floor(index/6)*(usableH/5)}));
  const slotY=height*.31,slotGap=Math.min(width*.14,92);
  const slotPositions=Array.from({length:6},(_,index)=>({x:boardX+(index-2.5)*slotGap,y:slotY}));
  return{width,height,mode,boardX,boardY,boardWidth,boardHeight,ballRadius,ballPositions,slotPositions,dockX:width*.5,dockY:height*.90,console:null};
}
