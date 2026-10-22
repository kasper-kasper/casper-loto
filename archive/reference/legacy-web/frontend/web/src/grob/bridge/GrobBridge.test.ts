import { expect, test, vi } from "vitest";
import type { GrobSnapshot } from "./contracts";
import { GrobBridge } from "./GrobBridge";

test("bridge is instance scoped, revision guarded, and disposable",()=>{
  const bridge=new GrobBridge(),listener=vi.fn();bridge.subscribeSnapshot(listener);
  const value={revision:2} as GrobSnapshot;bridge.publish(value);bridge.publish({...value,revision:1});expect(listener).toHaveBeenCalledTimes(1);
  bridge.dispose();bridge.publish({...value,revision:3});expect(listener).toHaveBeenCalledTimes(1);
});

