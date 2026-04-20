from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import HDAttachmentViewSet, HDCommentViewSet, HelpDeskViewSet, choices_view

router = DefaultRouter()
router.register('helpdesks', HelpDeskViewSet, basename='helpdesk')

urlpatterns = router.urls + [
    path('choices/', choices_view, name='choices'),
    path(
        'helpdesks/<int:helpdesk_pk>/attachments/',
        HDAttachmentViewSet.as_view({'post': 'create'}),
        name='helpdesk-attachment-list',
    ),
    path(
        'helpdesks/<int:helpdesk_pk>/attachments/<int:pk>/',
        HDAttachmentViewSet.as_view({'delete': 'destroy'}),
        name='helpdesk-attachment-detail',
    ),
    path(
        'helpdesks/<int:helpdesk_pk>/comments/',
        HDCommentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='helpdesk-comment-list',
    ),
]
