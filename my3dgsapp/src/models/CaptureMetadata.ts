export interface CaptureMetadata {
  schema_version: "1.0";
  app: {
    name: "my3DGSAPP";
    version: string;
  };
  device: {
    platform: "ios" | "android" | "web";
    model: string;
    os_version: string;
  };
  capture: {
    mode: "qa";
    media_type: "video";
    duration_sec: number;
    width: number;
    height: number;
    fps: number;
    orientation: "portrait" | "landscape" | "unknown";
    recorded_at: string;
  };
  quality_hints: {
    blur_warning: boolean;
    low_light_warning: boolean;
    motion_too_fast_warning: boolean;
    too_short_warning: boolean;
    coverage_hint: "unknown" | "poor" | "ok" | "good";
  };
  notes: {
    user_title: string;
    user_note: string;
  };
}
