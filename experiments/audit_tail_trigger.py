"""Replay frozen v0.2 streams to audit why the tail rule cannot trigger."""
from pathlib import Path
import json
import numpy as np
import run_pilot as base
import run_tail_pilot as tail

root=Path(__file__).resolve().parent
records=[]
for seed in tail.SEEDS:
 for s,scenario in enumerate(base.SCENARIOS):
  for p,rate in enumerate(base.RATES):
   for q in range(100):
    labels=base.generate_labels(seed,s,p,q)
    result=tail.run_policy(labels,'fixed128_tail32',float(labels.mean()))
    checked=hits=0
    before_final=0
    while checked<base.BUDGET and hits<base.K:
     before_final=hits
     end=min(base.BUDGET,checked+(32 if hits==9 else 128))
     hits+=int(np.count_nonzero(labels[checked:end]))
     checked=end
    assert checked==result['checked'] and int(hits>=10)==result['full']
    records.append({'scenario':scenario,'nominal_rate':rate,'full':result['full'],
      'triggered':int(result['tail_calls']>0),
      'completed_before_tail':int(hits>=10 and before_final<=8),
      'first_batch_complete':int(hits>=10 and checked==128)})
summary=[]
for scenario in base.SCENARIOS:
 for rate in base.RATES:
  g=[r for r in records if r['scenario']==scenario and r['nominal_rate']==rate]
  summary.append({'scenario':scenario,'nominal_rate':rate,'queries':len(g),
   **{name:float(np.mean([r[name] for r in g])) for name in
      ('full','triggered','completed_before_tail','first_batch_complete')}})
out=root/'results/tail_audit_v01'
out.mkdir(parents=True,exist_ok=True)
base.write_csv(out/'tail_trigger_audit.csv',summary)
print(json.dumps(summary,indent=2))
