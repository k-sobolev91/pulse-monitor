from django.contrib import admin
from django.utils.html import format_html
from .models import Service, Check

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'status_badge', 'url', 'check_interval', 'last_checked', 'is_active']
    list_filter = ['status', 'is_active', 'created_at']
    search_fields = ['name', 'url']
    readonly_fields = ['last_checked', 'last_status_change', 'created_at', 'updated_at', 'uptime_percentage']

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'url', 'is_active')
        }),
        ('Параметры проверки', {
            'fields': ('check_interval', 'timeout')
        }),
        ('Статус', {
            'fields': ('status', 'last_checked', 'last_status_change', 'uptime_percentage'),
            'classes': ('collapse',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Цветной значок статуса"""
        colors = {
            'up': '#28a745',      # зелёный
            'down': '#dc3545',    # красный
            'unknown': '#6c757d', # серый
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'


@admin.register(Check)
class CheckAdmin(admin.ModelAdmin):
    list_display = ['service', 'status_badge', 'response_time', 'status_code', 'checked_at']
    list_filter = ['status', 'service', 'checked_at']
    search_fields = ['service__name', 'error_message']
    readonly_fields = ['checked_at']

    fieldsets = (
        ('Информация о проверке', {
            'fields': ('service', 'status', 'checked_at')
        }),
        ('Результаты', {
            'fields': ('response_time', 'status_code', 'error_message')
        }),
    )

    def status_badge(self, obj):
        """Цветной значок статуса"""
        colors = {
            'up': '#28a745',
            'down': '#dc3545',
            'timeout': '#ffc107',
            'error': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'

    def has_add_permission(self, request):
        """Проверки добавляет только система (Celery), не админ"""
        return False