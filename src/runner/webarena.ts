// Module 3: Agent Runner — WebArena Docker Integration
// Configures connections to 4 WebArena Docker apps, verifies service
// reachability, and supports resetting app state between experiment runs.
// Requirements: 20.1, 20.2, 20.3

import type { ExperimentConfig } from '../config/types.js';

/**
 * Names of the four WebArena Docker-hosted applications.
 */
export type WebArenaAppName = 'reddit' | 'gitlab' | 'cms' | 'ecommerce';

/**
 * Reset strategy for a WebArena app.
 *
 * - `'endpoint'` — HTTP POST/GET to a reset endpoint (fastest, ~seconds).
 * - `'shell'`    — Execute a shell command such as `bash prepare.sh` or a DB restore script.
 * - `'compose'`  — `docker compose down && docker compose up -d` (most reliable but slowest).
 */
export type ResetStrategy = 'endpoint' | 'shell' | 'compose';

/**
 * Configuration for a single WebArena app.
 */
export interface WebArenaAppConfig {
  /** Base URL of the running app (e.g. `http://localhost:9999`) */
  url: string;
  /** Optional HTTP endpoint that triggers a state reset */
  resetEndpoint?: string;
  /** Optional shell command for reset (e.g. `bash prepare.sh`) */
  resetCommand?: string;
  /** Docker Compose service name for compose-based reset */
  composeService?: string;
  /** Which reset strategy to use (default: inferred from available config) */
  resetStrategy?: ResetStrategy;
}

/**
 * Full WebArena configuration mapping app names to their configs.
 * Satisfies Req 20.1: configurable connections to all 4 apps via URLs.
 */
export type WebArenaConfig = Record<string, WebArenaAppConfig>;

/**
 * Connectivity status for a single app.
 */
export interface AppConnectivityStatus {
  app: string;
  url: string;
  reachable: boolean;
  statusCode?: number;
  error?: string;
  latencyMs: number;
}

/**
 * Result of verifying all WebArena services.
 */
export interface ServiceVerificationResult {
  allReachable: boolean;
  statuses: AppConnectivityStatus[];
  /** Apps that failed connectivity check */
  failures: AppConnectivityStatus[];
}

/**
 * Result of resetting a single app.
 */
export interface AppResetResult {
  app: string;
  strategy: ResetStrategy;
  success: boolean;
  durationMs: number;
  error?: string;
}

/**
 * Result of resetting all apps.
 */
export interface ResetAllResult {
  allSucceeded: boolean;
  results: AppResetResult[];
  totalDurationMs: number;
}

/**
 * Default WebArena app configuration with standard localhost ports.
 * (Req 20.1)
 *
 * Standard ports:
 * - Reddit:    9999
 * - GitLab:    8023
 * - CMS:       7780 (Shopping Admin / Magento Admin)
 * - E-commerce: 7770 (Shopping / Magento Storefront)
 */
export const DEFAULT_WEBARENA_APPS: WebArenaConfig = {
  reddit: {
    url: 'http://localhost:9999',
    resetStrategy: 'shell',
    resetCommand: 'bash prepare.sh',
    composeService: 'reddit',
  },
  gitlab: {
    url: 'http://localhost:8023',
    resetStrategy: 'compose',
    composeService: 'gitlab',
  },
  cms: {
    url: 'http://localhost:7780',
    resetStrategy: 'shell',
    resetCommand: 'bash prepare.sh',
    composeService: 'cms',
  },
  ecommerce: {
    url: 'http://localhost:7770',
    resetStrategy: 'shell',
    resetCommand: 'bash prepare.sh',
    composeService: 'ecommerce',
  },
};

/**
 * Build a WebArenaConfig from ExperimentConfig, merging user-provided
 * app URLs/endpoints with defaults. (Req 20.1)
 */
export function buildWebArenaConfig(
  experimentConfig: Pick<ExperimentConfig, 'webarena'>,
): WebArenaConfig {
  const config: WebArenaConfig = {};
  const userApps = experimentConfig.webarena.apps;

  for (const [name, userApp] of Object.entries(userApps)) {
    const defaults = DEFAULT_WEBARENA_APPS[name];
    config[name] = {
      url: userApp.url,
      resetEndpoint: userApp.resetEndpoint ?? defaults?.resetEndpoint,
      resetCommand: defaults?.resetCommand,
      composeService: defaults?.composeService,
      resetStrategy: defaults?.resetStrategy ?? 'compose',
    };
  }

  return config;
}

