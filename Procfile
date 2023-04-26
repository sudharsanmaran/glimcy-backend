release: ./release-tasks.sh
web: gunicorn glimcy.wsgi --log-file -
worker: celery -A glimcy worker --concurrency=3 -E -l INFO
beat: celery -A glimcy beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler