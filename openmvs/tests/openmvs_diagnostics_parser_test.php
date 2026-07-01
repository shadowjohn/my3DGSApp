<?php
require __DIR__ . '/../crontab/inc/function.php';

function assert_true($condition, $message){
    if(!$condition){
        fwrite(STDERR, $message . PHP_EOL);
        exit(1);
    }
}

$log = implode("\n", [
    "[timing] START openmvs_refine OpenMVS mesh refinement",
    "RefineMesh: linear solver failed to converge",
    "RefineMesh: linear solver failed to converge",
    "[env-check] RefineMesh GPU stage failed; retrying with CPU",
    "[timing] START openmvs_texture OpenMVS mesh texturing",
    "TextureMesh: rejected texture patch because no valid view",
    "TextureMesh: rejected texture patch because no valid view",
    "TextureMesh: rejected texture patch because no valid view",
    "missing scene_dense.mvs",
]) . "\n";

$diagnostics = ovm_parse_log_diagnostics($log, 'uploads/42/logs/openmvs_pipeline.log');
$byKey = [];
foreach($diagnostics as $row){
    $byKey[$row['stage'] . '|' . $row['pattern_id']] = $row;
}

assert_true($byKey['openmvs_refine|openmvs.linear_solver_failure']['pattern_count'] === 2, 'linear solver count');
assert_true($byKey['openmvs_refine|openmvs.cpu_fallback']['pattern_count'] === 1, 'cpu fallback count');
assert_true($byKey['openmvs_texture|openmvs.texture_patch_rejected']['pattern_count'] === 3, 'texture patch count');
assert_true($byKey['openmvs_texture|openmvs.missing_scene']['severity'] === 'error', 'missing scene severity');
assert_true($byKey['openmvs_texture|openmvs.missing_scene']['first_seen_line'] === 9, 'line number');
assert_true(strpos($byKey['openmvs_refine|openmvs.linear_solver_failure']['message_sample'], 'linear solver') !== false, 'sample');
assert_true(explode('.', $byKey['openmvs_refine|openmvs.linear_solver_failure']['pattern_id'], 2)[0] === 'openmvs', 'alias category source');
assert_true($byKey['openmvs_refine|openmvs.linear_solver_failure']['pattern_id'] === 'openmvs.linear_solver_failure', 'alias code source');
assert_true($byKey['openmvs_refine|openmvs.linear_solver_failure']['message_summary'] === 'Linear solver failures', 'alias message source');
assert_true($byKey['openmvs_refine|openmvs.linear_solver_failure']['raw_log_path'] === 'uploads/42/logs/openmvs_pipeline.log', 'alias source path source');

$createStructureDiagnostics = ovm_parse_log_diagnostics(implode("\n", [
    "[timing] START openmvs_create_structure OpenMVS native SfM (GPU)",
    "Linear solver failure. Failed to compute a step: Eigen failure.",
    "[timing] END openmvs_create_structure success",
]) . "\n", 'uploads/42/logs/openmvs_pipeline.log');
assert_true($createStructureDiagnostics[0]['severity'] === 'warning', 'successful CreateStructure linear solver warning');

$qaDiagnostics = ovm_parse_log_diagnostics("openmvs.qa_report_missing qa_report.json missing\n", 'uploads/42/logs/openmvs_pipeline.log');
assert_true($qaDiagnostics[0]['pattern_id'] === 'openmvs.qa_report_missing', 'qa missing pattern');
assert_true($qaDiagnostics[0]['severity'] === 'warning', 'qa missing warning');

assert_true(ovm_capture_source_type('zip') === 'images', 'zip capture source');
assert_true(ovm_capture_source_type('mp4') === 'video', 'mp4 capture source');
assert_true(ovm_capture_source_type('mov') === null, 'unknown capture source');
assert_true(ovm_capture_quality_from_ratio(null, 0) === [null, null, null], 'unknown capture quality');

[, $grade, $decision] = ovm_capture_quality_from_ratio(0.95, 0);
assert_true($grade === 'A' && $decision === 'run', 'A capture quality');
[, $grade, $decision] = ovm_capture_quality_from_ratio(0.65, 0);
assert_true($grade === 'C' && $decision === 'warn', 'C capture quality');
[, $grade, $decision] = ovm_capture_quality_from_ratio(0.45, 0);
assert_true($grade === 'D' && $decision === 'hold', 'D capture quality');
[, $grade, $decision] = ovm_capture_quality_from_ratio(0.20, 0);
assert_true($grade === 'F' && $decision === 'reject', 'F capture quality');

$emptyCapture = ovm_capture_summary_fields([], [], []);
assert_true($emptyCapture['capture_source_type'] === null, 'empty source stays null');
assert_true($emptyCapture['capture_preset'] === null, 'empty preset stays null');
assert_true($emptyCapture['capture_mask_status'] === null, 'empty mask stays null');

$capture = ovm_capture_summary_fields(
    ['kind'=>'zip', 'capture_preset'=>'normal_orbit', 'mask_mode'=>'auto'],
    ['input_frame_count'=>20, 'registered_frame_count'=>15],
    [['severity'=>'warning', 'pattern_count'=>1]]
);
assert_true($capture['capture_source_type'] === 'images', 'capture source from kind');
assert_true($capture['capture_preset'] === 'normal_orbit', 'capture preset from row');
assert_true($capture['capture_mask_status'] === 'auto', 'capture mask from row');
assert_true($capture['capture_frame_count'] === 20, 'capture frame count');
assert_true($capture['capture_selected_frame_count'] === 20, 'capture selected frame count');
assert_true($capture['capture_aligned_camera_count'] === 15, 'capture aligned count');
assert_true($capture['capture_registered_ratio'] === '0.7500', 'capture ratio format');
assert_true($capture['capture_warning_count'] === 1, 'capture warning count');
assert_true($capture['capture_quality_score'] === '70.00', 'capture warning penalty');
assert_true($capture['capture_quality_grade'] === 'C', 'capture warning grade');
assert_true($capture['capture_quality_decision'] === 'warn', 'capture warning decision');

echo "ok\n";
