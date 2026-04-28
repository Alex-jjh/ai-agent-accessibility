import os, json
from pathlib import Path

for d in ['expansion-som', 'expansion-cua']:
    base = Path(f'data/{d}')
    jsons = list(base.rglob('*.json'))
    cases = [f for f in jsons if 'cases' in str(f) and f.name not in ('run-state.json', 'manifest.json')]
    print(f'{d}: {len(cases)} case files')
    if cases:
        with open(cases[0]) as f:
            data = json.load(f)
        cid = data.get('caseId', '?')
        succ = data.get('trace', {}).get('success', '?')
        mode = data.get('agentConfig', {}).get('observationMode', '?')
        print(f'  sample: {cid} success={succ} mode={mode}')
