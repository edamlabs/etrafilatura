.DEFAULT_GOAL := help
.PHONY: help build build-release test lint format types arch check cargo-fmt clean dist stress integration suite publish docs serve cov licenses health apidiff fidelity benchmark

help:             ## list targets
	@awk 'BEGIN{FS=":.*## "} /^[a-z][a-zA-Z0-9_-]*:.*##/ {printf "  \033[32m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build:            ## compile native extension into the venv (debug)
	uv run maturin develop

build-release:    ## compile native extension into the venv (release)
	uv run maturin develop --release

test:             ## unit suite with coverage gate
	uv run pytest --cov --cov-report=term-missing -q

stress:           ## concurrency and volume suite only
	uv run pytest -m stress -q -p no:randomly --timeout=300

integration:      ## live network suite
	uv run pytest -m integration -q --timeout=300

suite:            ## everything, one 100% coverage gate
	uv run pytest -m "" --cov --cov-report=term-missing -q --timeout=300

lint:             ## ruff check
	uv run ruff check src tests tools

format:           ## ruff format
	uv run ruff format src tests tools

types:            ## ty static type check
	uv run ty check

arch:             ## tach import contracts
	uv run tach check

check: lint types arch build test ## full gate

cov:              ## Rust line coverage driven by the Python suite (gate: 90%)
	tools/coverage.sh 90

fidelity:         ## extraction agreement vs Python trafilatura (ARGS=--update rewrites baseline)
	uv run --group bench python -m tools.fidelity $(ARGS)

benchmark:        ## etrafilatura vs trafilatura timings -> docs/benchmark.md + chart
	uv run --group bench pytest -m bench -q -p no:randomly -p no:cacheprovider --benchmark-json=bench.json
	uv run --group bench python -m tools.benchchart bench.json

licenses:         ## regenerate THIRD_PARTY_LICENSES.md from the Rust dependency tree
	cargo about generate about.hbs | tr -d "\r" > THIRD_PARTY_LICENSES.md

health:           ## dependency health report (archived, stale, dormant)
	uv run python tools/health.py --output health.md --token "$$(gh auth token 2>/dev/null)"

apidiff:          ## engine public API diff: make apidiff OLD=0.4.0 NEW=0.5.0
	tools/apidiff.sh trafilatura $(OLD) $(NEW) nchapman/trafilatura-rs upstream-context

cargo-fmt:        ## rustfmt the native crate
	cargo fmt

clean:            ## remove build artifacts
	rm -rf target dist site .pytest_cache .ruff_cache htmlcov coverage.xml coverage.lcov .coverage health.md upstream-context bench.json .benchmarks

dist:             ## build release wheels + sdist -> dist/
	uv run maturin build --release --sdist --out dist

docs:             ## build the documentation (strict, fails on broken links)
	uv run mkdocs build --strict

serve:            ## serve the documentation locally
	uv run mkdocs serve -a 127.0.0.1:8000

publish:          ## build and upload to PyPI
	uv run maturin publish
