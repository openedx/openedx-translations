.PHONY: piptools upgrade

piptools:
	pip install -q -r requirements/pip_tools.txt

upgrade: piptools  ## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	pip-compile --alow-unsafe --rebuild --upgrade -o requirements/pip.txt requirements/pip.in
	pip-compile --rebuild --upgrade -o requirements/pip_tools.txt requirements/pip_tools.in
	pip install -qr requirements/pip.txt
	pip install -qr requirements/pip_tools.txt
	pip-compile --rebuild --upgrade -o requirements/translations.txt requirements/translations.in
