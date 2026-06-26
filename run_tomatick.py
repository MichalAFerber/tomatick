"""py2app entry point. Kept at repo root because py2app wants a script file.

For development, prefer ``python -m tomatick``.
"""

from tomatick.app import main

if __name__ == "__main__":
    main()
