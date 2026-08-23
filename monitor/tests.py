import pytest
from django.test import TestCase
from unittest.mock import patch, MagicMock
from monitor.models import Service, Check
from monitor.checks.http_check import HTTPChecker


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