// Module 5: HAR Recorder — capture and replay pipeline for Track B
export { captureHar } from './capture/capture.js';
export { createReplaySession, classifyRequest, computeCoverageGap } from './replay/replay.js';
export type {
  HarCaptureOptions,
  HarCaptureResult,
  HarMetadata,
  HarReplayOptions,
  ReplaySession,
} from './types.js';
