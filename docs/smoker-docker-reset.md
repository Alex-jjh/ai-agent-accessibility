# Smoker Docker Reset Strategy

> **Context**: Mode A (3,042 cases) accumulated Docker state drift that
> required post-hoc GT corrections on tasks 41, 198, 293. Smoker is
> lower-risk (base variant only, no patches) but info-retrieval tasks
> can still mutate DB state (search queries, view counts, login events).
> This doc locks in a pragmatic reset strategy.

## What changes vs Mode A

Mode A problem:
- 26 operators × 13 tasks × 3 agents × 3 reps = 3,042 cases
- Zero Docker resets across the full run
- Drift sources: agent actions (searches, clicks) + variant patches
  modifying DOM that triggered server-side events

Smoker difference:
- base variant only = zero DOM patches
- Only drift source is agent's own actions
- string_match tasks (231) are pure reads → minimal DB writes
- Mixed-eval tasks (453) can touch URL state but rarely mutate DB beyond
  `search_query` / audit log tables

## Strategy: one clean start per shard

Reset WebArena containers **once before each shard starts**, then let
the shard run to completion. Detect drift via the answer-consistency
check in `scripts/smoker/analyze-smoker.py` — any task where reps 1/2/3
produce different literal answers is dropped from the passing set.

This is a ~20-minute cost per shard (vs >2 hours if we reset every 200
cases) and catches drift at the filter stage where it belongs.

## Commands

### Full reset (2 min wall, most reliable)

Run on the WebArena EC2 (10.0.1.50) via SSM:

```bash
# One-liner — stops all 4 app containers and restarts from AMI-baked images
for c in shopping shopping_admin forum gitlab; do
  docker restart $c
done
# Wait for health
sleep 60
for port in 7770 7780 9999 8023; do
  curl -sf http://localhost:$port >/dev/null && echo "  :$port OK" || echo "  :$port FAIL"
done
```

Note: `docker restart` preserves the container but replays the DB from
the volume. If a prior experiment mutated the volume, use the harder
reset below.

### Hard reset (volume destroyed, ~3 min)

Only if `docker restart` doesn't restore expected baseline state:

```bash
# Stop + remove + recreate from terraform-baked AMI images
docker stop shopping shopping_admin forum gitlab
docker rm shopping shopping_admin forum gitlab

# Terraform user-data brings these back on instance reboot.
# Faster: manually re-run the docker run commands from user-data.
sudo systemctl restart docker
# Or just reboot the WebArena EC2 if you're not in a hurry:
sudo reboot
```

The infra/webarena.tf user-data regenerates containers on boot. See
`docs/deployment.md` for the instance-reboot flow.

### Magento-only reset (fast, Stage 3 only)

For Stage 3 (Manipulation) where patches run, drift is faster. If only
Magento drifts:

```bash
# Requires dump.sql present in the container from initial provisioning.
docker exec shopping mysql -u magentouser -pMyPassword magentodb \
  < /docker-entrypoint-initdb.d/dump.sql
docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb \
  < /docker-entrypoint-initdb.d/dump.sql
```

Not recommended for smoker — container-level restart is simpler and
covers all 4 apps.

## Pre-shard checklist

Before launching either smoker shard:

```bash
# From the control host, SSM into the WebArena EC2
aws ssm start-session --target <webarena-instance-id>

# On the WebArena EC2
for c in shopping shopping_admin forum gitlab; do docker restart $c; done
sleep 60

# Sanity-check each app responds
for port in 7770 7780 9999 8023; do
  curl -sfI http://localhost:$port | head -1
done
```

Expected output: four `HTTP/1.1 200` or `HTTP/1.1 302` lines (redirects
are fine — they indicate the app server is up).

Then on the Platform EC2, launch the shard:

```bash
bash scripts/launchers/launch-smoker-shard-a.sh   # or shard-b
```

## Post-shard verification

After the shard completes, before running the filter:

```bash
# On local machine after download
python3.11 scripts/smoker/analyze-smoker.py \
  --shard-a data/smoker-shard-a \
  --shard-b data/smoker-shard-b
```

Look at the `answer_drift` drop-reason count in the output. If >10% of
tasks drop for drift, the container-level restart didn't stick — audit
the raw cases to confirm it's agent-side variance vs DB-side drift
before deciding whether to re-run.

## What we are explicitly NOT doing

- Not resetting per-rep or per-task (too slow; 2,052 cases × 2 min each
  = 68 hours of pure reset time)
- Not checkpointing the DB state between reps (same problem)
- Not migrating to WebArena Verified slim images yet (migration effort
  unjustified at smoker stage; revisit for Stage 3 if drift bites)

## When to escalate

- >20% of tasks drop for `answer_drift` → DB-side drift is dominating.
  Re-run the affected shard with a hard reset between 200-case batches.
- Task 4/41/94/198/293 drop for drift → they did in Mode A too; apply
  the same GT corrections from `scripts/amt/ground-truth-corrections.json`
  if their drift pattern matches.
- GitLab 5xx errors appear in traces → GitLab container memory pressure,
  restart just that container: `docker restart gitlab`.
