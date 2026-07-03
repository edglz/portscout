# Contributing to Portscout

Thanks for your interest in improving Portscout. Contributions of all kinds are
welcome: bug reports, documentation, tests, new scan profiles, and features.

## Getting started

1. Fork and clone the repository.
2. Create a virtual environment and install the dev extras:

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. Create a branch: `git checkout -b feature/short-description`.

## Before you open a pull request

Please make sure the quality gate passes locally:

```bash
ruff check .      # lint
mypy              # type-check
pytest            # tests
```

- Keep the **domain** layer free of third-party imports. Business rules belong in
  `domain/` and `application/`; anything touching nmap, the filesystem, or the terminal
  belongs in an adapter under `infrastructure/` or `presentation/`.
- Add or update tests for any behavior change. The domain and adapters are unit-tested
  without touching the network.
- Follow the existing style; `ruff` enforces most of it.

## Architecture guidelines

Portscout uses a hexagonal (ports and adapters) architecture. When adding a capability:

- Define the abstraction as a **port** (a `Protocol`) in `domain/ports.py`.
- Implement it as an **adapter** in `infrastructure/`.
- Wire it up in `bootstrap.py` — the only place that knows about concrete adapters.

## Reporting bugs and requesting features

Please use the issue templates. Include your OS, Python version, and nmap version
(`nmap --version`) for bug reports.

## Code of Conduct

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).
