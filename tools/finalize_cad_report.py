"""Compare stage 2B with the validated stage 2 checkpoint and verify provenance."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'backups/stage2_validated'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def main():
    core=read(ROOT/'docs/validation_report.json');old=read(BASE/'docs/validation_report.json')
    cad=read(ROOT/'docs/cad_visual_validation.json');scan=read(ROOT/'docs/scan_visual_validation.json')
    guard=read(ROOT/'cad/reports/kinematic_invariants.json')
    protected=read(ROOT/'cad/reports/stage2b_protected_assets.json')
    protected_results={path:sha(ROOT/path)==digest for path,digest in protected.items()}
    backup_results={}
    for name in ('stage1_validated','stage2_validated'):
        directory=ROOT/'backups'/name
        manifest=read(directory/'checkpoint_manifest.json')['files']
        backup_results[name]={path:(directory/path).is_file() and sha(directory/path)==digest
                              for path,digest in manifest.items()}
    core_files=['controllers/cartesian_controller/cartesian_controller.py',
                'controllers/cartesian_controller/runtime.ini','config/robot_parameters.json']
    core_results={path:sha(ROOT/path)==sha(BASE/path) for path in core_files}
    source_results={}
    for name in ('beckhoff_research.json','rexroth_research.json','ax5203_research.json'):
        report=ROOT/'cad/reports'/name
        if not report.exists():continue
        for asset in read(report).get('assets',[]):
            path=asset.get('file',asset.get('path'))
            if path and asset.get('sha256'):
                path=path.replace('\\','/')
                source_results[path]=(ROOT/path).is_file() and sha(ROOT/path)==asset['sha256'].lower()
    source_manifest_results={}
    for asset in read(ROOT/'cad/reports/cad_sources.json')['assets']:
        path=asset['file'].replace('\\','/')
        source_manifest_results[path]=(ROOT/path).is_file() and sha(ROOT/path)==asset['sha256'].lower()
    source_manifest_complete=set(source_results).issubset(source_manifest_results)
    config=read(ROOT/'config/cad_integration.json')
    validated={resource['path']:resource['sha256'] for check in cad['checks']
               if check['name'].startswith('cad_resource_') for resource in check['details']['resources']}
    current_assets={mesh['path']:sha(ROOT/mesh['path']) for part in config['parts'] if part['enabled']
                    for mesh in part['meshes']}
    assets_unchanged=current_assets==validated
    metrics={name:{'stage2':value,'stage2b':core['continuous_metrics'][name],
                   'delta':core['continuous_metrics'][name]-value}
             for name,value in old['continuous_metrics'].items()}
    log_names=['validation_webots_stdout.log','validation_webots_stderr.log',
               'cad_visual_webots_stdout.log','cad_visual_webots_stderr.log',
               'scan_visual_webots_stdout.log','scan_visual_webots_stderr.log']
    logs={}
    for name in log_names:
        path=ROOT/'docs'/name
        logs[name]={'bytes':path.stat().st_size,'warning_error_lines':[line for line in path.read_text(encoding='utf-8-sig').splitlines()
                    if re.search(r'\b(?:WARNING|ERROR|OpenGL error)\b|Traceback',line,re.I)]}
    expected_checks=[c['name'] for c in core['checks']]==[c['name'] for c in old['checks']]
    passed=(core['passed'] and cad['passed'] and scan['passed'] and guard['passed']
            and len(core['checks'])==23 and expected_checks
            and all(protected_results.values()) and all(core_results.values()) and all(source_results.values())
            and all(source_manifest_results.values()) and source_manifest_complete
            and all(all(files.values()) for files in backup_results.values())
            and assets_unchanged and all(value['delta']==0 for value in metrics.values())
            and not any(log['warning_error_lines'] for log in logs.values()))
    result={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'passed':passed,
            'baseline':'backups/stage2_validated','core_checks':len(core['checks']),
            'cad_checks':len(cad['checks']),'scan_checks':len(scan['checks']),
            'static_checks':len(guard['checks']),'core_check_names_unchanged':expected_checks,
            'core_files_byte_identical':core_results,'protected_assets_unchanged':protected_results,
            'backup_files_unchanged':backup_results,
            'source_cad_hashes_unchanged':source_results,'validated_cad_meshes_unchanged':assets_unchanged,
            'source_manifest_hashes_correct':source_manifest_results,
            'source_manifest_covers_downloads':source_manifest_complete,
            'continuous_metrics_comparison':metrics,'simulation_time_s':core['simulation_time_s'],
            'simulation_time_unchanged':core['simulation_time_s']==old['simulation_time_s'],
            'logs':logs,'regressions_detected':not passed}
    write(ROOT/'cad/reports/regression_comparison.json',result)
    baseline_manifest=read(BASE/'checkpoint_manifest.json')['files']
    changes=[]
    for folder in ('cad','config','controllers','docs','meshes','protos','tools','worlds'):
        for path in (ROOT/folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:continue
            relative=path.relative_to(ROOT).as_posix()
            if relative=='cad/reports/change_manifest.json':continue
            digest=sha(path)
            if baseline_manifest.get(relative)!=digest:
                changes.append({'path':relative,'status':'created' if relative not in baseline_manifest else 'modified',
                                'bytes':path.stat().st_size,'sha256':digest})
    for path in (ROOT/'README.md',ROOT/'blender/official_cad_components.blend'):
        relative=path.relative_to(ROOT).as_posix()
        changes.append({'path':relative,'status':'created' if relative not in baseline_manifest else 'modified',
                        'bytes':path.stat().st_size,'sha256':sha(path)})
    write(ROOT/'cad/reports/change_manifest.json',{'scope':'Stage 2B artifacts, excludes this manifest, backups, local packages and Python caches',
          'git_state':'No Git repository initialized','files':sorted(changes,key=lambda entry:entry['path'])})
    print(json.dumps({'passed':passed,'core_checks':len(core['checks']),'cad_checks':len(cad['checks']),
                      'scan_checks':len(scan['checks']),'all_metric_deltas_zero':all(v['delta']==0 for v in metrics.values()),
                      'all_protected_assets_unchanged':all(protected_results.values()),'changes':len(changes)}))
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
