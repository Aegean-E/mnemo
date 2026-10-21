"""`python -m mnemo` runs the CLI and exits with its code."""

import sys

from mnemo.cli import main

if __name__ == "__main__":
    sys.exit(main())
