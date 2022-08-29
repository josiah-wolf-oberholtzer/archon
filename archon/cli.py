import argparse
from pathlib import Path

from .config import ArchonConfig


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-level", default="info")
    subparsers = parser.add_subparsers(dest="command", required=True)
    # run the harness
    harness_parser = subparsers.add_parser("run-harness")
    harness_parser.add_argument("path", help="path to analysis JSON", type=Path)
    harness_parser.add_argument(
        "--history-size",
        default=10,
        metavar="N",
        help="windows size for live analysis (default: %(default)d)",
        type=int,
    )
    harness_parser.add_argument(
        "--mfcc-count",
        default=13,
        help="number of MFCC coefficients to query against (default: %(default)d)",
        metavar="N",
        type=int,
    )
    harness_parser.add_argument(
        "--use-mfcc",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="use MFCCs for querying (default: %(default)s)",
    )
    harness_parser.add_argument(
        "--use-pitch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="use pitch for querying (default: %(default)s)",
    )
    harness_parser.add_argument(
        "--use-spectral",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="use spectral features for querying (default: %(default)s)",
    )
    # run the pipeline
    pipeline_parser = subparsers.add_parser("run-pipeline")
    pipeline_parser.add_argument("path", help="path to analysis JSON", type=Path)
    # validate analysis
    validate_parser = subparsers.add_parser("validate-analysis")
    validate_parser.add_argument("path", help="path to analysis JSON", type=Path)
    return parser.parse_args()


def main(args=None):
    parsed_args = parse_args(args)
    config = ArchonConfig(analysis_path=parsed_args.path.resolve())
    if not any([config.use_pitch, config.use_spectral, config.use_mfcc]):
        raise ValueError
    if parsed_args.command == "run-pipeline":
        from . import pipeline

        pipeline.run(config)
    if parsed_args.command == "validate-analysis":
        from . import pipeline

        pipeline.validate(config)
    if parsed_args.command == "run-harness":
        from . import harness

        config.history_size = parsed_args.history_size
        config.mfcc_count = parsed_args.mfcc_count
        config.use_mfcc = parsed_args.use_mfcc
        config.use_pitch = parsed_args.use_pitch
        config.use_spectral = parsed_args.use_spectral
        harness.run(config)
