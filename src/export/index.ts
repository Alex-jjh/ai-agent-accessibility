// Data export — manifest generation, CSV export, JSON store
export { generateManifest, collectSoftwareVersions } from './manifest.js';
export { exportToCsv, scrubPii, buildSiteMapping } from './csv.js';
export type { ClassifiedRecord, CsvExportResult } from './csv.js';
export { ExperimentStore } from './store.js';
export type { StoreConfig } from './store.js';
