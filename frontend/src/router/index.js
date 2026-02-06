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
                    path: '/assignments',
                    name: 'assignments',
                    component: () => import('@/views/pages/TeacherAssignmentList.vue'),
                    meta: { breadcrumb: 'Atribuição de Aulas' }
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

                // --- COORDENAÇÃO ---
                {
                    path: '/coordination/planning',
                    name: 'planning',
                    component: () => import('@/views/pages/coordination/PlanningReview.vue')
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
    if (localStorage.getItem('token') && !authStore.user) {
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
    } else {
        next();
    }
});

export default router;