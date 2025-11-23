from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SegmentViewSet, ClassRoomViewSet, StudentViewSet, 
    EnrollmentViewSet, SubjectViewSet, TeacherAssignmentViewSet
)

router = DefaultRouter()
router.register(r'segments', SegmentViewSet)
router.register(r'classrooms', ClassRoomViewSet)
router.register(r'students', StudentViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'assignments', TeacherAssignmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]