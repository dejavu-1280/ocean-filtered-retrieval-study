"""v0.2: test a student's tail-shrink direction, with AI-specified batch=32."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import platform
import sys
import numpy as np
import scipy
import run_pilot as base

ROOT = Path(__file__).resolve().parent
SEEDS = (2026111401, 2026111402, 2026111403, 2026111404, 2026111405)
TAIL = 32
METHODS = ('fixed128', 'fixed32', 'fixed128_tail32', 'doubling',
           'adaptive_v01', 'adaptive_tail32')


def next_target(method, observed, p_global, k, budget, last_batch):
    checked = len(observed)
    if method == 'fixed32':
        return min(budget, checked+TAIL)
    mapping = {'fixed128': 'fixed_batch', 'fixed128_tail32': 'fixed_batch',
               'doubling': 'doubling', 'adaptive_v01': 'adaptive',
               'adaptive_tail32': 'adaptive'}
    if method not in mapping:
        raise ValueError(method)
    target = base.next_target(mapping[method], observed, p_global, k, budget, last_batch)
    if method.endswith('_tail32') and checked and np.count_nonzero(observed) == k-1:
        target = min(target, checked+TAIL)
    return target


def run_policy(labels, method, p_global, k=base.K, budget=base.BUDGET):
    if k < 1 or budget < 1 or not 0 <= p_global <= 1 or len(labels) < budget:
        raise ValueError('Invalid k, budget, probability, or sequence length')
    checked = calls = hits = last_batch = tail_calls = 0
    while hits < k and checked < budget:
        # Policy receives only observed labels and permitted global metadata.
        target = next_target(method, labels[:checked], p_global, k, budget, last_batch)
        assert checked < target <= budget
        tail_calls += int(method.endswith('_tail32') and checked > 0 and hits == k-1)
        last_batch = target-checked
        hits += int(np.count_nonzero(labels[checked:target]))
        checked, calls = target, calls+1
    return {'full': int(hits >= k), 'returned': min(hits, k), 'checked': checked,
            'calls': calls, 'deficit': max(0, k-hits), 'tail_calls': tail_calls}


def aggregate(rows):
    summary = []
    for scenario in base.SCENARIOS:
        for rate in base.RATES:
            for method in METHODS:
                group = [r for r in rows if r['scenario'] == scenario
                         and r['nominal_rate'] == rate and r['method'] == method]
                overscan = [r['overscan'] for r in group if r['full']]
                summary.append({'scenario': scenario, 'nominal_rate': rate, 'method': method,
                                'queries': len(group),
                                'full_rate': float(np.mean([r['full'] for r in group])),
                                'checked_mean': float(np.mean([r['checked'] for r in group])),
                                'checked_p95': float(np.quantile([r['checked'] for r in group], .95)),
                                'calls_mean': float(np.mean([r['calls'] for r in group])),
                                'overscan_success_mean': float(np.mean(overscan)) if overscan else None,
                                'tail_trigger_rate': float(np.mean([r['tail_calls'] > 0 for r in group])),
                                'deficit_mean': float(np.mean([r['deficit'] for r in group]))})
    return summary


def main():
    out = ROOT/'results'/'pilot_v02'
    if out.exists() and any(out.iterdir()):
        raise SystemExit('Output already exists; preserve it and choose a new version directory.')
    hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
              for name in ('run_tail_pilot.py', 'run_pilot.py', 'PROTOCOL_V02.md')}
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    rows, fingerprints = [], []
    for seed in SEEDS:
        for s, scenario in enumerate(base.SCENARIOS):
            for p, rate in enumerate(base.RATES):
                for query in range(100):
                    labels = base.generate_labels(seed, s, p, query)
                    positions = np.flatnonzero(labels)
                    rank = int(positions[base.K-1])+1 if len(positions) >= base.K else base.N+1
                    actual_rate = float(labels.mean())
                    query_id = f'{seed}-{s}-{p}-{query}'
                    fingerprints.append({'query_id': query_id,
                                         'labels_sha256': hashlib.sha256(np.packbits(labels).tobytes()).hexdigest()})
                    for method in METHODS:
                        result = run_policy(labels, method, actual_rate)
                        assert result['full'] == int(rank <= base.BUDGET)
                        rows.append({'query_id': query_id, 'seed': seed, 'scenario': scenario,
                                     'nominal_rate': rate, 'actual_global_rate': actual_rate,
                                     'method': method, **result,
                                     'kth_eligible_rank': rank if rank <= base.N else '',
                                     'overscan': result['checked']-rank if result['full'] else ''})
    summary = aggregate(rows)
    base.write_csv(out/'per_query.csv', rows)
    base.write_csv(out/'summary.csv', summary)
    base.write_csv(out/'query_fingerprints.csv', fingerprints)
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    manifest = {'stage': 'candidate-prefix simulation only; not ocean or ANN latency evidence',
                'started_at_utc': started, 'completed_at_utc': datetime.now(timezone.utc).isoformat(),
                'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__,
                'platform': platform.platform(), 'seeds': SEEDS, 'tail_batch': TAIL,
                'k': base.K, 'n': base.N, 'budget': base.BUDGET,
                'independent_queries': len(fingerprints), 'paired_policy_observations': len(rows),
                'all_methods_same_fullness_per_query': True, 'source_sha256': hashes,
                'files_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted(out.glob('*.csv'))}}
    (out/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'queries': len(fingerprints), 'observations': len(rows), 'output': str(out)}, ensure_ascii=False))
    for r in summary:
        if r['nominal_rate'] == .01:
            print(f"{r['scenario']:12} {r['method']:20} full={r['full_rate']:.3f} "
                  f"checks={r['checked_mean']:.3f} calls={r['calls_mean']:.3f} tail={r['tail_trigger_rate']:.3f}")


if __name__ == '__main__':
    main()
