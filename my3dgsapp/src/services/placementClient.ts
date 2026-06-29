import type { Placement } from "../models/Placement";
import type { StudioJob } from "../models/StudioJob";

export function getServerPlacement(job: StudioJob): Placement | null {
  return job.placement || null;
}
