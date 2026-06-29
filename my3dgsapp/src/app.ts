import { renderCapturePage } from "./pages/CapturePage";
import { renderHomePage } from "./pages/HomePage";
import { renderJobStatusPage } from "./pages/JobStatusPage";
import { renderMapPage } from "./pages/MapPage";
import { renderResultPage } from "./pages/ResultPage";
import { renderSettingsPage } from "./pages/SettingsPage";
import { renderUploadPage } from "./pages/UploadPage";

type Route = "home" | "settings" | "capture" | "upload" | "jobs" | "map" | "result";

const routes: Record<Route, () => string> = {
  home: renderHomePage,
  settings: renderSettingsPage,
  capture: renderCapturePage,
  upload: renderUploadPage,
  jobs: renderJobStatusPage,
  map: renderMapPage,
  result: renderResultPage
};

export function createApp(root: HTMLElement): void {
  const render = () => {
    const route = getRoute();
    root.innerHTML = `
      <main class="app-shell">
        <section class="app-content">${routes[route]()}</section>
        <nav class="tabbar">
          ${navItem("home", "首頁", route)}
          ${navItem("map", "地圖", route)}
          ${navItem("capture", "拍攝", route)}
          ${navItem("jobs", "任務", route)}
          ${navItem("settings", "設定", route)}
        </nav>
      </main>
    `;
  };

  window.addEventListener("hashchange", render);
  render();
}

function getRoute(): Route {
  const raw = location.hash.replace(/^#\/?/, "");
  if (raw in routes) return raw as Route;
  return "home";
}

function navItem(route: Route, label: string, activeRoute: Route): string {
  const active = route === activeRoute ? " active" : "";
  return `<a class="tabbar-item${active}" href="#${route}">${label}</a>`;
}
