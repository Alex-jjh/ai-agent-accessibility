#!/usr/bin/env npx tsx
/**
 * audit-operator-batch.ts — batch runner for A.5 DOM signature audit.
 *
 * Runs audit-operator.ts across all 13 experiment task URLs × 26 operators
 * × N reps, then aggregates into results/amt/dom_signatures.json with
 * mean ± stddev per dimension per operator.
 *
 * Usage:
 *   npx tsx scripts/audit-operator-batch.ts --base-ip 10.0.1.50
 *   npx tsx scripts/audit-operator-batch.ts --base-ip 10.0.1.50 --reps 3
 *   npx tsx scripts/audit-operator-batch.ts --base-ip 10.0.1.50 --operators L1,L6,L11 --tasks 23,29
 *
 * Spec: roadmap v8 §2.4 — 13 URLs × 3 reps × 26 operators = 1,014 audits.
 */
import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..');

// ─── Task URL mapping ───
// Each experiment task has a start_url from test.raw.json. We resolve
// the __PLACEHOLDER__ tokens to actual WebArena URLs.
interface TaskUrl {
  taskId: string;
  app: string;
  loginApp: string;  // for --login-app flag
  url: string;       // resolved URL
}

function buildTaskUrls(baseIp: string): TaskUrl[] {
  const S = `http://${baseIp}:7770`;
  const SA = `http://${baseIp}:7780`;
  const R = `http://${baseIp}:9999`;
  const G = `http://${baseIp}:8023`;

  // 13 experiment tasks from project-context.md
  return [
    // shopping_admin tasks
    { taskId: '4',   app: 'shopping_admin', loginApp: 'shopping_admin', url: `${SA}/admin/dashboard` },
    { taskId: '41',  app: 'shopping_admin', loginApp: 'shopping_admin', url: `${SA}/admin/dashboard` },
    { taskId: '94',  app: 'shopping_admin', loginApp: 'shopping_admin', url: `${SA}/admin/dashboard` },
    { taskId: '198', app: 'shopping_admin', loginApp: 'shopping_admin', url: `${SA}/admin/dashboard` },
    // shopping tasks
    { taskId: '23',  app: 'shopping', loginApp: 'shopping',
      url: `${S}/3-pack-samsung-galaxy-s6-screen-protector-nearpow-tempered-glass-screen-protector-with-9h-hardness-crystal-clear-easy-bubble-free-installation-scratch-resist.html` },
    { taskId: '24',  app: 'shopping', loginApp: 'shopping',
      url: `${S}/haflinger-men-s-wool-felt-open-back-slippers-beige-550-peat-us-7.html` },
    { taskId: '26',  app: 'shopping', loginApp: 'shopping',
      url: `${S}/epson-workforce-wf-3620-wifi-direct-all-in-one-color-inkjet-printer-copier-scanner-amazon-dash-replenishment-ready.html` },
    { taskId: '188', app: 'shopping', loginApp: 'shopping', url: `${S}/` },
    // reddit tasks
    { taskId: '29',  app: 'reddit', loginApp: 'reddit', url: `${R}/` },
    { taskId: '67',  app: 'reddit', loginApp: 'reddit', url: `${R}/` },
    // gitlab tasks
    { taskId: '132', app: 'gitlab', loginApp: 'gitlab', url: `${G}/` },
    { taskId: '293', app: 'gitlab', loginApp: 'gitlab', url: `${G}/` },
    { taskId: '308', app: 'gitlab', loginApp: 'gitlab', url: `${G}/` },
  ];
}

// ─── Signature types (mirror audit-operator.ts output) ───
interface OperatorSignature {
  D1_tagCountDeltas: Record<string, number>;
  D2_attrChanges: { added: number; removed: number };
  D3_nodeCountDelta: number;
  A1_rolesChanged: number;
  A2_namesChanged: number;
  A3_ariaStateChanges: Record<string, number>;
  V1_ssim: number | null;
  V2_maxBBoxShift_px: number;
  V3_meanContrastDelta: number;
  F1_interactiveCountDelta: number;
  F2_inlineHandlerDelta: number;
  F3_focusableCountDelta: number;
  changesReturned: number;
  durationMs: number;
}

interface AuditResult {
  operators: Record<string, OperatorSignature>;
  errors: Record<string, string>;
}

