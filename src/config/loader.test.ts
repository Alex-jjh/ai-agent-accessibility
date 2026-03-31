import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { loadConfig, validateConfig } from './loader.js';

/** Minimal valid config — only webarena.apps is truly required */
const MINIMAL_CONFIG = {
  webarena: {
    apps: {
      reddit: { url: 'http://localhost:9999' },
    },
  },
};

const FULL_CONFIG = {
  scanner: { wcagLevels: ['A', 'AA', 'AAA'], stabilityIntervalMs: 1000, stabilityTimeoutMs: 15000, concurrency: 3 },
  variants: {
    levels: ['low', 'base', 'high'],
    scoreRanges: { low: { min: 0, max: 0.3 }, base: { min: 0.4, max: 0.7 }, high: { min: 0.8, max: 1.0 } },
  },
  runner: {
    agentConfigs: [{ observationMode: 'text-only', llmBackend: 'claude-opus' }],
    repetitions: 5, maxSteps: 50, concurrency: 2,
  },
  recorder: { waitAfterLoadMs: 5000, concurrency: 10 },
  webarena: {
    apps: {
      reddit: { url: 'http://localhost:9999' },
      gitlab: { url: 'http://localhost:8080', resetEndpoint: '/reset' },
    },
  },
  output: { dataDir: 'results', exportFormats: ['json', 'csv'] },
};

let tmpDir: string;

beforeEach(() => { tmpDir = mkdtempSync(join(tmpdir(), 'cfg-test-')); });
afterEach(() => { rmSync(tmpDir, { recursive: true, force: true }); });

function writeJson(name: string, data: unknown): string {
  const p = join(tmpDir, name);
  writeFileSync(p, JSON.stringify(data));
  return p;
}

function writeYaml(name: string, content: string): string {
  const p = join(tmpDir, name);
  writeFileSync(p, content);
  return p;
}


// --- loadConfig: file parsing ---

describe('loadConfig', () => {
  it('parses a valid JSON config file', () => {
    const cfg = loadConfig(writeJson('config.json', FULL_CONFIG));
    expect(cfg.scanner.concurrency).toBe(3);
    expect(cfg.runner.repetitions).toBe(5);
    expect(cfg.webarena.apps.reddit.url).toBe('http://localhost:9999');
  });

  it('parses a valid YAML config file', () => {
    const yamlContent = `
webarena:
  apps:
    reddit:
      url: http://localhost:9999
scanner:
  wcagLevels:
    - A
    - AA
  concurrency: 8
`;
    const cfg = loadConfig(writeYaml('config.yaml', yamlContent));
    expect(cfg.webarena.apps.reddit.url).toBe('http://localhost:9999');
    expect(cfg.scanner.concurrency).toBe(8);
    expect(cfg.scanner.wcagLevels).toEqual(['A', 'AA']);
  });

  it('parses .yml extension', () => {
    const yamlContent = `
webarena:
  apps:
    cms:
      url: http://localhost:7770
`;
    const cfg = loadConfig(writeYaml('config.yml', yamlContent));
    expect(cfg.webarena.apps.cms.url).toBe('http://localhost:7770');
  });

  it('throws on unsupported file extension', () => {
    const p = join(tmpDir, 'config.toml');
    writeFileSync(p, 'key = "value"');
    expect(() => loadConfig(p)).toThrow('Unsupported config file extension');
  });

  it('throws on invalid JSON content', () => {
    const p = join(tmpDir, 'bad.json');
    writeFileSync(p, '{ broken json');
    expect(() => loadConfig(p)).toThrow();
  });

  it('throws when validation fails', () => {
    const cfg = { scanner: { concurrency: -1 } }; // missing webarena
    expect(() => loadConfig(writeJson('bad.json', cfg))).toThrow('Invalid config');
  });
});


// --- validateConfig: error reporting ---

