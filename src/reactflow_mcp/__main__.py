"""Entry point: `python -m reactflow_mcp` or `reactflow-mcp`."""

from reactflow_mcp.server import mcp


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
