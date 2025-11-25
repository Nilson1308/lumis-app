from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SegmentViewSet, ClassRoomViewSet, StudentViewSet, 
    EnrollmentViewSet, SubjectViewSet, TeacherAssignmentViewSet,
    GradeViewSet, AttendanceViewSet
)

router = DefaultRouter()
router.register(r'segments', SegmentViewSet)
router.register(r'classrooms', ClassRoomViewSet)
router.register(r'students', StudentViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'assignments', TeacherAssignmentViewSet)
router.register(r'grades', GradeViewSet)
router.register(r'attendance', AttendanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]