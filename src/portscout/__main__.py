"""Console entry point: build the container and launch the TUI."""

from __future__ import annotations

import sys

from .bootstrap import build_container
from .presentation.app import PortscoutApp


def main() -> int:
    container = build_container()
    app = PortscoutApp(
        scan_service=container.scan,
        dependency_service=container.dependencies,
        config_service=container.config,
    )
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
