import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { installMotionBudget } from "./performance";
import "./styles.css";
import "./lottery-themes.css";
import { initializeTelegram, isLocalDevMode } from "./telegram";

async function start(): Promise<void> {
  installMotionBudget();
  if (import.meta.env.VITE_DESIGN_PREVIEW === "true") {
    const { installDesignPreview } = await import("./designPreview");
    installDesignPreview();
  }
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App initData={initializeTelegram()} localDev={isLocalDevMode()} />
    </StrictMode>,
  );
}

void start();
