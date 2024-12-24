PYTHON_SETUP	=	python setup.py

isort:
	find . -name '*.py' -exec isort --profile black {} \;

spell:
	-find . -name '*.py' | xargs codespell -w

black: isort
	find . -name '*.py' -exec black -l 119 {} \;


check:
	python manage.py check

commit:	_commit

_commit: spell isort black check
	git add apps/
	git commit -a
	git push origin

restart:
	sudo systemctl restart gunicorn
	sudo systemctl restart celery
	sudo systemctl restart celery_beat

FORCE:
