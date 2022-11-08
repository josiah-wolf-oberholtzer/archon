import argparse
import dataclasses
from pathlib import Path
from typing import Tuple

from . import harness, pipeline
from .config import ArchonConfig


def build_harness_subparser(subparsers):
    parser = subparsers.add_parser("run-harness")
    parser.add_argument("path", help="path to analysis JSON", type=Path)
    parser.add_argument(
        "--history-size",
        default=10,
        metavar="N",
        help="windows size for live analysis (default: %(default)d)",
        type=int,
    )
    parser.add_argument(
        "--mfcc-count",
        default=13,
        help="number of MFCC coefficients to query against (default: %(default)d)",
        metavar="N",
        type=int,
    )
    parser.add_argument(
        "--use-mfcc",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="use MFCCs for querying (default: %(default)s)",
    )
    parser.add_argument(
        "--use-pitch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="use pitch for querying (default: %(default)s)",
    )
    parser.add_argument(
        "--use-spectral",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="use spectral features for querying (default: %(default)s)",
    )
    parser.add_argument("--input-count", type=int, default=8)
    parser.add_argument("--output-count", type=int, default=8)
    parser.add_argument("--input-device", required=False)
    parser.add_argument("--output-device", required=False)
    parser.add_argument(
        "--input-bus", type=int, default=8, help="bus ID to run analysis against"
    )
    parser.add_argument(
        "--output-bus", type=int, default=0, help="bus ID to output audio to"
    )


def build_pipeline_subparser(subparsers):
    parser = subparsers.add_parser("run-pipeline")
    parser.add_argument("path", help="path to analysis JSON", type=Path)
    parser.add_argument("--partition-hop-in-ms", default=500.0, type=float)
    parser.add_argument("--partition-sizes-in-ms", nargs="+", type=float)


def build_validate_subparser(subparsers):
    parser = subparsers.add_parser("validate-analysis")
    parser.add_argument("path", help="path to analysis JSON", type=Path)


def parse_args(args=None) -> Tuple[str, ArchonConfig]:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_harness_subparser(subparsers)
    build_pipeline_subparser(subparsers)
    build_validate_subparser(subparsers)
    parsed_args = vars(parser.parse_args())
    command = parsed_args.pop("command")
    analysis_path = parsed_args.pop("path").resolve()
    config = dataclasses.replace(
        ArchonConfig(analysis_path=analysis_path), **parsed_args
    )
    config.validate()
    return command, config


def main(args=None):
    command, config = parse_args()
    {
        "run-pipeline": pipeline.run,
        "validate-analysis": pipeline.validate,
        "run-harness": harness.run,
    }[command](config)
