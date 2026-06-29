import type { Placement } from "../models/Placement";

export interface PlacementTransform {
  position: [number, number, number];
  scale: number;
  rotationDegrees: {
    heading: number;
    pitch: number;
    roll: number;
  };
}

export function toPlacementTransform(placement: Placement): PlacementTransform {
  return {
    position: [placement.lon, placement.lat, placement.height_m],
    scale: placement.scale,
    rotationDegrees: {
      heading: placement.heading_deg ?? placement.rotation_deg ?? 0,
      pitch: placement.pitch_deg ?? 0,
      roll: placement.roll_deg ?? 0
    }
  };
}
