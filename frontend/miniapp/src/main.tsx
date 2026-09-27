import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { broadcastPreviewConfig } from "./broadcastPreview";
import { BroadcastPreviewBanner } from "./BroadcastPreviewBanner";
import { installMotionBudget } from "./performance";
import "./styles.css";
import "./lottery-themes.css";
import "./account.css";
import { initializeTelegram, isLocalDevMode } from "./telegram";

async function start(): Promise<void> {
  performance.mark("miniapp:runtime-ready");
  installMotionBudget();
  const broadcastPreview = broadcastPreviewConfig();
  if (broadcastPreview) document.documentElement.dataset.broadcastPreview = "true";
  if (import.meta.env.VITE_DESIGN_PREVIEW === "true" || broadcastPreview) {
    const { installDesignPreview } = await import("./designPreview");
    installDesignPreview();
  }
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <BroadcastPreviewBanner />
      <App initData={initializeTelegram()} localDev={isLocalDevMode() || Boolean(broadcastPreview)} />
    </StrictMode>,
  );
}

void start();
