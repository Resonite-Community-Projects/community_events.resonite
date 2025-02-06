import sys
import argparse
import logging
from mkdocs.commands.serve import serve
from mkdocs.config.base import load_config

def run():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Run MkDocs server")
    parser.add_argument("command", choices=["serve"], help="Command to run (only 'serve' is supported)")
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        default="0.0.0.0:8002",
        help="Bind address (default: 0.0.0.0:8002)",
        metavar="<IP:PORT>"
    )

    args = parser.parse_args(sys.argv[1:])

    if args.command == "serve":
        logging.getLogger("mkdocs").setLevel(logging.INFO)
        config = load_config()
        serve(dev_addr=args.address, config=config)