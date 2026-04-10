from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api.views import HelpDeskViewSet

router = DefaultRouter(trailing_slash=False)
router.register('', HelpDeskViewSet, basename='help-desk')

urlpatterns = [
    path('', include(router.urls)),
]
