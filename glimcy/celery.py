import os
import ssl

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "glimcy.settings")
app = Celery("glimcy", broker_use_ssl={
    'ssl_cert_reqs': ssl.CERT_NONE
},
             redis_backend_use_ssl={
                 'ssl_cert_reqs': ssl.CERT_NONE
             })
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
