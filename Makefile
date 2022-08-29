clean:
	find . -name '*.__pycache__' | xargs rm -Rf
	find . -name '*.egg-info' | xargs rm -Rf
	find . -name '*.pyc' | xargs rm -Rf
	find . -name '*cache' | xargs rm -Rf

black-check: ## Check syntax via black
	black --check --diff .

black-reformat: ## Reformat via black
	black .

flake8:  ## Check via flake8
	flake8 .

isort: ## Reformat via isort
	isort .

mypy:  ## Run mypy
	mypy archon

pytest:
	pytest

reformat: ## Reformat codebase
	make isort
	make black-reformat
