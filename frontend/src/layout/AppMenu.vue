<script setup>
import { ref, computed, watchEffect, onMounted, onBeforeUnmount, watch } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRoute } from 'vue-router';
import AppMenuItem from './AppMenuItem.vue';
import api from '@/service/api';

const authStore = useAuthStore();
const route = useRoute();
const model = ref([]);

// Contagens para badges
const unreadAnnouncementsCount = ref(0);
const newLessonPlansCount = ref(0);
let refreshInterval = null;

// Função para buscar contagem de anúncios NÃO LIDOS
const fetchUnreadAnnouncementsCount = async () => {
    if (!authStore.token || (!authStore.isAdmin && !authStore.isCoordinator && !authStore.isTeacher)) {
        unreadAnnouncementsCount.value = 0;
        return;
    }
    
    try {
        const { data } = await api.get('announcements/');
        const allMessages = data.results || data;
        
        // Conta APENAS mensagens NÃO LIDAS (onde o usuário não é o remetente)
        const unreadMessages = allMessages.filter(msg => 
            msg.sender_id !== authStore.user?.id && !msg.is_read
        );
        
        unreadAnnouncementsCount.value = unreadMessages.length;
    } catch (error) {
        console.error('Erro ao buscar contagem de anúncios:', error);
        unreadAnnouncementsCount.value = 0;
    }
};

// Função para buscar contagem de planejamentos semanais com status "ENVIADO" (SUBMITTED)
const fetchNewLessonPlansCount = async () => {
    if (!authStore.token || (!authStore.isCoordinator && !authStore.isAdmin)) {
        newLessonPlansCount.value = 0;
        return;
    }
    
    try {
        // Busca APENAS planejamentos com status SUBMITTED (Enviado)
        // O backend já filtra automaticamente para mostrar apenas os destinados a este coordenador
        const { data } = await api.get('lesson-plans/?status=SUBMITTED');
        const plans = data.results || data;
        
        // Conta apenas os planejamentos ENVIADOS (status SUBMITTED) destinados a este coordenador
        newLessonPlansCount.value = plans.length;
    } catch (error) {
        console.error('Erro ao buscar contagem de planejamentos:', error);
        newLessonPlansCount.value = 0;
    }
};

// Função para atualizar todas as contagens
const refreshCounts = async () => {
    await Promise.all([
        fetchUnreadAnnouncementsCount(),
        fetchNewLessonPlansCount()
    ]);
};

