from django.contrib import admin
from .models import (
    Segment, ClassRoom, Subject, Enrollment, 
    TeacherAssignment, Student, Guardian, 
    Grade, Attendance, AcademicPeriod, LessonPlan,
    ExtraActivity, TaughtContent, SchoolEvent
)

# --- CONFIGURAÇÕES AUXILIARES ---

@admin.register(ExtraActivity)
class ExtraActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)

@admin.register(AcademicPeriod)
class AcademicPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)

@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'segment', 'year') # Removido 'shift'
    list_filter = ('segment', 'year') # Removido 'shift'
    search_fields = ('name',) # OBRIGATÓRIO para o autocomplete do Enrollment funcionar

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'classroom')
    list_filter = ('classroom', 'subject')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'subject__name')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'classroom', 'date_enrolled') # Removido 'is_active'
    list_filter = ('classroom',) # Removido 'is_active'
    search_fields = ('student__name', 'student__registration_number')
    autocomplete_fields = ['student', 'classroom']

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'subject', 'period', 'name', 'value', 'weight')
    list_filter = ('subject', 'period', 'enrollment__classroom')
    search_fields = ('enrollment__student__name',)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'subject', 'date', 'present', 'period')
    list_filter = ('date', 'subject', 'present', 'period')

# --- FASE 1: DADOS MESTRES (ALUNOS E PAIS) ---

@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ('name', 'cpf', 'phone', 'secondary_phone', 'email')
    search_fields = ('name', 'cpf', 'email')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'name', 'birth_date', 'city', 'created_at')
    search_fields = ('name', 'registration_number', 'cpf')
    list_filter = ('gender', 'state', 'nationality')
    
    # Interface melhorada para selecionar Muitos Responsáveis
    filter_horizontal = ('guardians',) 
    
    fieldsets = (
        ('Identificação', {
            'fields': ('name', 'registration_number', 'photo')
        }),
        ('Documentação Civil', {
            'fields': ('birth_date', 'gender', 'cpf', 'rg', 'nationality')
        }),
        ('Vida Escolar & Rotina', {
            'fields': ('period', 'is_full_time', 'meals', 'extra_activities')
        }),
        ('Endereço', {
            'fields': ('zip_code', 'street', 'number', 'complement', 'neighborhood', 'city', 'state')
        }),
        ('Saúde & Emergência', {
            'fields': ('allergies', 'medications', 'emergency_contact')
        }),
        ('Vínculos Familiares', {
            'fields': ('guardians',)
        }),
    )

# --- FASE 2: PLANEJAMENTO DO PROFESSOR ---

@admin.register(LessonPlan)
class LessonPlanAdmin(admin.ModelAdmin):
    list_display = ('get_teacher', 'get_subject', 'start_date', 'status')
    list_filter = ('status', 'start_date', 'assignment__classroom')
    search_fields = ('topic', 'assignment__teacher__first_name', 'assignment__teacher__last_name')
    
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Professor')
    def get_teacher(self, obj):
        return obj.assignment.teacher.get_full_name()

    @admin.display(description='Matéria')
    def get_subject(self, obj):
        return f"{obj.assignment.subject.name} ({obj.assignment.classroom.name})"

@admin.register(TaughtContent)
class TaughtContentAdmin(admin.ModelAdmin):
    list_display = ('date', 'get_classroom', 'get_subject', 'get_teacher', 'content_preview')
    list_filter = ('date', 'assignment__classroom', 'assignment__subject', 'assignment__teacher')
    search_fields = ('content', 'assignment__classroom__name', 'assignment__teacher__username', 'assignment__teacher__first_name')
    date_hierarchy = 'date'
    ordering = ('-date',)

    def get_classroom(self, obj):
        return obj.assignment.classroom.name
    get_classroom.short_description = "Turma"

    def get_subject(self, obj):
        return obj.assignment.subject.name
    get_subject.short_description = "Matéria"
    
    def get_teacher(self, obj):
        # Tenta pegar o nome completo, senão usa o login
        return obj.assignment.teacher.get_full_name() or obj.assignment.teacher.username
    get_teacher.short_description = "Professor"

    def content_preview(self, obj):
        # Mostra só os primeiros 50 caracteres para não poluir a tabela
        clean_content = obj.content or ""
        return (clean_content[:75] + '...') if len(clean_content) > 75 else clean_content
    content_preview.short_description = "Conteúdo Ministrado"

@admin.register(SchoolEvent)
class SchoolEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'event_type', 'target_audience')
    list_filter = ('event_type', 'target_audience')