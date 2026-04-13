from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, ServiceCategoryViewSet, ServiceViewSet

router = DefaultRouter()
router.register('departments', DepartmentViewSet, basename='department')
router.register('service-categories', ServiceCategoryViewSet, basename='servicecategory')
router.register('services', ServiceViewSet, basename='service')

urlpatterns = router.urls
