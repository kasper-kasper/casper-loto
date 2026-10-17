import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { MaintenanceGate } from "./MaintenanceGate";
import { PurchaseRecovery } from "./PurchaseRecovery";
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
  const initData = initializeTelegram();
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <MaintenanceGate>
      <BroadcastPreviewBanner />
      <App initData={initData} localDev={isLocalDevMode() || Boolean(broadcastPreview)} />
      <PurchaseRecovery initData={initData} />
      </MaintenanceGate>
    </StrictMode>,
  );
}

void start();
