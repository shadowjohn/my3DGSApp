import type { CaptureMetadata } from "../models/CaptureMetadata";
import type { UploadSession } from "../models/UploadSession";
import type { MobileApiClient } from "./mobileApi";

export interface UploadProgress {
  uploadId: string;
  sentBytes: number;
  totalBytes: number;
  percent: number;
}

export class UploadClient {
  constructor(private readonly api: MobileApiClient) {}

  async uploadMp4(file: File, metadata: CaptureMetadata, onProgress: (progress: UploadProgress) => void): Promise<UploadSession> {
    let session = await this.api.createUploadSession({
      file_name: file.name || "source.mp4",
      file_size: file.size,
      mime_type: file.type || "video/mp4"
    });
    const chunkSize = session.chunk_size || 8 * 1024 * 1024;

    while (session.next_offset < file.size) {
      const nextOffset = session.next_offset;
      const chunk = file.slice(nextOffset, Math.min(nextOffset + chunkSize, file.size));
      session = await this.api.uploadChunk(session.upload_id, nextOffset, chunk);
      const sentBytes = session.received_bytes || session.next_offset;
      onProgress({
        uploadId: session.upload_id,
        sentBytes,
        totalBytes: file.size,
        percent: Math.round((sentBytes / file.size) * 100)
      });
    }

    await this.api.finalizeUpload(session.upload_id, metadata);
    return { ...session, status: "finalized", received_bytes: file.size, next_offset: file.size, chunk_size: chunkSize };
  }
}
