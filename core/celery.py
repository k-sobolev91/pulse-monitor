import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-all-services': {
        'task': 'monitor.tasks.check_all_services',
        'schedule': 60.0,  # каждую минуту проверяем, каким сервисам пора на проверку
    },
}