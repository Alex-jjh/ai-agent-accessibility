// Configuration management — YAML/JSON config loading and validation
import { readFileSync } from 'node:fs';
import { extname } from 'node:path';
import yaml from 'js-yaml';
import type { ExperimentConfig } from './types.js';
import type { VariantLevel } from '../variants/types.js';

const VALID_WCAG = new Set(['A', 'AA', 'AAA']);
const VALID_VARIANTS = new Set(['low', 'medium-low', 'base', 'high']);
const VALID_OBS = new Set(['text-only', 'vision', 'vision-only', 'cua']);
const VALID_FMT = new Set(['json', 'csv']);

const DEFAULTS = {
  scanner: { wcagLevels: ['A', 'AA'] as ('A'|'AA'|'AAA')[], stabilityIntervalMs: 2000, stabilityTimeoutMs: 30000, concurrency: 5 },
  variants: { levels: ['low','medium-low','base','high'] as VariantLevel[], scoreRanges: { low:{min:0,max:0.25},'medium-low':{min:0.25,max:0.5},base:{min:0.4,max:0.7},high:{min:0.75,max:1} } as Record<VariantLevel,{min:number;max:number}> },
  runner: { repetitions: 3, maxSteps: 30, concurrency: 3 },
  recorder: { waitAfterLoadMs: 10000, concurrency: 5 },
  output: { dataDir: 'data', exportFormats: ['json'] as ('json'|'csv')[] },
};

export function loadConfig(filePath: string): ExperimentConfig {
  const raw = readFileSync(filePath, 'utf-8');
  const ext = extname(filePath).toLowerCase();
  let parsed: unknown;
  if (ext === '.yaml' || ext === '.yml') parsed = yaml.load(raw);
  else if (ext === '.json') parsed = JSON.parse(raw);
  else throw new Error(`Unsupported config file extension "${ext}". Use .yaml, .yml, or .json`);
  const v = validateConfig(parsed);
  if (!v.valid) throw new Error(`Invalid config:\n  - ${v.errors.join('\n  - ')}`);
  return applyDefaults(parsed as Record<string, unknown>);
}

export function validateConfig(config: unknown): { valid: boolean; errors: string[] } {
  const e: string[] = [];
  if (config == null || typeof config !== 'object' || Array.isArray(config)) return { valid: false, errors: ['Config must be a non-null object'] };
  const c = config as Record<string, unknown>;
  if (c.scanner !== undefined) vScanner(c.scanner, e);
  if (c.variants !== undefined) vVariants(c.variants, e);
  if (c.runner !== undefined) vRunner(c.runner, e);
  if (c.recorder !== undefined) vRecorder(c.recorder, e);
  if (c.webarena === undefined) e.push('Missing required section: webarena');
  else vWebarena(c.webarena, e);
  if (c.output !== undefined) vOutput(c.output, e);
  return { valid: e.length === 0, errors: e };
}

function posInt(v: unknown) { return typeof v === 'number' && Number.isInteger(v) && v >= 1; }
function posNum(v: unknown) { return typeof v === 'number' && v > 0; }
function isObj(v: unknown): v is Record<string, unknown> { return v != null && typeof v === 'object' && !Array.isArray(v); }

function vScanner(s: unknown, e: string[]) {
  if (!isObj(s)) { e.push('scanner must be an object'); return; }
  if (s.wcagLevels !== undefined && (!Array.isArray(s.wcagLevels) || !s.wcagLevels.every(l => VALID_WCAG.has(l as string))))
    e.push('scanner.wcagLevels must be an array of "A", "AA", or "AAA"');
  if (s.stabilityIntervalMs !== undefined && !posNum(s.stabilityIntervalMs))
    e.push('scanner.stabilityIntervalMs must be a positive number');
  if (s.stabilityTimeoutMs !== undefined && !posNum(s.stabilityTimeoutMs))
    e.push('scanner.stabilityTimeoutMs must be a positive number');
  if (s.concurrency !== undefined && !posInt(s.concurrency))
    e.push('scanner.concurrency must be a positive integer');
}

