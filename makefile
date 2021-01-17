RUN = poetry run

.PHONY: fix test setup ipython

fix:
	$(RUN) pre-commit run --all-files

test:
	$(RUN) python -m unittest $(TESTS)

setup:
	pip3 install --user poetry
	poetry install
	$(RUN) pre-commit install
	$(RUN) ipython profile create --ProfileDir.location=./.ipython_profile
	./make-pyrightconfig.sh

ipython:
	$(RUN) ipython --ProfileDir.location=./.ipython_profile
