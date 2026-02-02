<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import api from '@/service/api';

const router = useRouter();
const authStore = useAuthStore();

const notifications = ref([]);
const unreadCount = ref(0);
const op = ref(); // OverlayPanel ref

// --- LÓGICA DE DADOS ---
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
    op.value.toggle(event);
    if (unreadCount.value > 0) {
        markAllRead();
    }
};

const markAllRead = async () => {
    try {
        await api.patch('notifications/mark_all_read/');
        unreadCount.value = 0;
        notifications.value.forEach(n => n.read = true);
    } catch (e) { console.error(e); }
};

const goToLink = (link) => {
    if (link) {
        router.push(link);
        op.value.hide();
    }
};

// --- HELPERS VISUAIS ---
const getIconClass = (notif) => {
    const title = (notif.title || '').toLowerCase();
    if (title.includes('atraso') || title.includes('pendente')) return 'bg-red-100 text-red-500';
    if (title.includes('sucesso') || title.includes('aprovado')) return 'bg-green-100 text-green-500';
    return 'bg-blue-100 text-blue-500'; // Padrão
};

const getIcon = (notif) => {
    const title = (notif.title || '').toLowerCase();
    if (title.includes('atraso') || title.includes('pendente')) return 'pi-exclamation-triangle';
    if (title.includes('sucesso') || title.includes('aprovado')) return 'pi-check-circle';
    return 'pi-bell';
};

const formatDate = (dateString) => {
    const d = new Date(dateString);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);

    if (diffMins < 60) return `${diffMins} min atrás`;
    if (diffHours < 24) return `${diffHours} horas atrás`;
    return d.toLocaleDateString('pt-BR');
};

// Polling
let interval;
onMounted(() => {
    loadNotifications();
    interval = setInterval(loadNotifications, 60000);
});
onBeforeUnmount(() => clearInterval(interval));
</script>

<template>
    <div class="relative inline-block">
        <button type="button" class="layout-topbar-action relative overflow-visible mr-3" @click="toggleNotifications">
            <OverlayBadge :value="unreadCount > 0 ? unreadCount : null" severity="danger" size="small">
                <i class="pi pi-bell text-xl"></i>
            </OverlayBadge>
        </button>

        <OverlayPanel ref="op" class="w-24rem p-0 shadow-lg border-round-xl">
            <div class="flex flex-column gap-0">
                
                <div class="flex items-center justify-between p-4 border-b border-surface">
                    <span class="font-semibold text-xl">Notificações</span>
                    <span v-if="notifications.length > 0" 
                          class="text-sm text-primary font-bold cursor-pointer hover:underline" 
                          @click="markAllRead">
                        Ler todas
                    </span>
                </div>

                <div class="max-h-24rem overflow-y-auto custom-scrollbar p-0">
                    
                    <ul v-if="notifications.length > 0" class="p-0 m-0 list-none">
                        <li v-for="notif in notifications" :key="notif.id" 
                            class="flex align-items-start py-3 px-4 border-b border-surface hover:surface-100 cursor-pointer transition-colors"
                            :class="{'surface-50': !notif.read}"
                            @click="goToLink(notif.link)">
                            
                            <div class="w-3rem h-3rem flex items-center justify-center rounded-full mr-3 shrink-0"
                                 :class="getIconClass(notif)">
                                <i class="pi text-xl" :class="getIcon(notif)"></i>
                            </div>
                            
                            <div class="flex-1">
                                <span class="text-surface-900 font-medium block mb-1">
                                    {{ notif.title }}
                                </span>
                                <span class="text-surface-600 text-sm block leading-normal mb-2">
                                    {{ notif.message }}
                                </span>
                                <span class="text-xs text-gray-400 font-medium">
                                    {{ formatDate(notif.created_at) }}
                                </span>
                            </div>

                            <div v-if="!notif.read" class="w-2 h-2 bg-blue-500 border-circle mt-2 ml-2 shrink-0"></div>
                        </li>
                    </ul>

                    <div v-else class="p-5 text-center">
                        <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                            <i class="pi pi-bell-slash text-2xl text-gray-400"></i>
                        </div>
                        <span class="text-gray-500 font-medium">Nenhuma notificação nova</span>
                    </div>

                </div>

                <div class="p-3 border-t border-surface text-center">
                    <Button label="Ver Histórico Completo" link class="p-0 text-primary font-bold text-sm" @click="router.push('/notifications'); op.hide()" />
                </div>

            </div>
        </OverlayPanel>
    </div>
</template>

<style scoped>
/* Ajustes para o layout do PrimeVue/Tailwind ficarem perfeitos */
.layout-topbar-action {
    overflow: visible !important;
}

/* Scrollbar fina para o painel */
.custom-scrollbar::-webkit-scrollbar {
    width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
    background: #f1f1f1; 
}
.custom-scrollbar::-webkit-scrollbar-thumb {
    background: #ccc; 
    border-radius: 3px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #aaa; 
}

/* Classes utilitárias do exemplo adaptadas */
.rounded-full { border-radius: 9999px; }
.shrink-0 { flex-shrink: 0; }
.border-b { border-bottom-width: 1px; border-bottom-style: solid; }
.border-t { border-top-width: 1px; border-top-style: solid; }
.border-surface { border-color: var(--surface-border); }
.leading-normal { line-height: 1.5; }
</style>