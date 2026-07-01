from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
SIBLING_JPGTOGLB = PROJECT_ROOT.parent / "jpgtoglb"
SAMPLE_MP4 = SIBLING_JPGTOGLB / "uploads" / "2" / "2.mp4"
SAMPLE_MP4_ALT = SIBLING_JPGTOGLB / "uploads" / "7" / "7.mp4"
SAMPLE_ZIP = SIBLING_JPGTOGLB / "uploads" / "1" / "1.zip"
