import os
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
# Bloco de segurança do WeasyPrint
try:
    from weasyprint import HTML, CSS
except OSError:
    HTML = None
    CSS = None

from .models import Enrollment, Grade, Attendance, Subject, AcademicPeriod, TeacherAssignment, TaughtContent, ClassRoom
from datetime import datetime


def _get_report_branding(request):
    """
    Logo e nome da escola para relatórios PDF.
    Regra: logo da conta (SchoolAccount); se não houver, logo Lumis.
    """
    try:
        from apps.core.models import SchoolAccount
        school = SchoolAccount.objects.first()
        if school and school.logo:
            logo_url = request.build_absolute_uri(school.logo.url)
            school_name = school.name
            return logo_url, school_name
    except Exception:
        pass

    # Fallback: logo Lumis (static)
    logo_path = os.path.join(settings.BASE_DIR, 'apps', 'core', 'static', 'images', 'logo_st.png')
    if os.path.exists(logo_path):
        logo_url = request.build_absolute_uri(settings.STATIC_URL + 'images/logo_st.png')
    else:
        logo_url = None
    return logo_url, 'Lumis Educacional'

def generate_student_report_card(request, enrollment_id):
    try:
        enrollment = Enrollment.objects.get(id=enrollment_id)
    except Enrollment.DoesNotExist:
        return HttpResponse("Matrícula não encontrada", status=404)

    # Verifica se foi solicitado um período específico
    period_id = request.GET.get('period')
    selected_period = None
    
    if period_id and period_id != 'null': # O Frontend pode mandar string 'null'
        try:
            selected_period = AcademicPeriod.objects.get(id=period_id)
        except AcademicPeriod.DoesNotExist:
            pass

    student = enrollment.student
    classroom = enrollment.classroom
    # Apenas matérias do corpo docente da turma (TeacherAssignment)
    subjects = Subject.objects.filter(
        teacherassignment__classroom=classroom
    ).distinct().order_by('name')
    
    # --- CORREÇÃO AQUI ---
    if selected_period:
        all_periods = [selected_period]
    else:
        # Pega todos (1º, 2º, 3º, 4º) independente de estarem ativos ou não
        all_periods = AcademicPeriod.objects.all().order_by('start_date')
    # ---------------------

    report_data = []

    for subject in subjects:
        row = {
            'subject': subject.name,
            'period_grades': [], 
            'final_average': '-',
            'total_absences': 0,
            'status': '-'
        }

        sum_of_averages = 0
        count_of_periods_with_grades = 0
        
        for period in all_periods:
            grades = Grade.objects.filter(enrollment=enrollment, subject=subject, period=period)
            
            # Média do Período (Ponderada)
            p_weighted = 0
            p_weight = 0
            for g in grades:
                p_weighted += (g.value * g.weight)
                p_weight += g.weight
            
            if p_weight > 0:
                period_avg = p_weighted / p_weight
                row['period_grades'].append(f"{period_avg:.1f}")
                
                # Acumula para a Média Final
                sum_of_averages += period_avg
                count_of_periods_with_grades += 1
            else:
                row['period_grades'].append("-")

            # Somar Faltas
            absences = Attendance.objects.filter(enrollment=enrollment, subject=subject, period=period, present=False).count()
            row['total_absences'] += absences

        # Cálculo da Média Final (Média Aritmética dos Bimestres)
        if count_of_periods_with_grades > 0:
            # Ex: (Nota 1º Bim + Nota 2º Bim) / 2
            final_avg = sum_of_averages / count_of_periods_with_grades
            row['final_average'] = f"{final_avg:.1f}"
            
            # Regra simples de aprovação (Média 6)
            row['status'] = 'Aprovado' if final_avg >= 6 else 'Recuperação'
        
        report_data.append(row)

    logo_url, school_name = _get_report_branding(request)

    context = {
        'student': student,
        'classroom': classroom,
        'report_data': report_data,
        'periods_header': all_periods,
        'is_partial': selected_period is not None,
        'generated_at': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'logo_url': logo_url,
        'school_name': school_name
    }

    if HTML is None:
        return HttpResponse("Erro: Biblioteca PDF não instalada.", status=500)

    html_string = render_to_string('reports/report_card.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Boletim_{student.name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def _can_access_classroom(user, classroom_id):
    """Professor: apenas suas turmas. Coordenador/Admin: qualquer turma."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if user.is_superuser or user.groups.filter(name='Coordenacao').exists():
        return True
    return ClassRoom.objects.filter(
        pk=classroom_id,
        teacherassignment__teacher=user
    ).exists()


def generate_diary_report(request):
    """
    Diário de classe em PDF.
    GET: classroom, period. Professor: só suas turmas. Coordenador: escolhe turma.
    """
    from rest_framework.permissions import IsAuthenticated
    if not request.user.is_authenticated:
        return HttpResponse("Acesso negado.", status=403)

    classroom_id = request.GET.get('classroom')
    period_id = request.GET.get('period')
    if not classroom_id or not period_id:
        return HttpResponse("Parâmetros classroom e period são obrigatórios.", status=400)

    try:
        classroom = ClassRoom.objects.get(pk=classroom_id)
        period = AcademicPeriod.objects.get(pk=period_id)
    except (ClassRoom.DoesNotExist, AcademicPeriod.DoesNotExist):
        return HttpResponse("Turma ou período não encontrado.", status=404)

    if not _can_access_classroom(request.user, classroom_id):
        return HttpResponse("Sem permissão para acessar esta turma.", status=403)

    # TaughtContent: atribuições desta turma, datas no período
    contents = TaughtContent.objects.filter(
        assignment__classroom=classroom,
        date__gte=period.start_date,
        date__lte=period.end_date
    ).select_related('assignment', 'assignment__subject', 'assignment__teacher').order_by('date', 'assignment__subject__name')

    rows = []
    for tc in contents:
        rows.append({
            'date': tc.date.strftime('%d/%m/%Y'),
            'subject': tc.assignment.subject.name,
            'teacher': tc.assignment.teacher.get_full_name() or tc.assignment.teacher.username,
            'content': tc.content,
            'homework': tc.homework or '-'
        })

    logo_url, school_name = _get_report_branding(request)
    context = {
        'classroom': classroom,
        'period': period,
        'rows': rows,
        'generated_at': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'logo_url': logo_url,
        'school_name': school_name,
        'report_title': 'Diário de Classe'
    }

    if HTML is None:
        return HttpResponse("Erro: Biblioteca PDF não instalada.", status=500)

    html_string = render_to_string('reports/diary_report.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Diario_Classe_{classroom.name}_{period.name.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def generate_attendance_report(request):
    """
    Relatório de Frequências em PDF.
    GET: classroom, period. Professor: só suas turmas. Coordenador: escolhe turma.
    """
    if not request.user.is_authenticated:
        return HttpResponse("Acesso negado.", status=403)

    classroom_id = request.GET.get('classroom')
    period_id = request.GET.get('period')
    if not classroom_id or not period_id:
        return HttpResponse("Parâmetros classroom e period são obrigatórios.", status=400)

    try:
        classroom = ClassRoom.objects.get(pk=classroom_id)
        period = AcademicPeriod.objects.get(pk=period_id)
    except (ClassRoom.DoesNotExist, AcademicPeriod.DoesNotExist):
        return HttpResponse("Turma ou período não encontrado.", status=404)

    if not _can_access_classroom(request.user, classroom_id):
        return HttpResponse("Sem permissão para acessar esta turma.", status=403)

    # Enrollments ativos da turma
    enrollments = Enrollment.objects.filter(
        classroom=classroom, active=True
    ).select_related('student').order_by('student__name')

    # Matérias da turma (para colunas)
    subjects = Subject.objects.filter(
        teacherassignment__classroom=classroom
    ).distinct().order_by('name')

    rows = []
    for enroll in enrollments:
        row = {'student_name': enroll.student.name, 'registration': enroll.student.registration_number, 'subjects': []}
        for subj in subjects:
            presences = Attendance.objects.filter(
                enrollment=enroll, subject=subj, period=period, present=True
            ).count()
            absences = Attendance.objects.filter(
                enrollment=enroll, subject=subj, period=period, present=False
            ).count()
            row['subjects'].append({
                'subject': subj.name,
                'presences': presences,
                'absences': absences
            })
        rows.append(row)

    logo_url, school_name = _get_report_branding(request)
    context = {
        'classroom': classroom,
        'period': period,
        'rows': rows,
        'subjects': subjects,
        'generated_at': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'logo_url': logo_url,
        'school_name': school_name,
        'report_title': 'Frequências'
    }

    if HTML is None:
        return HttpResponse("Erro: Biblioteca PDF não instalada.", status=500)

    html_string = render_to_string('reports/attendance_report.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Frequencias_{classroom.name}_{period.name.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response