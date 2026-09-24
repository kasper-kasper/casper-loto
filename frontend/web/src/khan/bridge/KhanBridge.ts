import type { KhanIntent, KhanSnapshot } from "./contracts";

export class KhanBridge {
  private snapshots=new Set<(snapshot:KhanSnapshot)=>void>();
  private intents=new Set<(intent:KhanIntent)=>void>();
  private last:KhanSnapshot|null=null;
  private disposed=false;

  publish(snapshot:KhanSnapshot){if(this.disposed||(this.last&&snapshot.revision<=this.last.revision))return;this.last=snapshot;this.snapshots.forEach(listener=>listener(snapshot));}
  subscribeSnapshot(listener:(snapshot:KhanSnapshot)=>void){if(this.disposed)return()=>undefined;this.snapshots.add(listener);if(this.last)listener(this.last);return()=>{this.snapshots.delete(listener);};}
  emitIntent(intent:KhanIntent){if(!this.disposed)this.intents.forEach(listener=>listener(intent));}
  subscribeIntent(listener:(intent:KhanIntent)=>void){if(this.disposed)return()=>undefined;this.intents.add(listener);return()=>{this.intents.delete(listener);};}
  dispose(){this.disposed=true;this.last=null;this.snapshots.clear();this.intents.clear();}
}
