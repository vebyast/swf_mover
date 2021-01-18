RUN = poetry run
CONVERT = convert
MOGRIFY = mogrify
COMPARE = compare
EXPORTER = cargo run --manifest-path=$(HOME)/src/ruffle/Cargo.toml --package=exporter --

.PHONY: fix test setup ipython

fix:
	$(RUN) pre-commit run --all-files

test:
	$(RUN) python -m unittest $(TESTS)

integration:
	$(RUN) python -m swf_mover.swf_mover --swf=testdata/avatar05_SkirtRight17.swf
	$(EXPORTER) testdata/avatar05_SkirtRight17.swf testdata/avatar05_SkirtRight17.png
	$(EXPORTER) testdata/avatar05_SkirtRight17.moved.swf testdata/avatar05_SkirtRight17.moved.png
	$(MOGRIFY) -transparent white -trim testdata/avatar05_SkirtRight17.png
	$(MOGRIFY) -transparent white -trim testdata/avatar05_SkirtRight17.moved.png
	-$(COMPARE) -compose src testdata/avatar05_SkirtRight17.png testdata/avatar05_SkirtRight17.moved.png testdata/avatar05_SkirtRight17.diff.png

setup:
	pip3 install --user poetry
	poetry install
	$(RUN) pre-commit install
	$(RUN) ipython profile create --ProfileDir.location=./.ipython_profile
	./make-pyrightconfig.sh

ipython:
	$(RUN) ipython --ProfileDir.location=./.ipython_profile
