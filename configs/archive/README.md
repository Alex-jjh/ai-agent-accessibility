# configs/archive/ — Historical Experiment Configs

These YAML config files defined earlier experimental batches that have been
completed and analyzed. Retained for reproducibility — any paper claim about
an earlier pilot must be reproducible from its original config.

## What's here

### Pilot batches (N=1,040 existing data)
- `config-pilot.yaml` — Pilot 1 (2026-04-01), N=54
- `config-pilot2.yaml` — Pilot 2, multi-app screening
- `config-pilot3.yaml` — Pilot 3a (text-only), N=120
- `config-pilot3b.yaml` — Pilot 3b (text+vision), N=240
- `config-pilot4.yaml` — Pilot 4 text+SoM, N=240
- `config-pilot4-cua.yaml` — Pilot 4 CUA, N=120

### Smoke tests (pre-AMT)
- `config-psl-smoke.yaml` — PSL (pure-semantic-low) verification
- `config-psl-expanded-smoke.yaml` — PSL on 6 tasks
- `config-regression.yaml` — bug-fix regression on 9 tasks
- `config-reinject-smoke.yaml` — variant re-injection verification
- `config-task188-smoke.yaml` — task 188 control verification
- `config-vision-smoke.yaml` — SoM vision pipeline
- `config-cua-smoke.yaml` — CUA pipeline smoke
- `config-gitlab-smoke.yaml` — GitLab Vue.js expansion readiness
- `config-llama4-smoke.yaml` — Llama 4 Bedrock integration
- `config-expansion-phase2-smoke.yaml` — admin + shopping expansion

## Active configs (at repo root)

Currently active experiment configs remain at the repo root:

- AMT Mode A: `config-mode-a-shard-{a,b}.yaml`, `config-mode-a-llama4-textonly.yaml`, `config-mode-a-cua-screenshots.yaml`
- C.2 Composition: `config-c2-composition-shard-{a,b}.yaml`
- Expansion: `config-expansion-{claude,llama4,som,cua,som-smoke,cua-smoke}.yaml`
- Current smoke: `config-b1-smoke.yaml`

## How to run an archived config

If you need to re-run an archived experiment (e.g., for regression testing):

```bash
# On EC2:
nohup npx tsx scripts/runners/run-pilot3.ts \
  --config configs/archive/config-pilot4.yaml \
  > pilot4.log 2>&1 &
```

The `--config` flag accepts any path, so archiving doesn't break reproducibility.
