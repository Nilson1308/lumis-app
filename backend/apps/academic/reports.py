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

from .models import Enrollment, Grade, Attendance, Subject, AcademicPeriod, TeacherAssignment
from datetime import datetime

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

    logo_path = os.path.join(settings.BASE_DIR, 'apps', 'core', 'static', 'images', 'logo_st.png')

    if os.path.exists(logo_path):
        from pathlib import Path
        logo_url = Path(logo_path).as_uri()
    else:
        logo_url = None

    context = {
        'student': student,
        'classroom': classroom,
        'report_data': report_data,
        'periods_header': all_periods,
        'is_partial': selected_period is not None,
        'generated_at': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'logo_url': request.build_absolute_uri(settings.STATIC_URL + 'images/logo_st.png')
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