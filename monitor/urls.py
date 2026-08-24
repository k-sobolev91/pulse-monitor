from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet, CheckViewSet

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'checks', CheckViewSet, basename='check')

urlpatterns = [
    path('', include(router.urls)),
]