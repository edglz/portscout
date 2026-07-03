"""Portscout — a friendly, graphical TUI front-end for nmap.

The package is organized following the hexagonal (ports & adapters) architecture:

    domain/          Pure business core: value objects, entities and port
                     (interface) definitions. No I/O, no third-party imports.
    application/     Use cases that orchestrate the domain via the ports.
    infrastructure/  Adapters that implement the ports (nmap, config, deps).
    presentation/    The Textual TUI (a driving adapter).

`bootstrap.py` is the composition root that wires adapters into use cases.
"""

__version__ = "0.1.0"
