import { createRouter, createWebHistory } from 'vue-router';
import AppLayout from '@/layout/AppLayout.vue';
import { useAuthStore } from '@/stores/auth';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/login',
            name: 'login',
            component: () => import('@/views/pages/auth/Login.vue')
        },
        {
            path: '/reset-password/:uid/:token',
            name: 'reset-password',
            component: () => import('@/views/pages/auth/ResetPassword.vue')
        },
        {
            path: '/',
            component: AppLayout,
            meta: { requiresAuth: true },
            children: [
                {
                    path: '/',
                    name: 'dashboard',
                    component: () => import('@/views/Dashboard.vue')
                },
                {
                    path: '/students-at-risk',
                    name: 'students-at-risk',
                    component: () => import('@/views/pages/RiskStudentsList.vue'),
                    meta: { breadcrumb: 'Alunos em Risco' }
                },
                {
                    path: '/notifications',
                    name: 'notifications',
                    component: () => import('@/views/pages/Notifications.vue')
                },
                {
                    path: '/calendar',
                    name: 'calendar',
                    component: () => import('@/views/pages/CalendarView.vue'),
                    meta: { breadcrumb: 'Calendário' }
                },

                // --- PORTAL DA FAMÍLIA ---
                {
                    path: '/portal/familia',
                    name: 'parent-dashboard',
                    component: () => import('@/views/pages/parents/ParentDashboard.vue'),
                    meta: { requiresAuth: true } // Opcional: se tiver middleware de auth
                },
                {
                    path: '/portal/calendario',
                    name: 'parent-calendar',
                    component: () => import('@/views/pages/CalendarView.vue'),
                    meta: { requiresAuth: true, breadcrumb: 'Calendário escolar' }
                },
                {
                    path: '/portal/resumo/:id',
                    name: 'parent-student-summary',
                    component: () => import('@/views/pages/parents/ParentStudentSummary.vue'),
                    meta: { requiresAuth: true }
                },
                {
                    path: '/portal/boletim/:id',
                    name: 'parent-report-card',
                    component: () => import('@/views/pages/parents/ReportCardView.vue')
                },
                {
                    path: '/portal/frequencia/:id',
                    name: 'parent-attendance',
                    component: () => import('@/views/pages/parents/AttendanceView.vue')
                },
                {
                    path: '/portal/relatorios/:id',
                    name: 'parent-reports',
                    component: () => import('@/views/pages/parents/StudentReportsView.vue')
                },
                {
                    path: '/portal/diario/:id',
                    name: 'parent-class-diary',
                    component: () => import('@/views/pages/parents/ClassDiaryView.vue')
                },
                {
                    path: '/portal/grade/:id',
                    name: 'parent-class-schedule',
                    component: () => import('@/views/pages/parents/ParentClassScheduleView.vue'),
                    meta: { requiresAuth: true, breadcrumb: 'Grade horária' }
                },

                // --- MÓDULO ACADÊMICO ---
                {
                    path: '/students',
                    name: 'students-list',
                    component: () => import('@/views/pages/StudentsList.vue')
                },
                {
                    path: '/guardians',
                    name: 'guardians-list',
                    component: () => import('@/views/pages/GuardianList.vue')
                },
                {
                    path: '/classrooms',
                    name: 'classrooms',
                    component: () => import('@/views/pages/ClassRoomsList.vue')
                },
                {
                    path: '/classrooms/:id',
                    name: 'classroom-detail',
                    component: () => import('@/views/pages/ClassroomDetail.vue'),
                    meta: { breadcrumb: 'Detalhes da Turma' }
                },
                {
                    path: '/academic/classroom-schedules',
                    name: 'classroom-schedules-manage',
                    component: () => import('@/views/pages/ClassroomSchedulesManage.vue'),
                    meta: { breadcrumb: 'Grades horárias', requiresScheduleEditor: true }
                },
                {
                    path: '/subjects',
                    name: 'subjects',
                    component: () => import('@/views/pages/SubjectsList.vue')
                },
                {
                    path: '/enrollments',
                    name: 'enrollments',
                    component: () => import('@/views/pages/EnrollmentList.vue')
                },
                {
                    path: '/assignments',
                    name: 'assignments',
                    component: () => import('@/views/pages/AssignmentList.vue')
                },
                {
                    path: '/extra-activities',
                    name: 'extra-activities',
                    component: () => import('@/views/pages/ExtraActivitiesList.vue'),
                    meta: { breadcrumb: 'Atividades Extras' }
                },
                {
                    path: '/extra-activity-enrollments',
                    name: 'extra-activity-enrollments',
                    component: () => import('@/views/pages/ExtraActivityEnrollmentsList.vue'),
                    meta: { breadcrumb: 'Matrículas em Atividades' }
                },
                {
                    path: '/contraturnos',
                    name: 'contraturnos-list',
                    component: () => import('@/views/pages/ContraturnoList.vue'),
                    meta: { breadcrumb: 'Contraturnos' }
                },
                {
                    path: '/checklist-configs',
                    name: 'checklist-configs',
                    component: () => import('@/views/pages/ChecklistConfigList.vue'),
                    meta: { breadcrumb: 'Configuração de Checklist' }
                },

                // --- PORTAL DO PROFESSOR ---
                {
                    path: '/teacher/classes',
                    name: 'my-classes',
                    component: () => import('@/views/pages/teacher/MyClasses.vue')
                },
                {
                    path: '/teacher/lesson-plans',
                    name: 'lesson-plans',
                    component: () => import('@/views/pages/teacher/LessonPlanList.vue')
                },
                {
                    path: '/teacher/classes/:id/gradebook', 
                    name: 'class-gradebook',
                    component: () => import('@/views/pages/teacher/GradeBook.vue')
                },
                {
                    path: '/teacher/classes/:id/attendance',
                    name: 'class-attendance',
                    component: () => import('@/views/pages/teacher/AttendanceClass.vue')
                },
                {
                    path: '/teacher/contraturnos/:id/attendance',
                    name: 'contraturno-attendance',
                    component: () => import('@/views/pages/teacher/ContraturnoAttendance.vue')
                },
                {
                    path: '/teacher/classes/:id/checklist',
                    name: 'student-checklist',
                    component: () => import('@/views/pages/teacher/StudentChecklist.vue')
                },
                {
                    path: '/teacher/classes/:id/diary', 
                    name: 'class-diary',
                    component: () => import('@/views/pages/teacher/ClassDiary.vue'),
                    props: true
                },
                {
                    path: '/teacher/observacoes',
                    name: 'teacher-observations',
                    component: () => import('@/views/pages/teacher/TeacherObservations.vue')
                },
                {
                    path: '/teacher/relatorios',
                    name: 'student-report',
                    component: () => import('@/views/pages/teacher/StudentReportList.vue')
                },
                {
                    path: '/relatorios',
                    name: 'reports',
                    component: () => import('@/views/pages/ReportsPage.vue'),
                    meta: { breadcrumb: 'Relatórios PDF' }
                },

                // --- COORDENAÇÃO ---
                {
                    path: '/coordination/planning',
                    name: 'planning',
                    component: () => import('@/views/pages/coordination/PlanningReview.vue')
                },
                {
                    path: '/coordination/planning-guard',
                    name: 'planning-guard-manage',
                    component: () => import('@/views/pages/coordination/PlanningSubmissionGuardManage.vue')
                },
                {
                    path: '/coordination/observations',
                    name: 'observations',
                    component: () => import('@/views/pages/coordination/ObservationList.vue')
                },
                {
                    path: '/coordination/minutes',
                    name: 'meeting-minutes',
                    component: () => import('@/views/pages/coordination/MeetingMinutes.vue')
                },
                {
                    path: '/coordination/weekly-reports',
                    name: 'weekly-reports',
                    component: () => import('@/views/pages/coordination/WeeklyReportList.vue')
                },
                {
                    path: '/coordination/justificativas',
                    name: 'justification-review',
                    component: () => import('@/views/pages/coordination/JustificationReview.vue')
                },
                {
                    path: '/coordination/relatorios',
                    name: 'student-report-approval',
                    component: () => import('@/views/pages/coordination/StudentReportApproval.vue')
                },
                {
                    path: '/coordination/auditoria',
                    name: 'coordination-audit-logs',
                    component: () => import('@/views/pages/coordination/AuditLogs.vue')
                },
                // --- COMUNICAÇÃO ---
                {
                    path: '/comunicados',
                    name: 'communication',
                    component: () => import('@/views/pages/communication/CommunicationPanel.vue'),
                    meta: {
                        breadcrumb: ['Comunicação', 'Mural de Avisos']
                    }
                },
            ]
        },
        
        // --- PÁGINAS DE ERRO ---
        {
            path: '/pages/notfound',
            name: 'notfound',
            component: () => import('@/views/pages/NotFound.vue')
        },
        {
            path: '/auth/access',
            name: 'accessDenied',
            component: () => import('@/views/pages/auth/Access.vue')
        },
        {
            path: '/auth/error',
            name: 'error',
            component: () => import('@/views/pages/auth/Error.vue')
        },
        // Captura qualquer rota desconhecida e manda para 404
        {
            path: '/:pathMatch(.*)*',
            redirect: '/pages/notfound'
        }
    ]
});

// --- GUARDA DE ROTAS (PROTEÇÃO) ---
router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore();
    const requiresAuth = to.matched.some(record => record.meta.requiresAuth);

    // 1. Tenta restaurar a sessão se tiver token (F5 na página)
    // CORREÇÃO: Usamos a chave 'token', não 'access_token'
    const storedToken = localStorage.getItem('token') || sessionStorage.getItem('token');
    if (storedToken && !authStore.user) {
        try {
            await authStore.fetchUser();
        } catch (e) {
            authStore.logout(); // Token inválido
        }
    }

    // 2. Verifica permissão
    if (requiresAuth && !authStore.isAuthenticated) {
        next({ name: 'login' });
    } else if (to.name === 'login' && authStore.isAuthenticated) {
        next({ name: 'dashboard' });
    } else if (to.matched.some((r) => r.meta.requiresScheduleEditor) && !authStore.canEditClassSchedule) {
        next({ name: 'accessDenied' });
    } else {
        next();
    }
});

export default router;