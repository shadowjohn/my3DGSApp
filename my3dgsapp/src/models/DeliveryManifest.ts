import type { Placement } from "./Placement";

export interface DeliveryManifest {
  schema_version: "1.0";
  studio_job_id: number;
  delivery_url: string;
  compare_url: string;
  placement?: Placement;
}