/**
 * Check whether a single WebArena app is reachable via HTTP.
 * Uses a GET request with a short timeout.
 */
async function checkAppConnectivity(
  app: string,
  appConfig: WebArenaAppConfig,
  timeoutMs = 10_000,
): Promise<AppConnectivityStatus> {
  const start = Date.now();
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    const response = await fetch(appConfig.url, {
      method: 'GET',
      signal: controller.signal,
      redirect: 'follow',
    });

    clearTimeout(timer);

    return {
      app,
      url: appConfig.url,
      reachable: response.ok || response.status < 500,
      statusCode: response.status,
      latencyMs: Date.now() - start,
    };
  } catch (err) {
    return {
      app,
      url: appConfig.url,
      reachable: false,
      error: err instanceof Error ? err.message : String(err),
      latencyMs: Date.now() - start,
    };
  }
}

/**
 * Verify that all required WebArena services are reachable.
 * Reports per-app connectivity status and any failures. (Req 20.2)
 *
 * WHEN an experiment starts, the platform SHALL verify that all required
 * WebArena services are reachable and report any connectivity failures
 * before proceeding.
 */
export async function verifyWebArenaServices(
  config: WebArenaConfig,
  timeoutMs = 10_000,
): Promise<ServiceVerificationResult> {
  const entries = Object.entries(config);
  const statusPromises = entries.map(([app, appConfig]) =>
    checkAppConnectivity(app, appConfig, timeoutMs),
  );

  const statuses = await Promise.all(statusPromises);
  const failures = statuses.filter((s) => !s.reachable);

  return {
    allReachable: failures.length === 0,
    statuses,
    failures,
  };
}

/**
 * Reset a single WebArena app's state. (Req 20.3)
 *
 * Supports three reset strategies:
 * 1. **endpoint** — HTTP POST to the app's reset endpoint (fastest).
 * 2. **shell** — Execute a shell command (e.g. `bash prepare.sh`, DB restore).
 * 3. **compose** — Docker Compose restart (most reliable, slowest).
 *
 * The strategy is selected from the app config. If the configured strategy
 * fails, no automatic fallback is attempted — the caller should handle
 * failures (e.g. by using separate Docker Compose stacks per variant).
 *
 * ## Reset Mechanism Investigation (Spike Findings)
 *
 * **Reddit (PostgreSQL-backed)**:
 * - `pg_restore` or Docker volume reset can restore state.
 * - Persistent data makes full reset slow (~30s–1min for DB restore).
 * - `bash prepare.sh` works for initial seeding but is not idempotent.
 * - Recommendation: shell-based DB restore for quick iteration;
 *   separate Docker Compose stack per variant for full reliability.
 *
 * **GitLab (heavy stateful app)**:
 * - Docker Compose restart is the most reliable reset but slow (~2–3 min startup).
 * - DB restore is possible but complex (multiple databases, Redis, Gitaly).
 * - No simple HTTP reset endpoint available.
 * - Recommendation: prefer separate Docker Compose stacks per variant level.
 *   Fall back to compose restart only when stack isolation is not feasible.
 *
 * **CMS / Shopping Admin (Magento, MySQL-backed)**:
 * - MySQL dump/restore is reliable and fast (~10–20s).
 * - `bash prepare.sh` works for initial setup and is mostly idempotent.
 * - Recommendation: shell-based `mysql` restore for between-run resets.
 *
 * **E-commerce / Shopping (Magento storefront)**:
 * - Shares the MySQL database with CMS — must be reset together.
 * - Same strategy as CMS applies.
 * - Recommendation: reset CMS and E-commerce as a pair.
 *
 * **Overall Recommendation**:
 * For maximum reliability, prefer separate Docker Compose stacks per variant
 * level when disk space allows (each stack ~2–4 GB). This avoids reset
 * timing issues entirely. Fall back to endpoint/shell reset for quick
 * iteration during development. GitLab and Reddit are the least reliable
 * to reset in-place due to persistent state complexity.
 *
 * @param appName - Name of the app to reset
 * @param config - Full WebArena configuration
 * @param execCommand - Optional command executor (for testability). Defaults to child_process.exec.
 */
