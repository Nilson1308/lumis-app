from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WeeklyReportViewSet, ClassObservationViewSet, MeetingMinuteViewSet

router = DefaultRouter()
router.register(r'weekly-reports', WeeklyReportViewSet)
router.register(r'class-observations', ClassObservationViewSet)
router.register(r'meeting-minutes', MeetingMinuteViewSet)

urlpatterns = [
    path('', include(router.urls)),
]