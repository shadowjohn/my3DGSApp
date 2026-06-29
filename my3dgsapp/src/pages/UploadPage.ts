export function renderUploadPage(): string {
  return `
    <header class="page-header">
      <h1>上傳</h1>
      <p>Offset chunk upload</p>
    </header>
    <section class="panel">
      <div class="progress"><span style="width: 0%"></span></div>
      <p class="muted">上傳期間請保持 App 開啟；中斷後可重新開啟續傳。</p>
    </section>
  `;
}
