export function renderHomePage(): string {
  return `
    <header class="page-header">
      <h1>my3DGSAPP</h1>
      <p>Capture Companion for 3DGS Studio</p>
    </header>
    <section class="panel">
      <h2>最近掃描</h2>
      <p class="muted">尚未載入 jobs。APP-A2 接上 mobile API 後會顯示 token 底下的任務。</p>
      <a class="primary-action" href="#capture">開始拍攝 / 匯入 MP4</a>
    </section>
  `;
}
