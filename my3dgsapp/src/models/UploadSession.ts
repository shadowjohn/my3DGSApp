export type UploadStatus = "created" | "uploading" | "finalized" | "job_created" | "failed" | "expired";

export interface UploadSession {
  upload_id: string;
  status: UploadStatus;
  file_size?: number;
  received_bytes?: number;
  next_offset: number;
  chunk_size?: number;
}
