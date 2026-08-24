import pytest
from django.test import TestCase
from unittest.mock import patch, MagicMock
from monitor.checks.http_check import HTTPChecker
import os
from django.utils import timezone
from monitor.models import Service, Check
from rest_framework.test import APIClient
from rest_framework import status as http_status


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
        self.service.refresh_from_db()  # Обновить объект из БД

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

        self.service.refresh_from_db()  # Обновить объект из БД
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
        self.service.refresh_from_db()  # Обновить объект из БД


        self.assertEqual(check.status, 'timeout')
        self.assertIn('Timeout', check.error_message)

    @patch('monitor.checks.http_check.requests.get')
    def test_connection_error(self, mock_get):
        """Проверка ошибки соединения"""
        from requests import ConnectionError
        mock_get.side_effect = ConnectionError("Failed to connect")

        checker = HTTPChecker(self.service)
        check = checker.check()
        self.service.refresh_from_db()  # Обновить объект из БД

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
@pytest.mark.django_db
class TestServiceAPI(TestCase):
    """Тесты для REST API сервисов"""

    def setUp(self):
        self.client = APIClient()
        self.service = Service.objects.create(
            name="Test API Service",
            url="https://api.example.com",
            status='up'
        )

    def test_list_services(self):
        """GET /api/services/ — список сервисов"""
        response = self.client.get('/api/services/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], "Test API Service")

    def test_retrieve_service(self):
        """GET /api/services/{id}/ — детали сервиса"""
        response = self.client.get(f'/api/services/{self.service.id}/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Test API Service")
        self.assertIn('recent_checks', response.data)

    def test_create_service(self):
        """POST /api/services/ — создать сервис"""
        data = {
            'name': 'New Service',
            'url': 'https://new.example.com',
            'check_interval': 600,
            'timeout': 15
        }
        response = self.client.post('/api/services/', data)
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        self.assertTrue(Service.objects.filter(name='New Service').exists())

    def test_update_service(self):
        """PATCH /api/services/{id}/ — обновить сервис"""
        data = {'check_interval': 900}
        response = self.client.patch(f'/api/services/{self.service.id}/', data)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.service.refresh_from_db()
        self.assertEqual(self.service.check_interval, 900)

    def test_delete_service(self):
        """DELETE /api/services/{id}/ — удалить сервис"""
        response = self.client.delete(f'/api/services/{self.service.id}/')
        self.assertEqual(response.status_code, http_status.HTTP_204_NO_CONTENT)
        self.assertFalse(Service.objects.filter(id=self.service.id).exists())

    @patch('monitor.views.check_service.delay')
    def test_check_now_action(self, mock_delay):
        """POST /api/services/{id}/check_now/ — запустить проверку"""
        mock_delay.return_value = MagicMock(id='task-123')
        response = self.client.post(f'/api/services/{self.service.id}/check_now/')
        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)
        self.assertIn('Check triggered', response.data['message'])
        mock_delay.assert_called_once_with(self.service.id)

    def test_service_history_action(self):
        """GET /api/services/{id}/history/ — история проверок"""
        Check.objects.create(service=self.service, status='up', response_time=100)
        Check.objects.create(service=self.service, status='up', response_time=120)

        response = self.client.get(f'/api/services/{self.service.id}/history/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


@pytest.mark.django_db
class TestCheckAPI(TestCase):
    """Тесты для REST API проверок"""

    def setUp(self):
        self.client = APIClient()
        self.service = Service.objects.create(name="Test", url="https://test.com")
        self.check = Check.objects.create(
            service=self.service,
            status='up',
            response_time=100,
            status_code=200
        )

    def test_list_checks(self):
        """GET /api/checks/ — список всех проверок"""
        response = self.client.get('/api/checks/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'up')

    def test_retrieve_check(self):
        """GET /api/checks/{id}/ — детали проверки"""
        response = self.client.get(f'/api/checks/{self.check.id}/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'up')
        self.assertEqual(response.data['response_time'], 100)

@pytest.mark.django_db
class TestTelegramAlert(TestCase):
    """Тесты для Telegram алертов"""

    def setUp(self):
        self.service = Service.objects.create(
            name="Alert Test Service",
            url="https://alert-test.example.com",
            status='up'
        )

    @patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test-token', 'TELEGRAM_CHAT_ID': '123'})
    @patch('monitor.alerts.requests.post')
    def test_status_changed_alert(self, mock_post):
        """Проверка отправки алерта при изменении статуса"""
        from monitor.alerts import TelegramAlert

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        alert = TelegramAlert()
        self.service.last_status_change = timezone.now()
        result = alert.status_changed(self.service, 'up', 'down')

        self.assertTrue(result)
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn('chat_id', call_args[1]['json'])
        self.assertIn('test-token', call_args[0][0])

    @patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': '', 'TELEGRAM_CHAT_ID': ''})
    def test_alert_disabled_when_no_credentials(self):
        """Алерты отключены если нет token/chat_id"""
        from monitor.alerts import TelegramAlert

        alert = TelegramAlert()
        self.assertFalse(alert.enabled)

    @patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test-token', 'TELEGRAM_CHAT_ID': '123'})
    @patch('monitor.alerts.requests.post')
    def test_alert_handles_network_error(self, mock_post):
        """Алерт корректно обрабатывает ошибки сети"""
        from monitor.alerts import TelegramAlert

        mock_post.side_effect = Exception("Network error")

        alert = TelegramAlert()
        self.service.last_status_change = timezone.now()
        result = alert.status_changed(self.service, 'up', 'down')

        self.assertFalse(result)