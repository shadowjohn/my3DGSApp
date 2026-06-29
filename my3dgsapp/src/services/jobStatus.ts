import type { StudioJob, StudioJobStatus } from "../models/StudioJob";

export function getJobLabel(job: StudioJob): string {
  return statusLabels[job.status] || "處理中";
}

const statusLabels: Record<StudioJobStatus, string> = {
  pending: "等待處理",
  preflight: "品質檢查",
  running_openmvs: "3D 重建中",
  running_gaussian: "Gaussian 診斷中",
  aggregating: "產生交付結果",
  completed: "完成",
  partial_failed: "部分完成",
  failed: "失敗"
};
