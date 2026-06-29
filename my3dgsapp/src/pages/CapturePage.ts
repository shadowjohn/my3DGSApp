export function renderCapturePage(): string {
  return `
    <header class="page-header">
      <h1>拍攝 / 匯入</h1>
      <p>QA Scan only</p>
    </header>
    <section class="panel">
      <h2>拍攝指引</h2>
      <ul class="checklist">
        <li>繞物體或場景慢慢移動</li>
        <li>保持畫面穩定，避免快速晃動</li>
        <li>避免過暗、反光、透明與大面積純色</li>
        <li>建議影片長度 20-60 秒</li>
      </ul>
      <label class="file-picker">
        選擇 MP4
        <input type="file" accept="video/mp4,video/*" />
      </label>
    </section>
  `;
}
