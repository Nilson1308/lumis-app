<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useLayout } from '@/layout/composables/layout';
import { useAuthStore } from '@/stores/auth';

const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();
const authStore = useAuthStore();
const router = useRouter();

// Referência para o Popover
const op = ref(null);

// Abre/Fecha o Popover
const toggleProfile = (event) => {
    op.value.toggle(event);
};

// Ação de Logout
const onLogout = () => {
    authStore.logout();
    router.push('/login'); // Redireciona para o login (ajuste a rota se for /auth/login)
};

// Formata o nome para exibição
const userLabel = computed(() => {
    const u = authStore.user;
    if (u?.first_name && u?.last_name) return `${u.first_name} ${u.last_name}`;
    if (u?.first_name) return u.first_name;
    return u?.username || 'Usuário';
});

// Define o cargo para exibir (Estética)
const userRole = computed(() => {
    if (authStore.user?.is_superuser) return 'Administrador';
    if (authStore.isCoordinator) return 'Coordenação';
    if (authStore.isTeacher) return 'Professor';
    return 'Colaborador';
});
</script>

<template>
    <div class="layout-topbar">
        <div class="layout-topbar-logo-container">
            <button class="layout-menu-button layout-topbar-action" @click="toggleMenu">
                <i class="pi pi-bars"></i>
            </button>
            <router-link to="/" class="layout-topbar-logo">
                <img src="@/assets/lumis-icon.svg" alt="Lumis Logo" class="mx-auto" style="height: 30px;">
                <span>lumis</span>
            </router-link>
        </div>

        <div class="layout-topbar-actions">
            
            <div class="layout-config-menu">
                <button type="button" class="layout-topbar-action" @click="toggleDarkMode">
                    <i :class="['pi', { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }]"></i>
                </button>
            </div>

            <div class="layout-topbar-menu hidden lg:block">
                <div class="layout-topbar-menu-content">
                    <button type="button" class="layout-topbar-action" @click="toggleProfile">
                        <i class="pi pi-user"></i>
                        <span>Profile</span>
                    </button>
                </div>
            </div>
        </div>

        <Popover ref="op">
            <div class="flex flex-col gap-3 w-15rem">
                <div class="flex align-items-center gap-3 px-2 py-1">
                    <div class="flex items-center justify-center bg-purple-50 dark:bg-purple-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-user text-purple text-xl"></i>
                    </div>
                    <div>
                        <span class="font-bold block text-900">{{ userLabel }}</span>
                        <span class="text-sm text-600">{{ userRole }}</span>
                    </div>
                </div>        

                <Divider class="my-0" />

                <Button 
                    label="Sair do Sistema" 
                    icon="pi pi-sign-out" 
                    class="w-full justify-content-start px-2" 
                    @click="onLogout" 
                />
            </div>
        </Popover>
    </div>
</template>

<style scoped>
/* Ajuste fino para alinhar verticalmente o logo se necessário */
.layout-topbar-logo img {
    vertical-align: middle;
}
</style>