// ─── Aggregation ───
interface AggregatedDim {
  mean: number;
  stddev: number;
  n: number;
  values: number[];
}

function aggregate(values: number[]): AggregatedDim {
  const n = values.length;
  if (n === 0) return { mean: 0, stddev: 0, n: 0, values: [] };
  const mean = values.reduce((a, b) => a + b, 0) / n;
  const variance = values.reduce((a, v) => a + (v - mean) ** 2, 0) / n;
  return { mean: Number(mean.toFixed(4)), stddev: Number(Math.sqrt(variance).toFixed(4)), n, values };
}

function aggregateSignatures(
  sigs: OperatorSignature[],
): Record<string, AggregatedDim> {
  const dims: Record<string, number[]> = {
    D2_added: [], D2_removed: [], D3_nodeCountDelta: [],
    A1_rolesChanged: [], A2_namesChanged: [],
    V1_ssim: [], V2_maxBBoxShift_px: [], V3_meanContrastDelta: [],
    F1_interactiveCountDelta: [], F2_inlineHandlerDelta: [], F3_focusableCountDelta: [],
    changesReturned: [],
  };

  for (const sig of sigs) {
    dims.D2_added.push(sig.D2_attrChanges.added);
    dims.D2_removed.push(sig.D2_attrChanges.removed);
    dims.D3_nodeCountDelta.push(sig.D3_nodeCountDelta);
    dims.A1_rolesChanged.push(sig.A1_rolesChanged);
    dims.A2_namesChanged.push(sig.A2_namesChanged);
    if (sig.V1_ssim !== null) dims.V1_ssim.push(sig.V1_ssim);
    dims.V2_maxBBoxShift_px.push(sig.V2_maxBBoxShift_px);
    dims.V3_meanContrastDelta.push(sig.V3_meanContrastDelta);
    dims.F1_interactiveCountDelta.push(sig.F1_interactiveCountDelta);
    dims.F2_inlineHandlerDelta.push(sig.F2_inlineHandlerDelta);
    dims.F3_focusableCountDelta.push(sig.F3_focusableCountDelta);
    dims.changesReturned.push(sig.changesReturned);
  }

  const result: Record<string, AggregatedDim> = {};
  for (const [k, v] of Object.entries(dims)) {
    result[k] = aggregate(v);
  }
  return result;
}

