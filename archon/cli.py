import argparse
from pathlib import Path

from . import harness, pipeline


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-level", default="info")
    subparsers = parser.add_subparsers(dest="command", required=True)
    # run the harness
    harness_parser = subparsers.add_parser("run-harness")
    harness_parser.add_argument("--input", metavar="FILE", required=True, type=Path)
    # run the pipeline
    pipeline_parser = subparsers.add_parser("run-pipeline")
    pipeline_parser.add_argument("--input", metavar="DIR", required=True, type=Path)
    pipeline_parser.add_argument("--output", metavar="FILE", required=True, type=Path)
    # validate analysis
    validate_parser = subparsers.add_parser("validate-analysis")
    validate_parser.add_argument("--input", metavar="FILE", required=True, type=Path)
    return parser.parse_args()


def main(args=None):
    parsed_args = parse_args(args)
    if parsed_args.command == "run-pipeline":
        pipeline.run(input_path=parsed_args.input, output_path=parsed_args.output)
    if parsed_args.command == "validate-analysis":
        pipeline.validate(analysis_path=parsed_args.input)
    if parsed_args.command == "run-harness":
        harness.run(analysis_path=parsed_args.input)
