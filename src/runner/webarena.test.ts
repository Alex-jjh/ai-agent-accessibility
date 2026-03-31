// Unit tests for WebArena Docker integration
// Requirements: 20.1, 20.2, 20.3

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  DEFAULT_WEBARENA_APPS,
  buildWebArenaConfig,
  verifyWebArenaServices,
  resetWebArenaApp,
  resetAllWebArenaApps,
} from './webarena.js';
import type {
  WebArenaConfig,
  WebArenaAppConfig,
} from './webarena.js';

// ---------------------------------------------------------------------------
// Req 20.1 — Configuration for connecting to 4 WebArena Docker apps
// ---------------------------------------------------------------------------

describe('DEFAULT_WEBARENA_APPS', () => {
  it('defines all 4 WebArena apps', () => {
    expect(Object.keys(DEFAULT_WEBARENA_APPS)).toEqual(
      expect.arrayContaining(['reddit', 'gitlab', 'cms', 'ecommerce']),
    );
    expect(Object.keys(DEFAULT_WEBARENA_APPS)).toHaveLength(4);
  });

  it('uses standard localhost ports', () => {
    expect(DEFAULT_WEBARENA_APPS.reddit.url).toBe('http://localhost:9999');
    expect(DEFAULT_WEBARENA_APPS.gitlab.url).toBe('http://localhost:8023');
    expect(DEFAULT_WEBARENA_APPS.cms.url).toBe('http://localhost:7780');
    expect(DEFAULT_WEBARENA_APPS.ecommerce.url).toBe('http://localhost:7770');
  });
});

describe('buildWebArenaConfig', () => {
  it('merges user URLs with default reset config', () => {
    const config = buildWebArenaConfig({
      webarena: {
        apps: {
          reddit: { url: 'http://myhost:9999' },
          gitlab: { url: 'http://myhost:8023' },
          cms: { url: 'http://myhost:7780' },
          ecommerce: { url: 'http://myhost:7770' },
        },
      },
    });

    expect(config.reddit.url).toBe('http://myhost:9999');
    expect(config.reddit.composeService).toBe('reddit');
    expect(config.gitlab.resetStrategy).toBe('compose');
    expect(config.cms.resetCommand).toBe('bash prepare.sh');
  });

  it('preserves user-provided resetEndpoint', () => {
    const config = buildWebArenaConfig({
      webarena: {
        apps: {
          reddit: { url: 'http://localhost:9999', resetEndpoint: 'http://localhost:9999/reset' },
        },
      },
    });

    expect(config.reddit.resetEndpoint).toBe('http://localhost:9999/reset');
  });

  it('handles unknown app names gracefully (no defaults)', () => {
    const config = buildWebArenaConfig({
      webarena: {
        apps: {
          custom: { url: 'http://localhost:5000' },
        },
      },
    });

    expect(config.custom.url).toBe('http://localhost:5000');
    expect(config.custom.resetStrategy).toBe('compose');
  });
});

// ---------------------------------------------------------------------------
// Req 20.2 — Verify all services reachable before experiment start
// ---------------------------------------------------------------------------