export async function resetWebArenaApp(
  appName: string,
  config: WebArenaConfig,
  execCommand?: (cmd: string) => Promise<{ stdout: string; stderr: string }>,
): Promise<AppResetResult> {
  const appConfig = config[appName];
  if (!appConfig) {
    return {
      app: appName,
      strategy: 'compose',
      success: false,
      durationMs: 0,
      error: `Unknown app: ${appName}. Available apps: ${Object.keys(config).join(', ')}`,
    };
  }

  const strategy = inferResetStrategy(appConfig);
  const start = Date.now();

  try {
    switch (strategy) {
      case 'endpoint':
        await resetViaEndpoint(appConfig);
        break;
      case 'shell':
        await resetViaShell(appConfig, execCommand);
        break;
      case 'compose':
        await resetViaCompose(appConfig, execCommand);
        break;
    }

    return {
      app: appName,
      strategy,
      success: true,
      durationMs: Date.now() - start,
    };
  } catch (err) {
    return {
      app: appName,
      strategy,
      success: false,
      durationMs: Date.now() - start,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

/**
 * Infer the best reset strategy from the app's configuration.
 * Priority: explicit resetStrategy > endpoint (if URL provided) > shell > compose.
 */
function inferResetStrategy(appConfig: WebArenaAppConfig): ResetStrategy {
  if (appConfig.resetStrategy) return appConfig.resetStrategy;
  if (appConfig.resetEndpoint) return 'endpoint';
  if (appConfig.resetCommand) return 'shell';
  return 'compose';
}

/** Reset via HTTP POST to the app's reset endpoint. */
async function resetViaEndpoint(appConfig: WebArenaAppConfig): Promise<void> {
  if (!appConfig.resetEndpoint) {
    throw new Error('No reset endpoint configured');
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30_000);

  try {
    const response = await fetch(appConfig.resetEndpoint, {
      method: 'POST',
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Reset endpoint returned HTTP ${response.status}`);
    }
  } finally {
    clearTimeout(timer);
  }
}

/** Reset via shell command execution. */
async function resetViaShell(
  appConfig: WebArenaAppConfig,
  execCommand?: (cmd: string) => Promise<{ stdout: string; stderr: string }>,
): Promise<void> {
  if (!appConfig.resetCommand) {
    throw new Error('No reset command configured');
  }

  const exec = execCommand ?? defaultExecCommand;
  await exec(appConfig.resetCommand);
}

/** Reset via Docker Compose restart. */
async function resetViaCompose(
  appConfig: WebArenaAppConfig,
  execCommand?: (cmd: string) => Promise<{ stdout: string; stderr: string }>,
): Promise<void> {
  const service = appConfig.composeService;
  if (!service) {
    throw new Error('No Docker Compose service name configured');
  }

  const exec = execCommand ?? defaultExecCommand;
  await exec(`docker compose restart ${service}`);
}

/** Default command executor using Node.js child_process. */
async function defaultExecCommand(
  cmd: string,
): Promise<{ stdout: string; stderr: string }> {
  const { exec } = await import('node:child_process');
  const { promisify } = await import('node:util');
  const execAsync = promisify(exec);
  return execAsync(cmd, { timeout: 180_000 });
}

/**
 * Reset all WebArena apps, logging results. (Req 20.3)
 *
 * Resets are executed sequentially to avoid resource contention
 * (especially for compose-based resets that restart Docker containers).
 *
 * @param config - Full WebArena configuration
 * @param execCommand - Optional command executor (for testability)
 * @param logger - Optional logger function (defaults to console.log)
 */
export async function resetAllWebArenaApps(
  config: WebArenaConfig,
  execCommand?: (cmd: string) => Promise<{ stdout: string; stderr: string }>,
  logger: (message: string) => void = console.log,
): Promise<ResetAllResult> {
  const start = Date.now();
  const results: AppResetResult[] = [];

  for (const appName of Object.keys(config)) {
    logger(`[WebArena] Resetting ${appName}...`);
    const result = await resetWebArenaApp(appName, config, execCommand);
    results.push(result);

    if (result.success) {
      logger(
        `[WebArena] ${appName} reset OK (${result.strategy}, ${result.durationMs}ms)`,
      );
    } else {
      logger(
        `[WebArena] ${appName} reset FAILED (${result.strategy}): ${result.error}`,
      );
    }
  }

  return {
    allSucceeded: results.every((r) => r.success),
    results,
    totalDurationMs: Date.now() - start,
  };
}
