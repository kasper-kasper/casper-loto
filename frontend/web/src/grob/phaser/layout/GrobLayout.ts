export type GrobLayoutMode = "wide" | "compact" | "mobile";
export interface GrobLayout { width:number;height:number;mode:GrobLayoutMode;centerX:number;sarcophagusY:number;sarcophagusWidth:number;sarcophagusHeight:number;sealPositions:{x:number;y:number;scale:number}[]; }

export function computeGrobLayout(width:number,height:number):GrobLayout {
  const mode:GrobLayoutMode = width < 760 ? "mobile" : width < 1180 ? "compact" : "wide";
  const centerX=width/2;
  const sarcophagusWidth=Math.min(mode==="mobile"?width*.62:width*.46,640);
  const sarcophagusHeight=Math.min(mode==="mobile"?height*.30:height*.34,300);
  const sarcophagusY=mode==="mobile"?height*.50:height*.54;
  const sealPositions=Array.from({length:16},(_,index)=>{
    const left=index<8, step=left?index:index-8, progress=step/7;
    if(mode==="mobile") return {x:left?Math.max(42,width*.105):Math.min(width-42,width*.895),y:left?height*(.70-progress*.43):height*(.27+progress*.43),scale:.66};
    const sideProgress=left?1-progress:progress;
    return {x:centerX+(left?-1:1)*(sarcophagusWidth*.66+sideProgress*width*.12),y:left?height*(.72-progress*.43):height*(.29+progress*.43),scale:.66+sideProgress*.08};
  });
  return {width,height,mode,centerX,sarcophagusY,sarcophagusWidth,sarcophagusHeight,sealPositions};
}
