from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)
from .api.views import UserViewSet

router = DefaultRouter(trailing_slash=False)
router.register('users', UserViewSet, basename='user')

urlpatterns = [
    path('auth/login', TokenObtainPairView.as_view(), name='auth-login'),
    path('auth/refresh', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/logout', TokenBlacklistView.as_view(), name='auth-logout'),
    path('', include(router.urls)),
]
