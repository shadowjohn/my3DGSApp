const TOKEN_KEY = "my3dgsapp.mobile_api_token";
const SERVER_URL_KEY = "my3dgsapp.server_url";

export interface SecureTokenStore {
  getToken(): Promise<string | null>;
  setToken(token: string): Promise<void>;
  removeToken(): Promise<void>;
  getServerUrl(): Promise<string | null>;
  setServerUrl(serverUrl: string): Promise<void>;
}

export class DevSecureTokenStore implements SecureTokenStore {
  async getToken(): Promise<string | null> {
    return localStorage.getItem(TOKEN_KEY);
  }

  async setToken(token: string): Promise<void> {
    localStorage.setItem(TOKEN_KEY, token);
  }

  async removeToken(): Promise<void> {
    localStorage.removeItem(TOKEN_KEY);
  }

  async getServerUrl(): Promise<string | null> {
    return localStorage.getItem(SERVER_URL_KEY);
  }

  async setServerUrl(serverUrl: string): Promise<void> {
    localStorage.setItem(SERVER_URL_KEY, serverUrl);
  }
}
