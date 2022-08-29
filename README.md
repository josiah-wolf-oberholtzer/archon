# Archon

https://github.com/mpoliks/archon re-implemented in pure Python.

## Install 

```
pip install -r requirements.txt
```

## Run the test suite

```
pytest
```

## Run the pipeline

Given a target `analysis.json` path, analyze audio relative to that target path:

```
➜ python -m archon run-pipeline --help
usage: __main__.py run-pipeline [-h] path

positional arguments:
  path        path to analysis JSON

options:
  -h, --help  show this help message and exit
```

```
python -m archon run-pipeline path/to/analysis.json
```

## Run the harness

Given a pre-existing `analysis.json` path, load the analysis into the database
and launch the synthesis engine:

```
➜ python -m archon run-harness --help
usage: __main__.py run-harness [-h] [--history-size N] [--mfcc-count N] [--use-mfcc | --no-use-mfcc] [--use-pitch | --no-use-pitch] [--use-spectral | --no-use-spectral] path

positional arguments:
  path                  path to analysis JSON

options:
  -h, --help            show this help message and exit
  --history-size N      windows size for live analysis (default: 10)
  --mfcc-count N        number of MFCC coefficients to query against (default: 13)
  --use-mfcc, --no-use-mfcc
                        use MFCCs for querying (default: True) (default: True)
  --use-pitch, --no-use-pitch
                        use pitch for querying (default: True) (default: True)
  --use-spectral, --no-use-spectral
                        use spectral features for querying (default: True) (default: True)
```
