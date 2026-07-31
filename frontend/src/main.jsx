import {StrictMode} from "react";
import {createRoot} from "react-dom/client";

import App from "./App";
import "./styles/foundation.css";
import "./styles/dashboard.css";
import "./styles/results.css";
import "./styles/pages.css";
import "./styles/motion.css";

createRoot(document.getElementById("root")).render(
    <StrictMode>
        <App />
    </StrictMode>,
);
