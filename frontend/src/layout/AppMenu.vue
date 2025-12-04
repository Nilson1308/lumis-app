<script setup>
import { ref, computed } from 'vue'; // Importar computed
import AppMenuItem from './AppMenuItem.vue';
import { useAuthStore } from '@/stores/auth'; // Importar a Store

const authStore = useAuthStore();

// O Menu agora é uma propriedade computada (reage a mudanças)
const model = computed(() => {
    const menuItems = [
        {
            label: 'Home',
            items: [{ label: 'Dashboard', icon: 'pi pi-fw pi-home', to: { name: 'dashboard' } }]
        }
    ];

    // Se for COORDENADOR ou SUPERUSER, vê tudo
    if (authStore.isCoordinator || authStore.user?.is_superuser) {
        menuItems.push(
            {
                label: 'Acadêmico (Coordenação)',
                items: [
                    { label: 'Cadastro Alunos', icon: 'pi pi-fw pi-users', to: { name: 'students' } },
                    { label: 'Turmas', icon: 'pi pi-fw pi-th-large', to: { name: 'classrooms' } },
                    { label: 'Matérias', icon: 'pi pi-fw pi-book', to: { name: 'subjects' } },
                    { label: 'Matrículas', icon: 'pi pi-fw pi-id-card', to: { name: 'enrollments' } },
                    { label: 'Grade de Aulas', icon: 'pi pi-fw pi-briefcase', to: { name: 'assignments' } },
                ]
            },
            {
                label: 'Coordenação Pedagógica',
                items: [
                    { label: 'Observação de Sala', icon: 'pi pi-fw pi-eye', to: { name: 'observations' } },
                    { label: 'Relatórios Semanais', icon: 'pi pi-fw pi-list', to: { name: 'weekly-reports' } },
                    { label: 'Atas de Reunião', icon: 'pi pi-fw pi-file', to: { name: 'meeting-minutes' } },
                ]
            },
        );
    }

    // Se for PROFESSOR, vê menu específico
    if (authStore.isTeacher) {
        menuItems.push({
            label: 'Professor',
            items: [
                { label: 'Meus Diários', icon: 'pi pi-fw pi-calendar', to: { name: 'my-classes' } },
            ]
        });
    }

    return menuItems;
});
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="item">
            <app-menu-item v-if="!item.separator" :item="item" :index="i"></app-menu-item>
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>

<style lang="scss" scoped></style>