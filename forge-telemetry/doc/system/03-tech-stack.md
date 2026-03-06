# §3 — Tech Stack

## Runtime

| Component | Current Contract |
|-----------|------------------|
| Python | `>=3.9` |
| Packaging | `setuptools` |
| Validation | `pydantic>=2.0.0` |
| DB access | `sqlalchemy>=2.0.0` |
| Env loading | `python-dotenv>=1.0.0` |

## Package Metadata

`setup.py` currently declares:

- package name: `forge-telemetry`
- version: `0.1.0`
- description: `Unified telemetry client for the Forge ecosystem`
- license classifier: MIT

These are package metadata facts, not runtime governance authority.

## Supported Python Versions

The current package metadata lists classifiers for:

- Python 3.9
- Python 3.10
- Python 3.11

The runtime minimum in packaging is `>=3.9`.

## Snapshot Note

This repo is intentionally small. File totals and inventory counts are snapshot facts and are not repeated here as architecture doctrine.
