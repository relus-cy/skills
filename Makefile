.PHONY: test verify

test:
	python -m unittest discover -s tests -v

verify:
	bash scripts/verify.sh
