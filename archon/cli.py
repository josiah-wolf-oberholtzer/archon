import argparse
from pathlib import Path

from .pipeline import run


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    pipeline_parser = subparsers.add_parser("run-pipeline")
    pipeline_parser.add_argument("--input", metavar="DIR", required=True, type=Path)
    pipeline_parser.add_argument("--output", metavar="FILE", required=True, type=Path)
    return parser.parse_args()


def main(args=None):
    parsed_args = parse_args(args)
    if parsed_args.command == "run-pipeline":
        run(input_path=parsed_args.input, output_path=parsed_args.output)
