// Module 5: HAR Recorder — Type definitions for capture and replay

import type { Page } from 'playwright';

/** Options for HAR capture */
export interface HarCaptureOptions {
  urls: string[];
  waitAfterLoadMs: number;
  concurrency: number;
  outputDir: string;
  /** Optional browser instance from caller. If not provided, captureHar launches its own. */
  browser?: import('playwright').Browser;
}

/** Metadata stored alongside a HAR recording */
export interface HarMetadata {
  recordingTimestamp: string;
  targetUrl: string;
  geoRegion: string;
  sectorClassification: string;
  pageLanguage: string;
}

/** Result of capturing a single HAR recording */
export interface HarCaptureResult {
  harFilePath: string;
  metadata: HarMetadata;
  success: boolean;
  error?: string;
}

/** Options for replaying a HAR file */
export interface HarReplayOptions {
  harFilePath: string;
  unmatchedRequestBehavior: 'return-404' | 'passthrough';
}

/** An active HAR replay session */
export interface ReplaySession {
  page: Page;
  coverageGap: number;
  functionalUnmatched: string[];
  nonFunctionalUnmatched: string[];
  totalUnmatched: string[];
  isLowFidelity: boolean;
}
