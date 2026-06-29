export type PlacementSource = "server_adjusted" | "manual" | "estimated";

export interface Placement {
  lon: number;
  lat: number;
  height_m: number;
  scale: number;
  rotation_deg?: number;
  heading_deg?: number;
  pitch_deg?: number;
  roll_deg?: number;
  source: PlacementSource;
  updated_at: string;
}
