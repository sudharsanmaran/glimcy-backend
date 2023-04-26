#!/bin/bash

python manage.py makemigrations

python manage.py migrate

#custom Python script to  populate celery intervals and tasks
python manage.py populate_celery_beat_tables
