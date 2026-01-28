<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useLayout } from '@/layout/composables/layout';
import { useAuthStore } from '@/stores/auth';
import { useTenantStore } from '@/stores/tenant';


const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();
const authStore = useAuthStore();
const tenantStore = useTenantStore();
const router = useRouter();

const op = ref(null);

const toggleProfile = (event) => {
    op.value.toggle(event);
};

const onLogout = () => {
    authStore.logout();
    router.push('/login');
};

const userLabel = computed(() => {
    const u = authStore.user;
    if (u?.first_name && u?.last_name) return `${u.first_name} ${u.last_name}`;
    if (u?.first_name) return u.first_name;
    return u?.username || 'Usuário';
});

const userRole = computed(() => {
    if (authStore.user?.is_superuser) return 'Administrador';
    if (authStore.isCoordinator) return 'Coordenação';
    if (authStore.isTeacher) return 'Professor';
    if (authStore.isGuardian) return 'Responsável';
    return 'Colaborador';
});

// Lógica para o Logo Dinâmico
const logoSrc = computed(() => {
    // Se a escola tiver um logo personalizado na store, usa ele. 
    // Caso contrário, usa o ícone padrão do Lumis.
    return tenantStore.school.logo || '@/assets/lumis-icon.svg';
});

// Lógica para o Nome Dinâmico
const schoolName = computed(() => {
    return tenantStore.school.name || 'lumis';
});
</script>

<template>
    <div class="layout-topbar">
        <div class="layout-topbar-logo-container">
            <button class="layout-menu-button layout-topbar-action" @click="toggleMenu">
                <i class="pi pi-bars"></i>
            </button>
            <router-link to="/" class="layout-topbar-logo">
                <img :src="tenantStore.currentIcon" alt="logo" class="mx-auto" style="height: 30px;">
                <span class="text-primary font-bold ml-2">{{ tenantStore.currentName }}</span>
            </router-link>
        </div>

        <div class="layout-topbar-actions">
            <div class="layout-config-menu">
                <button type="button" class="layout-topbar-action" @click="toggleDarkMode">
                    <i :class="['pi', { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }]"></i>
                </button>
            </div>

            <div class="layout-topbar-menu-content">
                <button type="button" class="layout-topbar-action" @click="toggleProfile">
                    <i class="pi pi-user"></i>
                    <span>Profile</span>
                </button>
            </div>
        </div>

        <Popover ref="op">
            <div class="flex flex-col gap-3 w-15rem">
                <div class="flex align-items-center gap-3 px-2 py-1">
                    <div class="flex items-center justify-center bg-primary/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-user text-primary text-xl"></i>
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
.layout-topbar-logo img {
    vertical-align: middle;
    max-width: 150px; /* Garante que logos muito largos não quebrem o layout */
    object-fit: contain;
}
</style>