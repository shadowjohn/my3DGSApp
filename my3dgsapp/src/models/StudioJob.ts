import type { Placement } from "./Placement";

export type StudioJobStatus =
  | "pending"
  | "preflight"
  | "running_openmvs"
  | "running_gaussian"
  | "aggregating"
  | "completed"
  | "partial_failed"
  | "failed";

export interface StudioJob {
  studio_job_id: number;
  title: string;
  mode: "qa";
  status: StudioJobStatus;
  app_stage: string;
  created_at: string;
  confidence_level?: string;
  placement?: Placement;
  viewer_urls?: {
    delivery: string;
    compare: string;
  };
}