describe('verifyWebArenaServices', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('reports all reachable when all fetches succeed', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
    });
    vi.stubGlobal('fetch', mockFetch);

    const config: WebArenaConfig = {
      reddit: { url: 'http://localhost:9999' },
      gitlab: { url: 'http://localhost:8023' },
    };

    const result = await verifyWebArenaServices(config);

    expect(result.allReachable).toBe(true);
    expect(result.statuses).toHaveLength(2);
    expect(result.failures).toHaveLength(0);
    expect(result.statuses[0].reachable).toBe(true);
    expect(result.statuses[0].statusCode).toBe(200);
  });

  it('reports failures when a service is unreachable', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200 })
      .mockRejectedValueOnce(new Error('ECONNREFUSED'));
    vi.stubGlobal('fetch', mockFetch);

    const config: WebArenaConfig = {
      reddit: { url: 'http://localhost:9999' },
      gitlab: { url: 'http://localhost:8023' },
    };

    const result = await verifyWebArenaServices(config);

    expect(result.allReachable).toBe(false);
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0].app).toBe('gitlab');
    expect(result.failures[0].error).toContain('ECONNREFUSED');
  });

  it('treats HTTP 4xx as reachable (server is up)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
    }));

    const config: WebArenaConfig = {
      reddit: { url: 'http://localhost:9999' },
    };

    const result = await verifyWebArenaServices(config);

    expect(result.allReachable).toBe(true);
    expect(result.statuses[0].reachable).toBe(true);
    expect(result.statuses[0].statusCode).toBe(403);
  });

  it('treats HTTP 5xx as unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
    }));

    const config: WebArenaConfig = {
      reddit: { url: 'http://localhost:9999' },
    };

    const result = await verifyWebArenaServices(config);

    expect(result.allReachable).toBe(false);
    expect(result.failures).toHaveLength(1);
  });

  it('records latency for each app', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
    }));

    const config: WebArenaConfig = {
      reddit: { url: 'http://localhost:9999' },
    };

    const result = await verifyWebArenaServices(config);

    expect(result.statuses[0].latencyMs).toBeGreaterThanOrEqual(0);
  });
});

// ---------------------------------------------------------------------------
// Req 20.3 — Reset WebArena app state between experiment runs
// ---------------------------------------------------------------------------

describe('resetWebArenaApp', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('resets via endpoint when resetEndpoint is configured', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', mockFetch);

    const config: WebArenaConfig = {
      reddit: {
        url: 'http://localhost:9999',
        resetEndpoint: 'http://localhost:9999/reset',
        resetStrategy: 'endpoint',
      },
    };

    const result = await resetWebArenaApp('reddit', config);

    expect(result.success).toBe(true);
    expect(result.strategy).toBe('endpoint');
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:9999/reset',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('resets via shell command when resetCommand is configured', async () => {
    const mockExec = vi.fn().mockResolvedValue({ stdout: 'OK', stderr: '' });

    const config: WebArenaConfig = {
      cms: {
        url: 'http://localhost:7780',
        resetCommand: 'bash prepare.sh',
        resetStrategy: 'shell',
      },
    };

    const result = await resetWebArenaApp('cms', config, mockExec);

    expect(result.success).toBe(true);
    expect(result.strategy).toBe('shell');
    expect(mockExec).toHaveBeenCalledWith('bash prepare.sh');
  });

  it('resets via docker compose when compose strategy is used', async () => {
    const mockExec = vi.fn().mockResolvedValue({ stdout: '', stderr: '' });

    const config: WebArenaConfig = {
      gitlab: {
        url: 'http://localhost:8023',
        composeService: 'gitlab',
        resetStrategy: 'compose',
      },
    };

    const result = await resetWebArenaApp('gitlab', config, mockExec);

    expect(result.success).toBe(true);
    expect(result.strategy).toBe('compose');
    expect(mockExec).toHaveBeenCalledWith('docker compose restart gitlab');
  });

  it('returns failure for unknown app name', async () => {
    const config: WebArenaConfig = {
      reddit: { url: 'http://localhost:9999' },
    };

    const result = await resetWebArenaApp('unknown', config);

    expect(result.success).toBe(false);
    expect(result.error).toContain('Unknown app');
    expect(result.error).toContain('reddit');
  });

  it('returns failure when shell command throws', async () => {
    const mockExec = vi.fn().mockRejectedValue(new Error('Command failed'));

    const config: WebArenaConfig = {
      cms: {
        url: 'http://localhost:7780',
        resetCommand: 'bash prepare.sh',
        resetStrategy: 'shell',
      },
    };

    const result = await resetWebArenaApp('cms', config, mockExec);

    expect(result.success).toBe(false);
    expect(result.error).toContain('Command failed');
  });

  it('returns failure when endpoint returns non-OK status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));

    const config: WebArenaConfig = {
      reddit: {
        url: 'http://localhost:9999',
        resetEndpoint: 'http://localhost:9999/reset',
        resetStrategy: 'endpoint',
      },
    };

    const result = await resetWebArenaApp('reddit', config);

    expect(result.success).toBe(false);
    expect(result.error).toContain('HTTP 500');
  });

  it('returns failure when compose service is missing', async () => {
    const config: WebArenaConfig = {
      gitlab: {
        url: 'http://localhost:8023',
        resetStrategy: 'compose',
        // no composeService
      },
    };

    const result = await resetWebArenaApp('gitlab', config);

    expect(result.success).toBe(false);
    expect(result.error).toContain('No Docker Compose service name');
  });

  it('infers endpoint strategy when resetEndpoint is present and no explicit strategy', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200 }));

    const config: WebArenaConfig = {
      reddit: {
        url: 'http://localhost:9999',
        resetEndpoint: 'http://localhost:9999/reset',
        // no explicit resetStrategy
      },
    };

    const result = await resetWebArenaApp('reddit', config);

    expect(result.success).toBe(true);
    expect(result.strategy).toBe('endpoint');
  });

  it('records duration on success and failure', async () => {
    const mockExec = vi.fn().mockResolvedValue({ stdout: '', stderr: '' });

    const config: WebArenaConfig = {
      cms: {
        url: 'http://localhost:7780',
        resetCommand: 'bash prepare.sh',
        resetStrategy: 'shell',
      },
    };

    const result = await resetWebArenaApp('cms', config, mockExec);

    expect(result.durationMs).toBeGreaterThanOrEqual(0);
  });
});

