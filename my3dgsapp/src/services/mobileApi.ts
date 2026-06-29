import type { CaptureMetadata } from "../models/CaptureMetadata";
import type { StudioJob } from "../models/StudioJob";
import type { UploadSession } from "../models/UploadSession";
import type { SecureTokenStore } from "./secureToken";

export class MobileApiClient {
  constructor(private readonly tokenStore: SecureTokenStore) {}

  async createUploadSession(input: { file_name: string; file_size: number; mime_type: string; sha256?: string }): Promise<UploadSession> {
    return this.post("create_upload_session", input);
  }

  async uploadChunk(uploadId: string, offset: number, chunk: Blob): Promise<UploadSession> {
    const baseUrl = await this.requireServerUrl();
    const token = await this.requireToken();
    const url = `${baseUrl}/studio/mobile_api.php?mode=upload_chunk&upload_id=${encodeURIComponent(uploadId)}&offset=${encodeURIComponent(offset)}`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Device-Id": getDeviceId(),
        "X-App-Version": "0.1.0",
        "Content-Type": "application/octet-stream"
      },
      body: chunk
    });
    return readJson<UploadSession>(response);
  }

  async uploadStatus(uploadId: string): Promise<UploadSession> {
    return this.get(`upload_status&upload_id=${encodeURIComponent(uploadId)}`);
  }

  async finalizeUpload(
    uploadId: string,
    metadata: CaptureMetadata
  ): Promise<{ upload_id: string; status: "finalized"; upload_manifest_path: string; next_action: string }> {
    return this.post("finalize_upload", { upload_id: uploadId, metadata });
  }

  async createQaJobFromUpload(
    uploadId: string,
    title: string,
    note = ""
  ): Promise<{ upload_id: string; studio_job_id: number; mode: "qa"; status: "pending"; next_worker: string }> {
    return this.post("create_qa_job_from_upload", { upload_id: uploadId, title, note });
  }

  async jobDetail(studioJobId: number): Promise<StudioJob> {
    return this.get(`job_detail&id=${encodeURIComponent(studioJobId)}`);
  }

  async myJobs(): Promise<{ jobs: StudioJob[] }> {
    return this.get("my_jobs");
  }

  private async post<T>(mode: string, body: unknown): Promise<T> {
    const baseUrl = await this.requireServerUrl();
    const token = await this.requireToken();
    const response = await fetch(`${baseUrl}/studio/mobile_api.php?mode=${mode}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Device-Id": getDeviceId(),
        "X-App-Version": "0.1.0",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    });
    return readJson<T>(response);
  }

  private async get<T>(mode: string): Promise<T> {
    const baseUrl = await this.requireServerUrl();
    const token = await this.requireToken();
    const response = await fetch(`${baseUrl}/studio/mobile_api.php?mode=${mode}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Device-Id": getDeviceId(),
        "X-App-Version": "0.1.0"
      }
    });
    return readJson<T>(response);
  }

  private async requireServerUrl(): Promise<string> {
    const serverUrl = await this.tokenStore.getServerUrl();
    if (!serverUrl) throw new Error("server_url is not configured");
    return serverUrl.replace(/\/+$/, "");
  }

  private async requireToken(): Promise<string> {
    const token = await this.tokenStore.getToken();
    if (!token) throw new Error("mobile API token is not configured");
    return token;
  }
}

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return payload as T;
}

function getDeviceId(): string {
  const key = "my3dgsapp.device_id";
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const value = `web-${crypto.randomUUID()}`;
  localStorage.setItem(key, value);
  return value;
}
