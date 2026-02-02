<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { useLayout } from '@/layout/composables/layout';
import { useAuthStore } from '@/stores/auth';
import { useTenantStore } from '@/stores/tenant';
import api from '@/service/api';

import Button from 'primevue/button';
import Avatar from 'primevue/avatar';
import OverlayPanel from 'primevue/overlaypanel';
import ScrollPanel from 'primevue/scrollpanel';
import OverlayBadge from 'primevue/overlaybadge';
import Divider from 'primevue/divider';

const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();
const authStore = useAuthStore();
const tenantStore = useTenantStore();
const router = useRouter();

const op = ref(); // Perfil
const on = ref(); // Notificações

const notificacoes = ref([]);
const unreadCount = ref(0);

const toggle = (event) => {
    op.value.toggle(event);
};

const toggleNotificacoes = (event) => {
    on.value.toggle(event);
    fetchNotificacoes();
};

const userInitial = computed(() => {
    const user = authStore.user;
    if (user?.first_name) {
        return user.first_name[0].toUpperCase();
    }
    if (user?.username) {
        return user.username[0].toUpperCase();
    }
    return '?';
});

const fetchNotificacoes = async () => {
    try {
        const response = await api.get('notifications/');
        
        let data = response.data;
        if (data.results) data = data.results;

        notificacoes.value = Array.isArray(data) ? data : [];
        unreadCount.value = notificacoes.value.filter((n) => !n.read).length;

    } catch (error) {
        console.error('Erro ao buscar notificações:', error);
        notificacoes.value = [];
        unreadCount.value = 0;
    }
};

const handleNotificacaoClick = async (notificacao) => {
    try {
        if (!notificacao.read) {
            await api.patch(`notifications/${notificacao.id}/mark_read/`);
            notificacao.read = true; // Atualiza localmente
            unreadCount.value = Math.max(0, unreadCount.value - 1);
        }
        if (notificacao.link) {
            router.push(notificacao.link);
        }
        on.value.hide();
    } catch (error) {
        console.error('Erro ao marcar notificação:', error);
    }
};

const marcarTodasComoLidas = async () => {
    try {
        await api.patch('notifications/mark_all_read/');
        notificacoes.value.forEach(n => n.read = true);
        unreadCount.value = 0;
    } catch (error) {
        console.error('Erro ao marcar todas:', error);
    }
};

const getNotificacaoIcon = (titulo) => {
    // Adaptação simples baseada no título, já que não temos o campo 'tipo' na notificação genérica
    if (titulo?.includes('Planejamento')) return 'pi pi-calendar-times';
    if (titulo?.includes('Atraso')) return 'pi pi-exclamation-triangle';
    return 'pi pi-bell';
};

const getNotificacaoClass = (notificacao) => {
    if (!notificacao.read) {
        // Lógica visual baseada no título (substituto do tipo)
        if (notificacao.title?.includes('Atraso') || notificacao.title?.includes('Pendente')) {
            return 'avatar-atraso text-white';
        }
        return 'avatar-novo text-white'; // Padrão azul para novos
    }
    return 'avatar-lida text-color-secondary'; // Cinza para lidos
};

const onLogout = () => {
    authStore.logout();
    router.push('/login');
};

