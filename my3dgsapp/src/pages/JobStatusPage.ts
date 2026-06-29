export function renderJobStatusPage(): string {
  return `
    <header class="page-header">
      <h1>任務狀態</h1>
      <p>QA pipeline stages</p>
    </header>
    <section class="panel status-list">
      <div>等待處理</div>
      <div>品質檢查</div>
      <div>3D 重建中</div>
      <div>Gaussian 診斷中</div>
      <div>產生交付結果</div>
    </section>
  `;
}
