black-check: ## Check syntax via black
	black --skip-magic-trailing-comma --target-version py310 --check --diff .

black-reformat: ## Reformat via black
	black --skip-magic-trailing-comma --target-version py310 .

flake8:  ## Check via flake8
	flake8 .

isort: ## Reformat via isort
	isort --case-sensitive --multi-line 3 --trailing-comma --use-parentheses .

mypy:  ## Run mypy
	mypy --ignore-missing-imports archon

pytest:
	pytest

reformat: ## Reformat codebase
	make isort
	make black-reformat
