"""Per-stage verifiers — each module exports a `Verifier` class with a
`run() -> StageReport` method.

Importing this package does not load any data; each stage loads on demand.
"""
