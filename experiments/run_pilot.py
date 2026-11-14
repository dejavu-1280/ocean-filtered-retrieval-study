"""Paired candidate-prefix simulation; NOT an ANN/database latency benchmark."""
from pathlib import Path
from datetime import datetime, timezone
from functools import lru_cache
import csv
import hashlib
import json
import math
import platform
import sys
import numpy as np
import scipy
from scipy.stats import binom

ROOT = Path(__file__).resolve().parent
K, N, BUDGET = 10, 20000, 5000
PILOT, MIN_BATCH, PRIOR, SAFETY = 128, 32, 20, 1.2
METHODS = ('global_mean', 'global_iid95', 'fixed_batch', 'doubling', 'adaptive')
ITERATIVE = ('fixed_batch', 'doubling', 'adaptive')
SEEDS = (271828, 314159, 161803, 141421, 173205)
RATES = (0.002, 0.01, 0.05)
SCENARIOS = ('independent', 'enriched', 'depleted')


@lru_cache(maxsize=100000)
def iid_target(k, p, budget):
    """Smallest binomial 95% target, clipped to budget, with no guarantee at cap."""
    if p <= 0 or binom.sf(k-1, budget, p) < 0.95:
        return budget
    lo, hi = k, budget
    while lo < hi:
        mid = (lo+hi)//2
        if binom.sf(k-1, mid, p) >= 0.95:
            hi = mid
        else:
            lo = mid+1
    return lo


def next_target(method, observed, p_global, k, budget, last_batch):
    """Only observed prefix and permitted catalogue statistic enter this policy."""
    checked = len(observed)
    if checked == 0:
        if method == 'global_mean':
            return min(budget, max(1, math.ceil(k/p_global))) if p_global else budget
        if method == 'global_iid95':
            return iid_target(k, p_global, budget)
        return min(PILOT, budget)
    if method.startswith('global_'):
        return checked
    if method == 'fixed_batch':
        return min(budget, checked+PILOT)
    if method == 'doubling':
        return min(budget, checked*2)
    if method != 'adaptive':
        raise ValueError(method)
    hits = int(np.count_nonzero(observed))
    p_hat = (hits+PRIOR*p_global)/(checked+PRIOR)
    proposed = math.ceil(SAFETY*(k-hits)/max(p_hat, 1e-12))
    step = min(max(MIN_BATCH, proposed), max(MIN_BATCH, 2*last_batch))
    return min(budget, checked+step)


def run_policy(labels, method, p_global, k=K, budget=BUDGET):
    if k < 1 or budget < 1 or not 0 <= p_global <= 1:
        raise ValueError('Invalid k, budget, or probability')
    if len(labels) < budget:
        raise ValueError('Candidate sequence is shorter than budget')
    checked = calls = hits = last_batch = 0
    while hits < k and checked < budget:
        target = next_target(method, labels[:checked], p_global, k, budget, last_batch)
        if target == checked:
            break
        if not checked < target <= budget:
            raise AssertionError('Policy did not advance within the budget')
        last_batch = target-checked
        hits += int(np.count_nonzero(labels[checked:target]))
        checked, calls = target, calls+1
    return {'full': int(hits >= k), 'returned': min(hits, k),
            'checked': checked, 'calls': calls, 'deficit': max(0, k-hits)}


