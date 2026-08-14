import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";
import { initializeTelegram } from "./telegram";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App initData={initializeTelegram()} />
  </StrictMode>,
);
