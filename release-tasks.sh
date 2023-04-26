#!/bin/bash
pip install -r backend/requirements/local.txt

python backend/manage.py makemigrations

python backend/manage.py migrate

#custom Python script to  populate celery intervals and tasks
python backend/manage.py populate_celery_beat_tables
