from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Service, Check
from .serializers import ServiceSerializer, ServiceDetailSerializer, CheckSerializer
from .tasks import check_service


class ServiceViewSet(viewsets.ModelViewSet):
    """
    CRUD API для сервисов мониторинга.

    list: список всех сервисов
    retrieve: детали сервиса с последними проверками
    create: добавить новый сервис
    update/partial_update: изменить сервис
    destroy: удалить сервис
    """
    queryset = Service.objects.all()
    search_fields = ['name', 'url']
    ordering_fields = ['name', 'status', 'last_checked', 'created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ServiceDetailSerializer
        return ServiceSerializer

    @action(detail=True, methods=['post'])
    def check_now(self, request, pk=None):
        """Запустить проверку сервиса немедленно (POST /api/services/{id}/check_now/)"""
        service = self.get_object()
        result = check_service.delay(service.id)
        return Response(
            {'message': f'Check triggered for {service.name}', 'task_id': result.id},
            status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """История проверок сервиса (GET /api/services/{id}/history/)"""
        service = self.get_object()
        checks = service.checks.all()[:100]
        serializer = CheckSerializer(checks, many=True)
        return Response(serializer.data)


class CheckViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Только чтение: список всех результатов проверок.
    """
    queryset = Check.objects.all()
    serializer_class = CheckSerializer
    filterset_fields = ['service', 'status']