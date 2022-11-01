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
    harness_parser.add_argument("--inputs", type=int, default=8)
    harness_parser.add_argument("--outputs", type=int, default=8)
    harness_parser.add_argument(
        "--input-bus", type=int, default=8, help="bus ID to run analysis against"
    )
    harness_parser.add_argument(
        "--output-bus", type=int, default=0, help="bus ID to output audio to"
    )
    # run the pipeline
    pipeline_parser = subparsers.add_parser("run-pipeline")
    pipeline_parser.add_argument("path", help="path to analysis JSON", type=Path)
    pipeline_parser.add_argument("--partition-hop-in-ms", default=500.0, type=float)
    pipeline_parser.add_argument("--partition-sizes-in-ms", nargs="+", type=float)

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

        config.partition_sizes_in_ms = parsed_args.partition_sizes_in_ms
        config.partition_hop_in_ms = parsed_args.partition_hop_in_ms
        pipeline.run(config)
    if parsed_args.command == "validate-analysis":
        from . import pipeline

        pipeline.validate(config)
    if parsed_args.command == "run-harness":
        from . import harness

        config.history_size = parsed_args.history_size
        config.input_bus = parsed_args.input_bus
        config.inputs = parsed_args.inputs
        config.mfcc_count = parsed_args.mfcc_count
        config.output_bus = parsed_args.output_bus
        config.outputs = parsed_args.outputs
        config.use_mfcc = parsed_args.use_mfcc
        config.use_pitch = parsed_args.use_pitch
        config.use_spectral = parsed_args.use_spectral
        harness.run(config)