// ─── CLI ───
function parseArgs(argv: string[]): Record<string, string> {
  const args: Record<string, string> = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const key = argv[i].slice(2);
      const val = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : 'true';
      args[key] = val;
    }
  }
  return args;
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const baseIp = args['base-ip'] || '10.0.1.50';
  const reps = parseInt(args['reps'] || '3', 10);
  const operatorFilter = args['operators']?.split(',').map(s => s.trim()) || null;
  const taskFilter = args['tasks']?.split(',').map(s => s.trim()) || null;
  const settleMs = args['settle-ms'] || '5000';
  const quietMs = args['quiet-ms'] || '500';
  const outputPath = args['output'] || join(REPO, 'results/amt/dom_signatures.json');

  const allTasks = buildTaskUrls(baseIp);
  const tasks = taskFilter
    ? allTasks.filter(t => taskFilter.includes(t.taskId))
    : allTasks;

  const operatorArg = operatorFilter ? operatorFilter.join(',') : '';  // empty = all 26

  const totalRuns = tasks.length * reps;
  console.error(`[batch] Tasks: ${tasks.length}, Reps: ${reps}, Total audit runs: ${totalRuns}`);
  console.error(`[batch] Operators: ${operatorArg || 'all 26'}`);
  console.error(`[batch] Output: ${outputPath}`);
  console.error('');

  // Collect per-operator signatures across all tasks × reps
  const allSigs: Record<string, OperatorSignature[]> = {};
  const allErrors: Record<string, string[]> = {};
  let runCount = 0;

  for (const task of tasks) {
    for (let rep = 1; rep <= reps; rep++) {
      runCount++;
      const runId = `batch-t${task.taskId}-r${rep}`;
      console.error(`[batch] [${runCount}/${totalRuns}] task=${task.taskId} rep=${rep} url=${task.url.slice(0, 60)}...`);

      const cmdArgs = [
        'scripts/audit-operator.ts',
        '--url', task.url,
        '--settle-ms', settleMs,
        '--quiet-ms', quietMs,
        '--run-id', runId,
        '--login-app', task.loginApp,
        '--login-base-url', (() => {
          const u = new URL(task.url);
          return `${u.protocol}//${u.host}`;
        })(),
      ];
      if (operatorArg) {
        cmdArgs.push('--operators', operatorArg);
      }

      const result = spawnSync('npx', ['tsx', ...cmdArgs], {
        encoding: 'utf-8',
        timeout: 600_000,  // 10 min per audit run
        cwd: REPO,
      });

      // Read the audit.json from the run-dir
      const auditPath = join(REPO, 'data/amt-audit-runs', runId, 'audit.json');
      if (!existsSync(auditPath)) {
        console.error(`[batch]   FAILED — no audit.json at ${auditPath}`);
        if (result.stderr) console.error(`[batch]   stderr: ${result.stderr.slice(-200)}`);
        continue;
      }

      try {
        const audit: AuditResult = JSON.parse(readFileSync(auditPath, 'utf-8'));
        for (const [opId, sig] of Object.entries(audit.operators)) {
          if (!allSigs[opId]) allSigs[opId] = [];
          allSigs[opId].push(sig);
        }
        for (const [opId, err] of Object.entries(audit.errors)) {
          if (!allErrors[opId]) allErrors[opId] = [];
          allErrors[opId].push(`${task.taskId}:r${rep}: ${err}`);
        }
        const opCount = Object.keys(audit.operators).length;
        const errCount = Object.keys(audit.errors).length;
        console.error(`[batch]   OK — ${opCount} operators, ${errCount} errors`);
      } catch (e) {
        console.error(`[batch]   FAILED to parse audit.json: ${e}`);
      }
    }
  }

  // Aggregate
  console.error('');
  console.error('[batch] Aggregating signatures...');

  const aggregated: Record<string, {
    dims: Record<string, AggregatedDim>;
    sampleCount: number;
    errorCount: number;
  }> = {};

  for (const [opId, sigs] of Object.entries(allSigs)) {
    aggregated[opId] = {
      dims: aggregateSignatures(sigs),
      sampleCount: sigs.length,
      errorCount: allErrors[opId]?.length ?? 0,
    };
  }

  const output = {
    schemaVersion: 'amt-dom-signatures/v1',
    timestamp: new Date().toISOString(),
    config: {
      baseIp,
      reps,
      taskCount: tasks.length,
      taskIds: tasks.map(t => t.taskId),
      operatorFilter: operatorFilter || 'all',
      settleMs: parseInt(settleMs),
      quietMs: parseInt(quietMs),
    },
    operators: aggregated,
    errors: allErrors,
  };

  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, JSON.stringify(output, null, 2));
  console.error(`[batch] Wrote ${outputPath}`);
  console.error(`[batch] ${Object.keys(aggregated).length} operators aggregated across ${runCount} runs`);

  // Summary table
  console.error('');
  console.error('Operator  | Samples | V1_ssim      | A1_roles     | F1_interact  | Changes');
  console.error('----------|---------|--------------|--------------|--------------|--------');
  for (const [opId, data] of Object.entries(aggregated).sort(([a], [b]) => a.localeCompare(b))) {
    const v1 = data.dims.V1_ssim;
    const a1 = data.dims.A1_rolesChanged;
    const f1 = data.dims.F1_interactiveCountDelta;
    const ch = data.dims.changesReturned;
    console.error(
      `${opId.padEnd(9)} | ${String(data.sampleCount).padEnd(7)} | ` +
      `${v1.mean.toFixed(3)}±${v1.stddev.toFixed(3)} | ` +
      `${a1.mean.toFixed(1)}±${a1.stddev.toFixed(1)}   | ` +
      `${f1.mean.toFixed(1)}±${f1.stddev.toFixed(1)}   | ` +
      `${ch.mean.toFixed(0)}±${ch.stddev.toFixed(0)}`
    );
  }

  if (Object.keys(allErrors).length > 0) {
    console.error('');
    console.error(`[batch] ${Object.values(allErrors).flat().length} total errors across ${Object.keys(allErrors).length} operators`);
    process.exit(1);
  }
}

main().catch(e => {
  console.error(e);
  process.exit(1);
});
