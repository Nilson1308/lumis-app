<script setup>
import { ref, computed, watchEffect } from 'vue';
import { useAuthStore } from '@/stores/auth';
import AppMenuItem from './AppMenuItem.vue';

const authStore = useAuthStore();
const model = ref([]);

// Usamos watchEffect para reconstruir o menu se o usuário mudar (login/logout)
watchEffect(() => {
    const newMenu = [];
    if (!authStore.isGuardian) {
        // 1. DASHBOARD (Todos vêem)
        newMenu.push({
            label: 'Home',
            items: [{ label: 'Dashboard', icon: 'pi pi-fw pi-home', to: { name: 'dashboard' } }]
        });
    }
    // 2. PORTAL DA FAMÍLIA (Exclusivo para Pais)
    if (authStore.isGuardian) {
        newMenu.push({
            label: 'Portal da Família',
            items: [
                { label: 'Meus Filhos', icon: 'pi pi-fw pi-users', to: { name: 'parent-dashboard' } }
            ]
        });
    }

    // 2. ACADÊMICO (Secretaria / Coordenação / Admin)
    if (authStore.isAdmin || authStore.isCoordinator) {
        newMenu.push({
            label: 'Acadêmico',
            items: [
                { label: 'Matrículas', icon: 'pi pi-fw pi-id-card', to: { name: 'enrollments' } },
                { label: 'Alunos', icon: 'pi pi-fw pi-user', to: { name: 'students-list' } },
                { label: 'Responsáveis', icon: 'pi pi-fw pi-users', to: { name: 'guardians-list' } }, // Novo
                { label: 'Turmas', icon: 'pi pi-fw pi-table', to: { name: 'classrooms' } },
                { label: 'Matérias', icon: 'pi pi-fw pi-book', to: { name: 'subjects' } }
            ]
        });

        newMenu.push({
            label: 'Coordenação',
            items: [
                { label: 'Atas de Reunião', icon: 'pi pi-fw pi-file', to: { name: 'meeting-minutes' } },
                { label: 'Relatórios Semanais', icon: 'pi pi-fw pi-list', to: { name: 'weekly-reports' } },
                { label: 'Observação de Sala', icon: 'pi pi-fw pi-eye', to: { name: 'observations' } },
                // O Coordenador vê os planos aqui ou via Dashboard, mas podemos por link direto
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
            ]
        });
    }

    model.value = newMenu;
});
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="item">
            <AppMenuItem v-if="!item.separator" :item="item" :index="i" />
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>