describe('resetAllWebArenaApps', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('resets all apps and reports aggregate result', async () => {
    const mockExec = vi.fn().mockResolvedValue({ stdout: '', stderr: '' });
    const logger = vi.fn();

    const config: WebArenaConfig = {
      reddit: {
        url: 'http://localhost:9999',
        resetCommand: 'bash prepare.sh',
        resetStrategy: 'shell',
      },
      gitlab: {
        url: 'http://localhost:8023',
        composeService: 'gitlab',
        resetStrategy: 'compose',
      },
    };

    const result = await resetAllWebArenaApps(config, mockExec, logger);

    expect(result.allSucceeded).toBe(true);
    expect(result.results).toHaveLength(2);
    expect(result.totalDurationMs).toBeGreaterThanOrEqual(0);
    expect(logger).toHaveBeenCalled();
  });

  it('reports partial failure when one app fails', async () => {
    const mockExec = vi.fn()
      .mockResolvedValueOnce({ stdout: '', stderr: '' })
      .mockRejectedValueOnce(new Error('Docker not running'));
    const logger = vi.fn();

    const config: WebArenaConfig = {
      reddit: {
        url: 'http://localhost:9999',
        resetCommand: 'bash prepare.sh',
        resetStrategy: 'shell',
      },
      gitlab: {
        url: 'http://localhost:8023',
        composeService: 'gitlab',
        resetStrategy: 'compose',
      },
    };

    const result = await resetAllWebArenaApps(config, mockExec, logger);

    expect(result.allSucceeded).toBe(false);
    expect(result.results[0].success).toBe(true);
    expect(result.results[1].success).toBe(false);
  });

  it('logs each app reset attempt', async () => {
    const mockExec = vi.fn().mockResolvedValue({ stdout: '', stderr: '' });
    const logger = vi.fn();

    const config: WebArenaConfig = {
      cms: {
        url: 'http://localhost:7780',
        resetCommand: 'bash prepare.sh',
        resetStrategy: 'shell',
      },
    };

    await resetAllWebArenaApps(config, mockExec, logger);

    const messages = logger.mock.calls.map((c: unknown[]) => c[0] as string);
    expect(messages.some((m: string) => m.includes('Resetting cms'))).toBe(true);
    expect(messages.some((m: string) => m.includes('reset OK'))).toBe(true);
  });
});
