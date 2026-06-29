import "./styles/app.css";
import { createApp } from "./app";

const root = document.querySelector<HTMLDivElement>("#app");
if (!root) throw new Error("#app not found");

createApp(root);