// Usamos watchEffect para reconstruir o menu se o usuário mudar (login/logout)
watchEffect(() => {
    const newMenu = [];
    if (!authStore.isGuardian) {
        // 1. DASHBOARD (Todos vêem)
        newMenu.push({
            label: 'Home',
            items: [
                { label: 'Dashboard', icon: 'pi pi-fw pi-home', to: { name: 'dashboard' } },
                { label: 'Calendário', icon: 'pi pi-fw pi-calendar', to: { name: 'calendar' } },
                ]
        });
    }
    // 2. PORTAL DA FAMÍLIA (Exclusivo para Pais)
    if (authStore.isGuardian) {
        newMenu.push({
            label: 'Portal da Família',
            items: [
                { label: 'Calendário', icon: 'pi pi-fw pi-calendar', to: { name: 'calendar' } },
                { label: 'Meus Filhos', icon: 'pi pi-fw pi-users', to: { name: 'parent-dashboard' } },
                { 
                    label: 'Meus Dados', 
                    icon: 'pi pi-fw pi-user-edit', 
                    to: { name: 'parent-dashboard', query: { action: 'profile' } } 
                }
            ]
        });
    }

    // 2. ACADÊMICO (Secretaria / Coordenação / Admin)
    if (authStore.isAdmin || authStore.isCoordinator  || authStore.isSecretary) {
        newMenu.push({
            label: 'Acadêmico',
            items: [
                { label: 'Matrículas', icon: 'pi pi-fw pi-id-card', to: { name: 'enrollments' } },
                { label: 'Alunos', icon: 'pi pi-graduation-cap', to: { name: 'students-list' } },
                { label: 'Responsáveis', icon: 'pi pi-fw pi-users', to: { name: 'guardians-list' } },
                { label: 'Turmas', icon: 'pi pi-fw pi-table', to: { name: 'classrooms' } },
                { label: 'Matérias', icon: 'pi pi-fw pi-book', to: { name: 'subjects' } },
                { label: 'Atribuições', icon: 'pi pi-fw pi-user', to: { name: 'assignments' } },
                { label: 'Contraturnos', icon: 'pi pi-fw pi-clock', to: { name: 'contraturnos-list' } },
                { label: 'Config. Checklist', icon: 'pi pi-fw pi-check-square', to: { name: 'checklist-configs' } },
                { label: 'Atividades Extras', icon: 'pi pi-fw pi-sun', to: { name: 'extra-activities' } },
                { label: 'Matrículas em Atividades', icon: 'pi pi-fw pi-user-plus', to: { name: 'extra-activity-enrollments' } }
            ]
        });
    }

    if (authStore.isAdmin || authStore.isCoordinator  || authStore.isTeacher) {
        newMenu.push({
            label: 'Comunicação',
            items: [
                { 
                    label: 'Mural de Avisos', 
                    icon: 'pi pi-megaphone', 
                    to: { name: 'communication' },
                    badge: unreadAnnouncementsCount.value
                }
            ]
        });
    }

    if (authStore.isCoordinator || authStore.isAdmin) {
        newMenu.push({
            label: 'Coordenação',
            items: [
                { 
                    label: 'Planejamentos Semanal', 
                    icon: 'pi pi-fw pi-calendar', 
                    to: { name: 'planning' },
                    badge: newLessonPlansCount.value
                },
                { label: 'Justificativas de Faltas', icon: 'pi pi-fw pi-check-circle', to: { name: 'justification-review' } },
                { label: 'Atas de Reunião', icon: 'pi pi-fw pi-file', to: { name: 'meeting-minutes' } },
                { label: 'Relatórios Semanais', icon: 'pi pi-fw pi-list', to: { name: 'weekly-reports' } },
                { label: 'Observação de Sala', icon: 'pi pi-fw pi-eye', to: { name: 'observations' } },
                { label: 'Relatórios Alunos', icon: 'pi pi-fw pi-list', to: { name: 'student-report-approval' } },
                // { label: 'Revisar Planejamentos', icon: 'pi pi-fw pi-check-square', to: { name: 'lesson-plans' } }
            ]
        });
    }

    // 3. PORTAL DO PROFESSOR (Professores / Admin)
    if (authStore.isTeacher || authStore.isAdmin) {
        newMenu.push({
            label: 'Portal do Professor',
            items: [
                { label: 'Minhas Turmas', icon: 'pi pi-fw pi-book', to: { name: 'my-classes' } },
                { label: 'Planejamento Semanal', icon: 'pi pi-fw pi-calendar-plus', to: { name: 'lesson-plans' } },
                { label: 'Relatórios Semanais', icon: 'pi pi-fw pi-list', to: { name: 'weekly-reports' } },
                { label: 'Relatórios Alunos', icon: 'pi pi-fw pi-list', to: { name: 'student-report' } },
            ]
        });
    }

    model.value = newMenu;
});

// Atualiza contagens quando o componente é montado e periodicamente
onMounted(() => {
    if (authStore.token) {
        refreshCounts();
        // Atualiza a cada 60 segundos
        refreshInterval = setInterval(refreshCounts, 60000);
    }
});

onBeforeUnmount(() => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

// Atualiza contagens quando navegar para páginas específicas
watch(
    () => route.name,
    (newRouteName) => {
        if (newRouteName === 'communication') {
            // Atualiza contagem de anúncios quando entrar na página de comunicação
            fetchUnreadAnnouncementsCount();
        } else if (newRouteName === 'planning') {
            // Atualiza contagem de planejamentos quando entrar na página de planejamentos
            fetchNewLessonPlansCount();
        }
    },
    { immediate: false }
);
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="item">
            <AppMenuItem v-if="!item.separator" :item="item" :index="i" />
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>