import requests
import time
from django.utils import timezone
from monitor.models import Service, Check


class HTTPChecker:
    """Проверяет доступность HTTP сервисов"""

    def __init__(self, service: Service):
        self.service = service

    def check(self) -> Check:
        """Выполнить одну проверку сервиса"""
        start_time = time.time()
        error_message = None
        status = 'unknown'
        status_code = None
        response_time = None
        old_status = self.service.status

        try:
            response = requests.get(
                self.service.url,
                timeout=self.service.timeout,
                allow_redirects=True
            )
            response_time = (time.time() - start_time) * 1000
            status_code = response.status_code

            if 200 <= status_code < 400:
                status = 'up'
            else:
                status = 'down'
                error_message = f"HTTP {status_code}"

        except requests.Timeout:
            response_time = (time.time() - start_time) * 1000
            status = 'timeout'
            error_message = f"Timeout after {self.service.timeout}s"

        except requests.ConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            status = 'down'
            error_message = f"Connection error: {str(e)[:100]}"

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = 'error'
            error_message = f"Error: {str(e)[:100]}"

        check = Check.objects.create(
            service=self.service,
            status=status,
            response_time=response_time,
            status_code=status_code,
            error_message=error_message
        )

        self.service.status = status
        self.service.last_checked = timezone.now()

        if old_status != status:
            self.service.last_status_change = timezone.now()
            # Отправить алерт при изменении статуса
            from monitor.alerts import TelegramAlert
            alert = TelegramAlert()
            alert.status_changed(self.service, old_status, status)

        self.service.save()

        return check