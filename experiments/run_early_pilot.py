"""Paired test of the student's threshold=8 against threshold=9."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import platform
import sys
import numpy as np
import scipy
import run_pilot as base
import run_tail_pilot as previous

ROOT = Path(__file__).resolve().parent
SEEDS = (2026111501, 2026111502, 2026111503, 2026111504, 2026111505)
METHODS = ('fixed128', 'fixed32', 'fixed128_tail32', 'fixed128_tail8')


def next_step(hits):
    return 32 if hits >= 8 else 128


def run_policy(labels, method, p_global, k=10, budget=5000):
    if method != 'fixed128_tail8':
        return previous.run_policy(labels, method, p_global, k, budget)
    if k != 10 or budget < 1 or len(labels) < budget or not 0 <= p_global <= 1:
        raise ValueError('Threshold 8 experiment requires k=10 and valid input')
    checked = hits = calls = tail_calls = 0
    while hits < k and checked < budget:
        target = min(budget, checked+next_step(hits))
        tail_calls += int(hits >= 8)
        hits += int(np.count_nonzero(labels[checked:target]))
        checked, calls = target, calls+1
    return {'full': int(hits >= k), 'returned': min(hits, k), 'checked': checked,
            'calls': calls, 'deficit': max(0, k-hits), 'tail_calls': tail_calls}


def main():
    out = ROOT/'results/pilot_v03'
    if out.exists() and any(out.iterdir()):
        raise SystemExit('Preserve existing results; use a new version for a new run.')
    hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
              ('run_early_pilot.py', 'run_tail_pilot.py', 'run_pilot.py', 'PROTOCOL_V03.md')}
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    rows, fingerprints = [], []
    for seed in SEEDS:
        for s, scenario in enumerate(base.SCENARIOS):
            for p, rate in enumerate(base.RATES):
                for q in range(100):
                    labels = base.generate_labels(seed, s, p, q)
                    positions = np.flatnonzero(labels)
                    rank = int(positions[9])+1 if len(positions) >= 10 else base.N+1
                    query_id = f'{seed}-{s}-{p}-{q}'
                    fingerprints.append({'query_id': query_id,
                        'labels_sha256': hashlib.sha256(np.packbits(labels).tobytes()).hexdigest()})
                    for method in METHODS:
                        r = run_policy(labels, method, float(labels.mean()))
                        assert r['full'] == int(rank <= base.BUDGET)
                        rows.append({'query_id': query_id, 'scenario': scenario,
                            'nominal_rate': rate, 'method': method, **r,
                            'kth_eligible_rank': rank if rank <= base.N else '',
                            'overscan': r['checked']-rank if r['full'] else ''})
    summary = []
    for scenario in base.SCENARIOS:
        for rate in base.RATES:
            for method in METHODS:
                group = [r for r in rows if r['scenario'] == scenario
                         and r['nominal_rate'] == rate and r['method'] == method]
                summary.append({'scenario': scenario, 'nominal_rate': rate,
                    'method': method, 'queries': len(group),
                    'full_rate': float(np.mean([r['full'] for r in group])),
                    'checked_mean': float(np.mean([r['checked'] for r in group])),
                    'checked_p95': float(np.quantile([r['checked'] for r in group], .95)),
                    'calls_mean': float(np.mean([r['calls'] for r in group])),
                    'tail_trigger_rate': float(np.mean([r['tail_calls'] > 0 for r in group]))})
    for name, values in [('per_query', rows), ('summary', summary), ('query_fingerprints', fingerprints)]:
        base.write_csv(out/f'{name}.csv', values)
    (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    manifest = {'stage': 'candidate simulation only', 'started_at_utc': started,
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__,
        'platform': platform.platform(), 'seeds': SEEDS, 'k': 10, 'n': base.N,
        'budget': base.BUDGET, 'threshold': 8, 'tail_batch': 32,
        'independent_queries': len(fingerprints), 'paired_observations': len(rows),
        'all_methods_same_fullness_per_query': True, 'source_sha256': hashes,
        'files_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.csv'))}}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'queries': len(fingerprints), 'observations': len(rows)}))
    for r in summary:
        if r['nominal_rate'] == .01:
            print(r)


if __name__ == '__main__':
    main()
