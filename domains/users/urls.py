from django.urls import path
from .api.views import (
    UserListCreateView,
    UserDetailView,
    DepartmentListCreateView,
    DepartmentAgentsView,
)

urlpatterns = [
    path("users/", UserListCreateView.as_view(), name="user-list-create"),
    path("users/<str:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("departments/", DepartmentListCreateView.as_view(), name="department-list-create"),
    path("departments/<str:dept_id>/agents/", DepartmentAgentsView.as_view(), name="department-agents"),
]
