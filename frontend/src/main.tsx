import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { MiloDataProvider } from "./data/MiloDataContext";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* BrowserRouter lets each screen have its own address, like /my-day */}
    <BrowserRouter>
      {/* MiloDataProvider holds the data every screen shares */}
      <MiloDataProvider>
        <App />
      </MiloDataProvider>
    </BrowserRouter>
  </StrictMode>
);
