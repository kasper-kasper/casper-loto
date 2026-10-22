import type { GrobPhase } from "../bridge/contracts";

export function selectionPhase(selected: number[], salesOpen: boolean): GrobPhase {
  if (!salesOpen) return "drawWaiting";
  if (selected.length === 0) return "idle";
  if (selected.length === 3) return "ready";
  return "selecting";
}

export function toggleSelection(selected: number[], value: number, max = 16, count = 3) {
  if (!Number.isInteger(value) || value < 1 || value > max) return selected;
  if (selected.includes(value)) return selected.filter(item => item !== value);
  if (selected.length >= count) return selected;
  return [...selected, value];
}

