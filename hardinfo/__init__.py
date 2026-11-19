"""HARDINFO - Windows System Diagnostics and Gaming Optimizer."""

from hardinfo.bootstrap import ensure_dependencies

# Any import of the package (including submodules) guarantees that runtime
# dependencies are available, like the original single-file launcher did.
ensure_dependencies()

from hardinfo.constants import APP_VERSION  # noqa: E402

__version__ = APP_VERSION


def run_app(argv: list[str] | None = None) -> int:
    """Programmatic entry point kept for backward compatibility."""
    from hardinfo.cli import main

    return main(argv)


__all__ = ["run_app", "APP_VERSION", "__version__"]
