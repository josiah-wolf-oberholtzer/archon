import logging

from .cli import main

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger("archon").setLevel(logging.INFO)
    main()
