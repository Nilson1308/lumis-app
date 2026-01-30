<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { useLayout } from '@/layout/composables/layout';
import { useAuthStore } from '@/stores/auth';
import { useTenantStore } from '@/stores/tenant';
import api from '@/service/api';

const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();
const authStore = useAuthStore();
const tenantStore = useTenantStore();
const router = useRouter();

// --- PERFIL ---
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

// --- NOTIFICAÇÕES ---
const notifications = ref([]);
const unreadCount = ref(0);
const opNotifications = ref(); 

const loadNotifications = async () => {
    if (!authStore.token) return;
    try {
        const { data } = await api.get('notifications/');
        notifications.value = data.results || data;
        unreadCount.value = notifications.value.filter(n => !n.read).length;
    } catch (e) {
        // Silently fail
    }
};

const toggleNotifications = (event) => {
    opNotifications.value.toggle(event);
    if (unreadCount.value > 0) {
        markAllRead(); 
    }
};

const markAllRead = async () => {
    try {
        await api.patch('notifications/mark_all_read/');
        unreadCount.value = 0;
        notifications.value.forEach(n => n.read = true);
    } catch (e) {
        console.error(e);
    }
};

const goToLink = (link) => {
    if (link) {
        router.push(link);
        opNotifications.value.hide();
    }
};

const viewAllNotifications = () => {
    router.push({ name: 'notifications' }); // Certifique-se que a rota 'notifications' existe
    opNotifications.value.hide();
};

let interval;
onMounted(() => {
    loadNotifications();
    interval = setInterval(loadNotifications, 60000);
});
onBeforeUnmount(() => clearInterval(interval));

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

            <button class="layout-topbar-action relative mr-3" @click="toggleNotifications">
                <OverlayBadge :value="unreadCount > 0 ? unreadCount : null" severity="danger" size="small">
                    <i class="pi pi-bell text-xl" />
                </OverlayBadge>
            </button>

            <OverlayPanel ref="opNotifications" class="w-24rem p-0">
                <div class="flex flex-column gap-0">
                    <div class="flex align-items-center justify-content-between p-3 border-bottom-1 surface-border bg-surface-50">
                        <span class="font-bold text-lg">Notificações</span>
                        <span v-if="notifications.length > 0" class="text-xs text-primary cursor-pointer hover:underline" @click="markAllRead">
                            Ler todas
                        </span>
                    </div>
                    
                    <div v-if="notifications.length === 0" class="p-5 text-center text-gray-500">
                        <i class="pi pi-bell-slash text-3xl mb-3 block text-gray-300"></i>
                        <span class="text-sm">Tudo limpo por aqui!</span>
                    </div>

                    <div class="max-h-20rem overflow-y-auto">
                        <div v-for="notif in notifications.slice(0, 5)" :key="notif.id" 
                             class="p-3 border-bottom-1 surface-border cursor-pointer hover:surface-100 transition-colors"
                             :class="{'bg-blue-50': !notif.read}"
                             @click="goToLink(notif.link)">
                            <div class="flex align-items-start gap-3">
                                <div class="mt-1">
                                    <i class="pi pi-circle-fill text-xs" :class="notif.read ? 'text-gray-300' : 'text-blue-500'"></i>
                                </div>
                                <div class="flex-1">
                                    <div class="font-semibold text-sm mb-1 text-900">{{ notif.title }}</div>
                                    <div class="text-sm text-700 line-height-3 mb-2" style="word-break: break-word;">{{ notif.message }}</div>
                                    <div class="text-xs text-gray-500 flex align-items-center gap-1">
                                        <i class="pi pi-clock text-xs"></i>
                                        {{ new Date(notif.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute:'2-digit' }) }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div v-if="notifications.length > 0" class="p-2 text-center border-top-1 surface-border bg-surface-50 hover:surface-100 cursor-pointer transition-colors" @click="viewAllNotifications">
                        <span class="text-primary font-bold text-sm">Ver todas as notificações</span>
                    </div>
                </div>
            </OverlayPanel>

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
                    class="w-full justify-content-start px-2 p-button-text p-button-danger" 
                    @click="onLogout" 
                />
            </div>
        </Popover>
    </div>
</template>

<style scoped>
.layout-topbar-logo img {
    vertical-align: middle;
    max-width: 150px; 
    object-fit: contain;
}
/* Importante para o botão não cortar o badge */
.layout-topbar-action {
    overflow: visible !important; 
}
</style>