describe('validateConfig', () => {
  it('returns valid for minimal config', () => {
    expect(validateConfig(MINIMAL_CONFIG)).toEqual({ valid: true, errors: [] });
  });

  it('returns valid for full config', () => {
    expect(validateConfig(FULL_CONFIG)).toEqual({ valid: true, errors: [] });
  });

  it('rejects null', () => {
    const r = validateConfig(null);
    expect(r.valid).toBe(false);
    expect(r.errors).toContain('Config must be a non-null object');
  });

  it('rejects arrays', () => {
    expect(validateConfig([]).valid).toBe(false);
  });

  it('reports missing webarena section', () => {
    const r = validateConfig({});
    expect(r.valid).toBe(false);
    expect(r.errors).toContain('Missing required section: webarena');
  });

  it('reports empty webarena.apps', () => {
    const r = validateConfig({ webarena: { apps: {} } });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch('at least one app');
  });

  it('reports missing app url', () => {
    const r = validateConfig({ webarena: { apps: { reddit: {} } } });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch('url must be a non-empty string');
  });

  it('reports invalid scanner.wcagLevels', () => {
    const r = validateConfig({ ...MINIMAL_CONFIG, scanner: { wcagLevels: ['X'] } });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch('wcagLevels');
  });

  it('reports invalid scanner.concurrency', () => {
    const r = validateConfig({ ...MINIMAL_CONFIG, scanner: { concurrency: 0 } });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch('concurrency must be a positive integer');
  });

  it('reports invalid scanner.stabilityIntervalMs', () => {
    const r = validateConfig({ ...MINIMAL_CONFIG, scanner: { stabilityIntervalMs: -100 } });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch('stabilityIntervalMs');
  });

  it('reports invalid variant levels', () => {
    const r = validateConfig({ ...MINIMAL_CONFIG, variants: { levels: ['ultra'] } });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch('variants.levels');
  });

  it('reports invalid scoreRanges key', () => {
    const r = validateConfig({ ...MINIMAL_CONFIG, variants: { scoreRanges: { ultra: { min: 0, max: 1 } } } });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch('invalid key');
  });

  it('reports invalid agentConfig fields', () => {
    const r = validateConfig({
      ...MINIMAL_CONFIG,
      runner: { agentConfigs: [{ observationMode: 'invalid', llmBackend: '' }] },
    });
    expect(r.valid).toBe(false);
    expect(r.errors.length).toBeGreaterThanOrEqual(2);
    expect(r.errors.some(e => e.includes('observationMode'))).toBe(true);
    expect(r.errors.some(e => e.includes('llmBackend'))).toBe(true);
  });

  it('reports invalid runner.repetitions', () => {
    const r = validateConfig({ ...MINIMAL_CONFIG, runner: { repetitions: 0 } });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch('repetitions');
  });

  it('reports invalid output.exportFormats', () => {
    const r = validateConfig({ ...MINIMAL_CONFIG, output: { exportFormats: ['xml'] } });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch('exportFormats');
  });

  it('collects multiple errors at once', () => {
    const r = validateConfig({
      scanner: { concurrency: -1 },
      runner: { maxSteps: 0 },
      // missing webarena
    });
    expect(r.valid).toBe(false);
    expect(r.errors.length).toBeGreaterThanOrEqual(3);
  });
});


// --- Default value application ---

describe('default values', () => {
  it('applies all defaults when only webarena is provided', () => {
    const cfg = loadConfig(writeJson('min.json', MINIMAL_CONFIG));

    // scanner defaults
    expect(cfg.scanner.wcagLevels).toEqual(['A', 'AA']);
    expect(cfg.scanner.stabilityIntervalMs).toBe(2000);
    expect(cfg.scanner.stabilityTimeoutMs).toBe(30000);
    expect(cfg.scanner.concurrency).toBe(5);

    // variants defaults
    expect(cfg.variants.levels).toEqual(['low', 'medium-low', 'base', 'high']);
    expect(cfg.variants.scoreRanges.low).toEqual({ min: 0.0, max: 0.25 });
    expect(cfg.variants.scoreRanges.high).toEqual({ min: 0.75, max: 1.0 });

    // runner defaults
    expect(cfg.runner.repetitions).toBe(3);
    expect(cfg.runner.maxSteps).toBe(30);
    expect(cfg.runner.concurrency).toBe(3);

    // recorder defaults
    expect(cfg.recorder.waitAfterLoadMs).toBe(10000);
    expect(cfg.recorder.concurrency).toBe(5);

    // output defaults
    expect(cfg.output.dataDir).toBe('data');
    expect(cfg.output.exportFormats).toEqual(['json']);
  });

  it('preserves user-provided values and fills missing ones', () => {
    const partial = {
      ...MINIMAL_CONFIG,
      scanner: { concurrency: 10 },
      runner: { maxSteps: 100 },
    };
    const cfg = loadConfig(writeJson('partial.json', partial));

    // user-provided
    expect(cfg.scanner.concurrency).toBe(10);
    expect(cfg.runner.maxSteps).toBe(100);

    // defaults filled in
    expect(cfg.scanner.wcagLevels).toEqual(['A', 'AA']);
    expect(cfg.scanner.stabilityIntervalMs).toBe(2000);
    expect(cfg.runner.repetitions).toBe(3);
    expect(cfg.runner.concurrency).toBe(3);
  });
});