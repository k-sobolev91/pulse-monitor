import pytest
from django.test import TestCase
from unittest.mock import patch, MagicMock
from monitor.checks.http_check import HTTPChecker
from django.utils import timezone
from monitor.models import Service, Check


@pytest.mark.django_db
class TestHTTPChecker(TestCase):
    """Тесты для HTTP проверки сервисов"""

    def setUp(self):
        self.service = Service.objects.create(
            name="Test API",
            url="https://api.example.com",
            check_interval=300,
            timeout=10
        )

    @patch('monitor.checks.http_check.requests.get')
    def test_successful_check_200(self, mock_get):
        """Проверка успешного ответа (200)"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        checker = HTTPChecker(self.service)
        check = checker.check()

        self.assertEqual(check.status, 'up')
        self.assertEqual(check.status_code, 200)
        self.assertIsNotNone(check.response_time)
        self.assertEqual(self.service.status, 'up')

    @patch('monitor.checks.http_check.requests.get')
    def test_failed_check_500(self, mock_get):
        """Проверка ошибки сервера (500)"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        checker = HTTPChecker(self.service)
        check = checker.check()

        self.assertEqual(check.status, 'down')
        self.assertEqual(check.status_code, 500)
        self.assertIn('HTTP 500', check.error_message)

    @patch('monitor.checks.http_check.requests.get')
    def test_timeout_check(self, mock_get):
        """Проверка таймаута"""
        from requests import Timeout
        mock_get.side_effect = Timeout("Connection timeout")

        checker = HTTPChecker(self.service)
        check = checker.check()

        self.assertEqual(check.status, 'timeout')
        self.assertIn('Timeout', check.error_message)

    @patch('monitor.checks.http_check.requests.get')
    def test_connection_error(self, mock_get):
        """Проверка ошибки соединения"""
        from requests import ConnectionError
        mock_get.side_effect = ConnectionError("Failed to connect")

        checker = HTTPChecker(self.service)
        check = checker.check()

        self.assertEqual(check.status, 'down')
        self.assertIn('Connection error', check.error_message)

    def test_check_saved_to_database(self):
        """Проверка, что результаты сохраняются в БД"""
        with patch('monitor.checks.http_check.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            checker = HTTPChecker(self.service)
            checker.check()

            self.assertEqual(Check.objects.count(), 1)
            check = Check.objects.first()
            self.assertEqual(check.service, self.service)
            self.assertEqual(check.status, 'up')

@pytest.mark.django_db
class TestTasks(TestCase):
    """Тесты для Celery задач"""

    def setUp(self):
        self.service = Service.objects.create(
            name="Test Service",
            url="https://example.com",
            check_interval=300,
            timeout=10
        )

    @patch('monitor.tasks.HTTPChecker')
    def test_check_service_task(self, mock_checker_class):
        """Проверка задачи check_service"""
        from monitor.tasks import check_service

        mock_checker = MagicMock()
        mock_check = MagicMock()
        mock_check.status = 'up'
        mock_checker.check.return_value = mock_check
        mock_checker_class.return_value = mock_checker

        result = check_service(self.service.id)

        self.assertIn('Test Service', result)
        self.assertIn('up', result)
        mock_checker_class.assert_called_once()

    def test_check_service_task_inactive_service(self):
        """Проверка, что неактивный сервис не проверяется"""
        from monitor.tasks import check_service

        self.service.is_active = False
        self.service.save()

        result = check_service(self.service.id)

        self.assertIn('not found or inactive', result)

    def test_check_service_task_nonexistent(self):
        """Проверка обработки несуществующего сервиса"""
        from monitor.tasks import check_service

        result = check_service(99999)

        self.assertIn('not found or inactive', result)

    @patch('monitor.tasks.check_service.delay')
    def test_check_all_services_triggers_due_checks(self, mock_delay):
        """Проверка, что check_all_services запускает проверку сервисов, которым пора"""
        from monitor.tasks import check_all_services

        # Сервис без last_checked должен быть проверен
        result = check_all_services()

        mock_delay.assert_called_once_with(self.service.id)
        self.assertIn('Triggered 1', result)

    @patch('monitor.tasks.check_service.delay')
    def test_check_all_services_skips_recent_checks(self, mock_delay):
        """Проверка, что недавно проверенные сервисы пропускаются"""
        from monitor.tasks import check_all_services

        self.service.last_checked = timezone.now()
        self.service.save()

        result = check_all_services()

        mock_delay.assert_not_called()
        self.assertIn('Triggered 0', result)
