from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet, CheckViewSet, DashboardView

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'checks', CheckViewSet, basename='check')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', DashboardView.as_view(), name='dashboard'),
]
