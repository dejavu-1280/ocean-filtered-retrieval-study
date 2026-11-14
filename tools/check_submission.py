"""Read-only cross-checks of the submitted evidence and report tables."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import re
import numpy as np

root = Path(__file__).resolve().parent.parent
report = (root/'REPORT.md').read_text(encoding='utf-8')
observations = independent = 0
for v in ('01', '02', '03'):
    out = root/f'experiments/results/pilot_v{v}'
    manifest = json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    sources = manifest.get('source_sha256', {'PROTOCOL.md': manifest.get('protocol_sha256'),
                                           'run_pilot.py': manifest.get('code_sha256')})
    for name, digest in sources.items():
        assert hashlib.sha256((root/'experiments'/name).read_bytes()).hexdigest() == digest, name
    for name, digest in manifest['files_sha256'].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest() == digest, name
    with (out/'per_query.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    observations += len(rows)
    ids = {r['query_id'] for r in rows}
    independent += len(ids)
    assert len(ids) == 4500
    groups = defaultdict(list)
    for r in rows:
        assert 0 < int(r['checked']) <= 5000
        assert 0 <= int(r['returned']) <= 10
        assert int(r['full']) == int(int(r['returned']) == 10)
        if not r['method'].startswith('global_'):
            rank = int(r['kth_eligible_rank']) if r['kth_eligible_rank'] else 20001
            assert int(r['full']) == int(rank <= 5000)
        groups[(r['scenario'], float(r['nominal_rate']), r['method'])].append(r)
    summaries = json.loads((out/'summary.json').read_text(encoding='utf-8'))
    for summary in summaries:
        group = groups[(summary['scenario'], summary['nominal_rate'], summary['method'])]
        assert len(group) == summary['queries'] == 500
        for source, metric in [('full', 'full_rate'), ('checked', 'checked_mean'), ('calls', 'calls_mean')]:
            assert abs(float(np.mean([int(r[source]) for r in group]))-summary[metric]) < 1e-9
        assert abs(float(np.quantile([int(r['checked']) for r in group], .95))-summary['checked_p95']) < 1e-9
    if v == '03':
        for scenario, label in [('independent', '独立'), ('enriched', '前段富集'), ('depleted', '前段稀疏')]:
            for rate in (.002, .01, .05):
                cell = {r['method']: r for r in summaries if r['scenario'] == scenario and r['nominal_rate'] == rate}
                a, b = cell['fixed128_tail32'], cell['fixed128_tail8']
                line = f"| {label} | {rate:.1%} | {a['full_rate']:.1%} | {1-b['checked_mean']/a['checked_mean']:.2%} | {b['calls_mean']-a['calls_mean']:.3f} | {a['tail_trigger_rate']:.1%} | {b['tail_trigger_rate']:.1%} |"
                assert line in report, line
assert (independent, observations) == (13500, 67500)
for filename in ('REPORT.md', 'README.md', 'REQUIREMENTS_CHECK.md'):
    body = (root/filename).read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)', body):
        if not target.startswith(('https:', 'http:', '#')):
            assert (root/target.split('#')[0]).exists(), (filename, target)
for n in range(1, 8):
    assert re.search(r'^\['+str(n)+r'\] ', report, re.M)
chat = (root/'collaboration/chat.md').read_text(encoding='utf-8')
headers = re.findall(r'^## (\d+)\. (用户|AI 助手)(.*)$', chat, re.M)
meta = json.loads((root/'collaboration/export_manifest.json').read_text(encoding='utf-8'))
assert len(headers) == meta['message_count']
assert [int(h[0]) for h in headers] == list(range(1, len(headers)+1))
assert all(not h[2] for h in headers)
assert '导出时间（UTC）' not in chat
assert meta['timestamp_fields_exported'] is False
assert '姓名：柴叶航' in report and '学号：22634127' in report
assert 'https://github.com/dejavu-1280/ocean-filtered-retrieval-study' in report[:700]
print(json.dumps({'independent_queries': independent, 'observations': observations,
    'all_frozen_hashes': 'match', 'all_summary_means_and_p95': 'match raw CSV',
    'nine_report_rows': 'match', 'reference_entries': 7,
    'chat_messages': len(headers), 'chat_time_labels': 'absent',
    'report_readme_checklist_links': 'valid'}, ensure_ascii=False, indent=2))
