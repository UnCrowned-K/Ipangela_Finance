.PHONY: install build test

install:
	pip install -r requirements.txt

build:
	python3 app.py

test: 
# 	testing will be placed here