function vVariants(v: unknown, e: string[]) {
  if (!isObj(v)) { e.push('variants must be an object'); return; }
  if (v.levels !== undefined && (!Array.isArray(v.levels) || !v.levels.every(l => VALID_VARIANTS.has(l as string))))
    e.push('variants.levels must be an array of "low", "medium-low", "base", or "high"');
  if (v.scoreRanges !== undefined) {
    if (!isObj(v.scoreRanges)) { e.push('variants.scoreRanges must be an object'); }
    else {
      for (const [k, r] of Object.entries(v.scoreRanges)) {
        if (!VALID_VARIANTS.has(k)) e.push(`variants.scoreRanges has invalid key "${k}"`);
        if (!isObj(r) || typeof r.min !== 'number' || typeof r.max !== 'number')
          e.push(`variants.scoreRanges.${k} must have numeric min and max`);
      }
    }
  }
}

function vAgentConfig(a: unknown, p: string, e: string[]) {
  if (!isObj(a)) { e.push(`${p} must be an object`); return; }
  if (!VALID_OBS.has(a.observationMode as string)) e.push(`${p}.observationMode must be "text-only", "vision", "vision-only", or "cua"`);
  if (typeof a.llmBackend !== 'string' || a.llmBackend.length === 0) e.push(`${p}.llmBackend must be a non-empty string`);
}

function vRunner(r: unknown, e: string[]) {
  if (!isObj(r)) { e.push('runner must be an object'); return; }
  if (r.agentConfigs !== undefined) {
    if (!Array.isArray(r.agentConfigs)) e.push('runner.agentConfigs must be an array');
    else r.agentConfigs.forEach((ac: unknown, i: number) => vAgentConfig(ac, `runner.agentConfigs[${i}]`, e));
  }
  if (r.repetitions !== undefined && !posInt(r.repetitions)) e.push('runner.repetitions must be a positive integer');
  if (r.maxSteps !== undefined && !posInt(r.maxSteps)) e.push('runner.maxSteps must be a positive integer');
  if (r.concurrency !== undefined && !posInt(r.concurrency)) e.push('runner.concurrency must be a positive integer');
}

function vRecorder(r: unknown, e: string[]) {
  if (!isObj(r)) { e.push('recorder must be an object'); return; }
  if (r.waitAfterLoadMs !== undefined && !posNum(r.waitAfterLoadMs)) e.push('recorder.waitAfterLoadMs must be a positive number');
  if (r.concurrency !== undefined && !posInt(r.concurrency)) e.push('recorder.concurrency must be a positive integer');
}

function vWebarena(w: unknown, e: string[]) {
  if (!isObj(w)) { e.push('webarena must be an object'); return; }
  if (w.apps === undefined) { e.push('webarena.apps is required'); return; }
  if (!isObj(w.apps)) { e.push('webarena.apps must be an object'); return; }
  if (Object.keys(w.apps).length === 0) e.push('webarena.apps must contain at least one app');
  for (const [n, app] of Object.entries(w.apps)) {
    if (!isObj(app)) { e.push(`webarena.apps.${n} must be an object`); continue; }
    if (typeof app.url !== 'string' || app.url.length === 0) e.push(`webarena.apps.${n}.url must be a non-empty string`);
  }
}

function vOutput(o: unknown, e: string[]) {
  if (!isObj(o)) { e.push('output must be an object'); return; }
  if (o.dataDir !== undefined && (typeof o.dataDir !== 'string' || o.dataDir.length === 0))
    e.push('output.dataDir must be a non-empty string');
  if (o.exportFormats !== undefined && (!Array.isArray(o.exportFormats) || !o.exportFormats.every(f => VALID_FMT.has(f as string))))
    e.push('output.exportFormats must be an array of "json" or "csv"');
}

function merge<T extends Record<string, unknown>>(provided: unknown, defaults: T): T {
  if (!isObj(provided)) return { ...defaults };
  const r = { ...defaults } as Record<string, unknown>;
  for (const [k, v] of Object.entries(provided)) {
    if (v === undefined) continue;
    // Deep merge nested plain objects (e.g. scoreRanges) instead of replacing them
    if (isObj(v) && isObj(r[k])) {
      r[k] = merge(v, r[k] as Record<string, unknown>);
    } else {
      r[k] = v;
    }
  }
  return r as T;
}

function applyDefaults(raw: Record<string, unknown>): ExperimentConfig {
  return {
    scanner: merge(raw.scanner, DEFAULTS.scanner),
    variants: merge(raw.variants, DEFAULTS.variants),
    runner: merge(raw.runner, DEFAULTS.runner),
    recorder: merge(raw.recorder, DEFAULTS.recorder),
    output: merge(raw.output, DEFAULTS.output),
    webarena: raw.webarena as ExperimentConfig['webarena'],
  } as ExperimentConfig;
}
