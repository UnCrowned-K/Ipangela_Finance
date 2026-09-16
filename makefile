.PHONY: install build test

install:
	pip install -r requirements.txt

build:
	python3 app.py

test:
	python3 -m pytest -q