from rest_framework import serializers
from .models import Service, Check


class CheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Check
        fields = ['id', 'status', 'response_time', 'status_code', 'error_message', 'checked_at']


class ServiceSerializer(serializers.ModelSerializer):
    uptime_24h = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'url', 'check_interval', 'timeout',
            'status', 'last_checked', 'last_status_change', 'is_active',
            'uptime_24h', 'created_at', 'updated_at'
        ]
        read_only_fields = ['status', 'last_checked', 'last_status_change']

    def get_uptime_24h(self, obj):
        uptime = obj.uptime_percentage()
        return round(uptime, 2) if uptime is not None else None


class ServiceDetailSerializer(ServiceSerializer):
    """Расширенный сериализатор с последними проверками"""
    recent_checks = serializers.SerializerMethodField()

    class Meta(ServiceSerializer.Meta):
        fields = ServiceSerializer.Meta.fields + ['recent_checks']

    def get_recent_checks(self, obj):
        checks = obj.checks.all()[:10]
        return CheckSerializer(checks, many=True).data