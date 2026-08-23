from django.db import models
from django.utils import timezone


class Service(models.Model):
    """Сервис для мониторинга"""

    STATUS_CHOICES = [
        ('up', 'UP'),
        ('down', 'DOWN'),
        ('unknown', 'UNKNOWN'),
    ]

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    url = models.URLField()  # HTTP endpoint или хост
    check_interval = models.IntegerField(default=300)  # секунды, 5 минут по умолчанию
    timeout = models.IntegerField(default=10)  # таймаут в секундах

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    last_checked = models.DateTimeField(null=True, blank=True)
    last_status_change = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.status})"

    def uptime_percentage(self):
        """Процент uptime за последние 24 часа"""
        from datetime import timedelta

        last_24h = timezone.now() - timedelta(hours=24)
        checks = self.checks.filter(checked_at__gte=last_24h)

        if not checks.exists():
            return None

        successful = checks.filter(status='up').count()
        return (successful / checks.count()) * 100


class Check(models.Model):
    """Результат одной проверки сервиса"""

    STATUS_CHOICES = [
        ('up', 'UP'),
        ('down', 'DOWN'),
        ('timeout', 'TIMEOUT'),
        ('error', 'ERROR'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='checks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    response_time = models.FloatField(null=True, blank=True)  # миллисекунды
    status_code = models.IntegerField(null=True, blank=True)  # HTTP status code
    error_message = models.TextField(blank=True, null=True)

    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['service', '-checked_at']),
        ]

    def __str__(self):
        return f"{self.service.name} — {self.status} at {self.checked_at}"