from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ServiceKeywordViewSet, classify_view, feedback_view, stats_view, train_view

router = DefaultRouter()
router.register('service-keywords', ServiceKeywordViewSet, basename='service-keyword')

urlpatterns = router.urls + [
    path('classify/', classify_view, name='classify'),
    path('classify/feedback/', feedback_view, name='classify-feedback'),
    path('classify/train/', train_view, name='classify-train'),
    path('classify/stats/', stats_view, name='classify-stats'),
]
