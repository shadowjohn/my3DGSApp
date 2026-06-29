export function renderResultPage(): string {
  return `
    <header class="page-header">
      <h1>成果</h1>
      <p>Delivery / Compare Viewer</p>
    </header>
    <section class="panel">
      <a class="primary-action" href="#map">回到地圖</a>
      <p class="muted">viewerLinks 會產生 delivery.php 與 viewer_compare_splat_mesh.html 入口。</p>
    </section>
  `;
}
