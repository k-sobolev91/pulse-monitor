from celery import shared_task
from django.utils import timezone
from monitor.models import Service
from monitor.checks.http_check import HTTPChecker


@shared_task
def check_service(service_id):
    """Проверить один сервис"""
    try:
        service = Service.objects.get(id=service_id, is_active=True)
    except Service.DoesNotExist:
        return f"Service {service_id} not found or inactive"

    checker = HTTPChecker(service)
    check = checker.check()

    return f"Checked {service.name}: {check.status}"


@shared_task
def check_all_services():
    """Проверить все активные сервисы, которым пора на проверку"""
    now = timezone.now()
    services = Service.objects.filter(is_active=True)

    checked_count = 0
    for service in services:
        # Проверяем, пора ли сервису на проверку
        if service.last_checked is None:
            should_check = True
        else:
            seconds_since_last_check = (now - service.last_checked).total_seconds()
            should_check = seconds_since_last_check >= service.check_interval

        if should_check:
            check_service.delay(service.id)
            checked_count += 1

    return f"Triggered {checked_count} service checks"