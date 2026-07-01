from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_cron_and_final_smoke_paths():
    text = (ROOT / "README.md").read_text()

    assert "## Cron" in text
    assert "php crontab/1_run.php" in text
    assert "*/1 * * * * cd /var/www/html/demo/php/map/3D/gaussian_splat/crontab && ./1min.sh" in text
    assert "uploads/final-smoke" in text
    assert "scripts/run_mvp_pipeline.sh /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4 uploads/final-smoke" in text
    assert "viewer_splat.php?src=uploads/final-smoke/exports/splat.ply" in text
