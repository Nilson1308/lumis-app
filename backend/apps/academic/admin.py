from django.contrib import admin
from .models import Segment, ClassRoom, Subject, Student, Enrollment, TeacherAssignment

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'registration_number')
    search_fields = ('name', 'registration_number')

@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'segment')
    list_filter = ('year', 'segment')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'classroom', 'active')
    list_filter = ('classroom__year', 'classroom')

# Registro simples para os outros
admin.site.register(Segment)
admin.site.register(Subject)
admin.site.register(TeacherAssignment)