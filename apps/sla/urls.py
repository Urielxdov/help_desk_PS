from rest_framework.routers import DefaultRouter

from .views import SLAConfigViewSet, ServiceQueueViewSet, TechnicianProfileViewSet

router = DefaultRouter()
router.register('technician-profiles', TechnicianProfileViewSet)
router.register('sla-config', SLAConfigViewSet)
router.register('service-queue', ServiceQueueViewSet)

urlpatterns = router.urls
