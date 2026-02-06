from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import reports
from .views import (
    SegmentViewSet, ClassRoomViewSet, StudentViewSet, 
    EnrollmentViewSet, SubjectViewSet, TeacherAssignmentViewSet,
    GradeViewSet, AttendanceViewSet, AcademicPeriodViewSet,
    DashboardDataView, GuardianViewSet, LessonPlanViewSet,
    CoordinatorViewSet, AbsenceJustificationViewSet,
    ExtraActivityViewSet, TaughtContentViewSet, SchoolEventViewSet,
    ClassScheduleViewSet
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
router.register(r'periods', AcademicPeriodViewSet)
router.register(r'guardians', GuardianViewSet)
router.register(r'lesson-plans', LessonPlanViewSet, basename='lesson-plans')
router.register(r'coordinators', CoordinatorViewSet, basename='coordinators')
router.register(r'justifications', AbsenceJustificationViewSet)
router.register(r'extra-activities', ExtraActivityViewSet)
router.register(r'taught-contents', TaughtContentViewSet)
router.register(r'calendar', SchoolEventViewSet, basename='calendar')
router.register(r'schedules', ClassScheduleViewSet)

urlpatterns = [
    path('dashboard/data/', DashboardDataView.as_view(), name='dashboard_data'),
    path('reports/student_card/<int:enrollment_id>/', reports.generate_student_report_card, name='student_report_card'),
    path('', include(router.urls)),
]