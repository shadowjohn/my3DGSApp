export function renderSettingsPage(): string {
  return `
    <header class="page-header">
      <h1>設定</h1>
      <p>Studio mobile API token</p>
    </header>
    <section class="panel form-panel">
      <label>Server URL <input value="https://3wa.tw/demo/php/map/3D/gaussian_splat" /></label>
      <label>API Token <input type="password" placeholder="m3d_xxxxxxxxxxxxxxxxx" /></label>
      <button class="primary-action" type="button">儲存設定</button>
      <p class="muted">v0.1 native SecureToken 先以 interface + dev stub 表示，後續接 Keychain / Keystore。</p>
    </section>
  `;
}