def generate_labels(seed, scenario_index, rate_index, query_index):
    rng = np.random.default_rng(np.random.SeedSequence([seed, scenario_index, rate_index, query_index]))
    p = RATES[rate_index]
    probabilities = np.full(N, p)
    mode = SCENARIOS[scenario_index]
    if mode == 'enriched':
        probabilities[:N//4], probabilities[N//4:] = p*2.8, p*0.4
    if mode == 'depleted':
        probabilities[:N//4], probabilities[N//4:] = p*0.2, p*(1-0.25*0.2)/0.75
    assert np.all((probabilities >= 0) & (probabilities <= 1))
    assert abs(float(probabilities.mean())-p) < 1e-12
    return rng.random(N) < probabilities


def aggregate(rows):
    result = []
    for scenario in SCENARIOS:
        for rate in RATES:
            for method in METHODS:
                group = [r for r in rows if r['scenario'] == scenario and r['nominal_rate'] == rate and r['method'] == method]
                overscan = [r['overscan'] for r in group if r['full']]
                result.append({'scenario': scenario, 'nominal_rate': rate, 'method': method, 'queries': len(group),
                               'full_rate': float(np.mean([r['full'] for r in group])),
                               'checked_mean': float(np.mean([r['checked'] for r in group])),
                               'checked_p95': float(np.quantile([r['checked'] for r in group], .95)),
                               'calls_mean': float(np.mean([r['calls'] for r in group])),
                               'overscan_success_mean': float(np.mean(overscan)) if overscan else None,
                               'deficit_mean': float(np.mean([r['deficit'] for r in group])),
                               'budget_feasible_rate': float(np.mean([r['budget_feasible'] for r in group])),
                               'corpus_insufficient_rate': float(np.mean([r['corpus_insufficient'] for r in group]))})
    return result


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    out = ROOT/'results'/'pilot_v01'
    if (out/'manifest.json').exists():
        previous = json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        if previous['code_sha256'] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
            raise SystemExit('Code changed: choose a new versioned output directory instead of replacing old results')
    out.mkdir(parents=True, exist_ok=True)
    protocol_sha = hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest()
    started = datetime.now(timezone.utc).isoformat()
    rows, fingerprints = [], []
    for seed in SEEDS:
        for s, scenario in enumerate(SCENARIOS):
            for p, rate in enumerate(RATES):
                for query in range(100):
                    labels = generate_labels(seed, s, p, query)
                    positions = np.flatnonzero(labels)
                    r_star = int(positions[K-1])+1 if len(positions) >= K else N+1
                    actual_rate = float(labels.mean())
                    results = {}
                    query_id = f'{seed}-{s}-{p}-{query}'
                    fingerprints.append({'query_id': query_id, 'labels_sha256': hashlib.sha256(np.packbits(labels).tobytes()).hexdigest()})
                    for method in METHODS:
                        r = run_policy(labels, method, actual_rate)
                        results[method] = r
                        rows.append({'query_id': query_id, 'seed': seed, 'scenario': scenario,
                                     'nominal_rate': rate, 'actual_global_rate': actual_rate, 'method': method,
                                     **r, 'kth_eligible_rank': r_star if r_star <= N else '',
                                     'budget_feasible': int(r_star <= BUDGET),
                                     'corpus_insufficient': int(len(positions) < K),
                                     'overscan': r['checked']-r_star if r['full'] else ''})
                    assert len({results[m]['full'] for m in ITERATIVE}) == 1
                    assert results['adaptive']['full'] == int(r_star <= BUDGET)
    summary = aggregate(rows)
    write_csv(out/'per_query.csv', rows)
    write_csv(out/'summary.csv', summary)
    write_csv(out/'query_fingerprints.csv', fingerprints)
    manifest = {'stage': 'candidate-prefix simulation only; no ocean samples, ANN index, or actual engine latency',
                'started_at_utc': started, 'completed_at_utc': datetime.now(timezone.utc).isoformat(),
                'python': sys.version, 'platform': platform.platform(), 'numpy': np.__version__, 'scipy': scipy.__version__,
                'k': K, 'n': N, 'budget': BUDGET, 'seeds': SEEDS, 'queries_per_seed_cell': 100,
                'independent_queries': len(fingerprints), 'paired_policy_observations': len(rows),
                'protocol_sha256': protocol_sha, 'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'parameters': {'pilot': PILOT, 'min_batch': MIN_BATCH, 'prior_strength': PRIOR, 'safety': SAFETY},
                'all_iterative_methods_same_fullness_per_query': True,
                'files_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.csv')}}
    (out/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'queries': len(fingerprints), 'rows': len(rows), 'checks': 'all passed'}, ensure_ascii=False))
    for r in summary:
        if r['nominal_rate'] == .01:
            print(f"{r['scenario']:12} {r['method']:14} full={r['full_rate']:.3f} checked={r['checked_mean']:.1f} calls={r['calls_mean']:.2f}")


if __name__ == '__main__':
    main()
