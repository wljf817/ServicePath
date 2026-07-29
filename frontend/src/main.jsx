import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import "./styles.css";
import "./styles/foundation.css";
import "./styles/dashboard.css";
import "./styles/results.css";
import "./styles/pages.css";

ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
);