let interval;
onMounted(() => {
    if (authStore.token) {
        fetchNotificacoes();
        interval = setInterval(fetchNotificacoes, 60000);
    }
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

        <div class="layout-topbar-actions items-center">
            <div class="layout-config-menu">
                <button type="button" class="layout-topbar-action" @click="toggleDarkMode">
                    <i :class="['pi', { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }]"></i>
                </button>

                <button type="button" class="layout-topbar-action mr-3 relative overflow-visible" @click="toggleNotificacoes">

                    <OverlayBadge v-if="unreadCount > 0" :value="unreadCount" severity="danger">
                        <i class="pi pi-bell" />
                    </OverlayBadge>

                    <i v-else class="pi pi-bell" />
                    <span>Notificações</span>
                </button>

                <OverlayPanel ref="on" appendTo="body" :pt="{ content: { class: 'p-0' } }">
                    <div class="flex flex-col" style="width: 25rem;">
                        <div class="flex justify-between center py-3 px-4 surface-50 border-bottom-1 surface-border">
                            <span class="font-bold text-lg">Notificações</span>
                            <Button v-if="unreadCount > 0" label="Marcar todas como lidas" class="p-button-text p-button-sm text-xs" @click="marcarTodasComoLidas"></Button>
                        </div>
                        
                        <ScrollPanel style="height: 250px;" class="w-full">
                            <div class="flex flex-col gap-1 p-2">
                                <div v-for="notificacao in notificacoes" :key="notificacao.id" @click="handleNotificacaoClick(notificacao)"
                                    :class="['flex items-center gap-3 p-3 border-round-md cursor-pointer hover:surface-100 transition-colors', 
                                    { 
                                        'surface-50': !notificacao.read,  
                                        'opacity-60': notificacao.read 
                                    }]">
                                    
                                    <Avatar :class="['flex-shrink-0', getNotificacaoClass(notificacao)]"
                                        :icon="getNotificacaoIcon(notificacao.title)" 
                                        shape="circle" />
                                    
                                    <div class="flex flex-col flex-1">
                                        <span class="font-bold text-sm mb-1 text-900">{{ notificacao.title }}</span>
                                        <p :class="['m-0 text-sm line-height-3 text-700']">
                                            {{ notificacao.message }}
                                        </p>
                                        <span class="text-xs text-500 mt-1">
                                            {{ new Date(notificacao.created_at).toLocaleDateString('pt-BR') }}
                                        </span>
                                    </div>
                                </div>
                                
                                <div v-if="!notificacoes.length" class="text-center text-color-secondary p-5">
                                    <i class="pi pi-bell-slash text-2xl mb-2 block text-300"></i>
                                    Nenhuma notificação por aqui.
                                </div>
                            </div>
                        </ScrollPanel>
                        
                        <div class="px-4 py-3 border-top-1 surface-border bg-surface-50">
                            <Button label="Ver todas as notificações" icon="pi pi-arrow-right" iconPos="right" class="p-button-outlined w-full p-button-sm" @click="router.push('/notifications'); on.hide()"></Button>
                        </div>
                    </div>
                </OverlayPanel>
            </div>

            <div v-if="authStore.token" class="flex items-center">
                <Avatar 
                    :label="userInitial"
                    class="cursor-pointer font-bold" 
                    shape="circle"
                    :style="{ 'background-color': 'var(--primary-color)', 'color': '#ffffff' }"
                    @click="toggle" 
                    aria-haspopup="true" 
                    aria-controls="overlay_panel"
                />
            </div>

            <OverlayPanel ref="op" id="overlay_panel">
                <div class="flex flex-col items-center gap-4 p-4" style="min-width: 200px;">
                    <div class="text-center">
                        <Avatar :label="userInitial" size="xlarge" shape="circle" class="mb-2 font-bold bg-primary text-white" />
                        <div class="font-bold text-900">{{ authStore.user?.first_name }} {{ authStore.user?.last_name }}</div>
                        <div class="text-sm text-500">{{ authStore.user?.email || authStore.user?.username }}</div>
                    </div>

                    <div class="flex flex-col gap-2 w-full">
                        <Button 
                            label="Sair" 
                            icon="pi pi-sign-out" 
                            class="p-button-text p-button-danger w-full justify-center"
                            @click="onLogout"
                        />
                    </div>
                </div>
            </OverlayPanel>
        </div>
    </div>
</template>

<style>
/* Força o badge a aparecer */
.p-overlaybadge .p-badge {
    display: flex !important;
    align-items: center;
    justify-content: center;
    min-width: 1rem;
    height: 1rem;
    padding: 0.5rem 0.25rem;
    font-size: 0.75rem !important;
}

.layout-topbar-action {
    overflow: visible !important;
}

.avatar-atraso {
    background: var(--p-red-500) !important;
    color: white !important;
}
.avatar-novo {
    background: var(--p-blue-500) !important;
    color: white !important;
}
.avatar-nao-lida {
    background: var(--p-green-500) !important;
    color: white !important;
}
.avatar-lida {
    background: var(--p-surface-300) !important;
    color: var(--text-color-secondary) !important;
}
</style>