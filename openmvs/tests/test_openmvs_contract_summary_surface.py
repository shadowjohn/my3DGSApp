import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def php_eval(code: str) -> str:
    return subprocess.run(["php", "-r", code], cwd=ROOT, text=True, capture_output=True, check=True).stdout


def test_validation_summary_lines_are_chinese():
    code = '''
require "job_view.php";
$lines = ovm_contract_summary_lines([
  "decision"=>["status"=>"deliverable","root_cause"=>"unknown","summary"=>"OpenMVS Fast output is deliverable.","grade"=>"A"]
], []);
echo implode("\\n", $lines);
'''
    html = php_eval(code)

    assert "Validation 可交付 / A" in html
    assert "來源：未知" in html
    assert "OpenMVS Fast output is deliverable." in html


def test_failure_summary_lines_are_chinese():
    code = '''
require "job_view.php";
$lines = ovm_contract_summary_lines([], [
  "root_cause"=>"capture",
  "failed_stage"=>"colmap_mapper",
  "retryable"=>false,
  "recapture_recommended"=>true,
  "recommendations"=>["補拍更多重疊影像"],
  "diagnostic_warnings"=>["openmvs.nonzero_exit failed"]
]);
echo implode("\\n", $lines);
'''
    html = php_eval(code)

    assert "Failure 拍攝問題" in html
    assert "失敗階段 colmap_mapper" in html
    assert "建議補拍" in html
    assert "補拍更多重疊影像" in html
    assert "openmvs.nonzero_exit failed" in html


def test_existing_validation_summary_is_visible_in_quality_cell():
    html = php_eval('require "job_view.php"; echo ovm_job_quality_cell_html(["id"=>8]);')
    assert "Validation 可交付" in html


def test_long_diagnostic_summary_is_collapsed_in_quality_cell():
    code = '''
require "job_view.php";
$long = str_repeat("OpenMVS very long diagnostic message ", 12) . "TAIL_SHOULD_ONLY_BE_IN_DIALOG";
echo ovm_job_quality_cell_html(["id"=>23, "diagnostic_summary"=>$long]);
'''
    html = php_eval(code)

    assert "詳細" in html
    assert "openDiagnosticsDialog(23)" in html
    assert "TAIL_SHOULD_ONLY_BE_IN_DIALOG" not in html


def test_long_validation_summary_is_collapsed_in_quality_cell():
    code = '''
require "job_view.php";
$lines = ovm_contract_summary_lines([
  "decision"=>[
    "status"=>"engine_failed",
    "root_cause"=>"engine",
    "summary"=>str_repeat("[env-check] OpenMVS pipeline mode ", 12) . "VALIDATION_TAIL_SHOULD_ONLY_BE_IN_DIALOG",
    "grade"=>"D"
  ]
], []);
echo ovm_contract_summary_html($lines, 23);
'''
    html = php_eval(code)

    assert "Validation 引擎失敗 / D" in html
    assert "詳細" in html
    assert "openDiagnosticsDialog(23)" in html
    assert "VALIDATION_TAIL_SHOULD_ONLY_BE_IN_DIALOG" not in html
