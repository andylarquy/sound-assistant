import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { StateProvider } from "./state/StateProvider";
import "./styles/global.scss";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <StateProvider>
      <App />
    </StateProvider>
  </StrictMode>,
);
