export function renderMapPage(): string {
  return `
    <section class="map-page">
      <div id="map" class="map-container">
        <div class="map-placeholder">
          Easymap + Cesium container
          <span>APP-A3 建立容器；APP-A5 接 job marker 與 placement display。</span>
        </div>
      </div>
      <a class="record-fab" href="#capture">錄影</a>
    </section>
  `;
}
