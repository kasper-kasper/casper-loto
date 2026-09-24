import type { Lottery } from "../../types";

export type KhanPhase = "idle" | "selecting" | "ready" | "purchasePending" | "purchaseSuccess" | "purchaseUncertain" | "purchaseError" | "drawWaiting" | "reconnecting";
export type KhanQuickQuantity = 1 | 5 | 25;

export interface KhanPurchaseView {
  mode: "manual" | "quick" | null;
  quantity: KhanQuickQuantity | null;
  status: "idle" | "pending" | "success" | "uncertain" | "error";
  message: string;
  ticketIds: string[];
}

export interface KhanSnapshot {
  revision: number;
  lottery: Lottery;
  balance: number;
  selectedNumbers: number[];
  salesOpen: boolean;
  serverNow: number;
  phase: KhanPhase;
  purchase: KhanPurchaseView;
  reducedMotion: boolean;
}

export type KhanIntent =
  | {type:"TOGGLE_NUMBER";value:number}
  | {type:"BUY_MANUAL"}
  | {type:"BUY_QUICK";quantity:KhanQuickQuantity}
  | {type:"RETRY_PURCHASE"}
  | {type:"EXIT"};
