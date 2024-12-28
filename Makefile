PYTHON_SETUP	=	python setup.py

isort:
	find . -name '*.py' | xargs -I {} echo '"{}"' | xargs isort --profile black

spell:
	find . -name '*.py' | xargs -I {} echo '"{}"' | xargs codespell 

djhtml:
	find . -name '*.html' | xargs -I {} echo '"{}"' | xargs djhtml

black: isort djhtml
	find . -name '*.py' | xargs -I {} echo '"{}"' | xargs black -l 119


check:
	python manage.py check

commit:	_commit

_commit: isort black check
	git add apps/
	git commit -a
	git push origin

restart:
	sudo systemctl restart gunicorn
	sudo systemctl restart celery
	sudo systemctl restart celery_beat

FORCE:
