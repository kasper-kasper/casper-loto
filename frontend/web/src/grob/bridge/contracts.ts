import type { LiveDraw, Lottery } from "../../types";

export type GrobPhase = "loading" | "idle" | "selecting" | "ready" | "purchasePending" | "purchaseSuccess" | "purchaseUncertain" | "purchaseError" | "drawWaiting" | "liveStarting" | "liveReveal" | "result" | "reconnecting" | "error";
export type QuickQuantity = 1 | 5 | 25;

export interface GrobPurchaseView {
  mode: "manual" | "quick" | null;
  quantity: QuickQuantity | null;
  status: "idle" | "pending" | "success" | "uncertain" | "error";
  message: string;
  ticketIds: string[];
}

export interface GrobLiveView {
  draw: LiveDraw | null;
  revealedNumbers: number[];
  revealCount: number;
  resultKind: "waiting" | "live" | "win" | "loss" | "spectator";
}

export interface GrobSnapshot {
  revision: number;
  phase: GrobPhase;
  lottery: Lottery;
  balance: number;
  selectedNumbers: number[];
  salesOpen: boolean;
  serverNow: number;
  purchase: GrobPurchaseView;
  live: GrobLiveView;
  reducedMotion: boolean;
  muted: boolean;
}

export type GrobIntent =
  | { type: "TOGGLE_NUMBER"; value: number }
  | { type: "BUY_MANUAL" }
  | { type: "BUY_QUICK"; quantity: QuickQuantity }
  | { type: "RETRY_PURCHASE" }
  | { type: "EXIT" }
  | { type: "SET_MUTED"; muted: boolean };

export type Unsubscribe = () => void;
