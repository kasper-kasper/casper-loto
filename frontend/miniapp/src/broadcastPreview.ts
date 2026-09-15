const supportedLotteries = new Set(["pll", "pss", "khan", "weekly", "september", "grob", "bingo"]);

export type BroadcastPreviewScenario = "win" | "loss";

export interface BroadcastPreviewConfig {
  lotteryCode: string;
  scenario: BroadcastPreviewScenario;
}

export function broadcastPreviewConfig(): BroadcastPreviewConfig | null {
  const params = new URLSearchParams(window.location.search);
  const lotteryCode = params.get("broadcast-preview");
  if (!lotteryCode || !supportedLotteries.has(lotteryCode)) return null;
  return {
    lotteryCode,
    scenario: params.get("scenario") === "loss" ? "loss" : "win",
  };
}
