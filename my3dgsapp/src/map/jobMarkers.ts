import type { StudioJob } from "../models/StudioJob";

export interface JobMarker {
  id: number;
  title: string;
  lon: number;
  lat: number;
  status: string;
}

export function toJobMarkers(jobs: StudioJob[]): JobMarker[] {
  return jobs
    .filter((job) => Boolean(job.placement))
    .map((job) => ({
      id: job.studio_job_id,
      title: job.title,
      lon: job.placement!.lon,
      lat: job.placement!.lat,
      status: job.status
    }));
}
