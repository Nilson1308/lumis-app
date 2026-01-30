<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const router = useRouter();
const toast = useToast();

const notifications = ref([]);
const loading = ref(true);

const loadNotifications = async () => {
    loading.value = true;
    try {
        const { data } = await api.get('notifications/');
        notifications.value = data.results || data;
    } catch (e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
};

const markAsRead = async (notification) => {
    if (notification.read) return;
    try {
        await api.patch(`notifications/${notification.id}/mark_read/`);
        notification.read = true;
        // Não recarrega tudo para ser mais fluido
    } catch (e) {
        console.error(e);
    }
};

const markAllRead = async () => {
    try {
        await api.patch('notifications/mark_all_read/');
        notifications.value.forEach(n => n.read = true);
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Todas marcadas como lidas', life: 3000 });
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao atualizar', life: 3000 });
    }
};

const deleteNotification = async (id) => {
    try {
        await api.delete(`notifications/${id}/`);
        notifications.value = notifications.value.filter(n => n.id !== id);
        toast.add({ severity: 'success', summary: 'Removido', detail: 'Notificação excluída', life: 3000 });
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir', life: 3000 });
    }
};

const openLink = (notification) => {
    markAsRead(notification);
    if (notification.link) {
        router.push(notification.link);
    }
};

onMounted(() => {
    loadNotifications();
});
</script>

<template>
    <div class="card">
        <div class="flex justify-content-between align-items-center mb-4">
            <h4 class="m-0">Minhas Notificações</h4>
            <div class="flex gap-2">
                <Button label="Marcar todas como lidas" icon="pi pi-check-circle" class="p-button-outlined" @click="markAllRead" :disabled="notifications.length === 0" />
                <Button icon="pi pi-refresh" class="p-button-text p-button-rounded" @click="loadNotifications" />
            </div>
        </div>

        <div v-if="loading" class="text-center p-4">
            <i class="pi pi-spin pi-spinner text-3xl"></i>
        </div>

        <div v-else-if="notifications.length === 0" class="text-center p-5 surface-ground border-round">
            <i class="pi pi-bell-slash text-4xl text-gray-400 mb-3"></i>
            <p class="text-gray-600">Você não tem notificações no momento.</p>
        </div>

        <div v-else class="flex flex-column gap-3">
            <div v-for="item in notifications" :key="item.id" 
                 class="p-3 border-round border-1 surface-border flex flex-column md:flex-row align-items-start md:align-items-center gap-3 transition-colors hover:surface-50"
                 :class="{'bg-blue-50 border-blue-100': !item.read, 'surface-card': item.read}">
                
                <div class="flex align-items-center justify-content-center border-circle w-3rem h-3rem flex-shrink-0"
                     :class="item.read ? 'bg-gray-100 text-gray-500' : 'bg-blue-100 text-blue-500'">
                    <i class="pi" :class="item.read ? 'pi-envelope-open' : 'pi-envelope'"></i>
                </div>

                <div class="flex-1 cursor-pointer" @click="openLink(item)">
                    <div class="flex align-items-center gap-2 mb-1">
                        <span class="font-bold text-900">{{ item.title }}</span>
                        <span v-if="!item.read" class="bg-blue-500 text-white text-xs px-2 py-0 border-round">Nova</span>
                    </div>
                    <p class="m-0 text-700 line-height-3">{{ item.message }}</p>
                    <small class="text-gray-500 mt-2 block">
                        <i class="pi pi-clock text-xs mr-1"></i>
                        {{ new Date(item.created_at).toLocaleString('pt-BR') }}
                    </small>
                </div>

                <div class="flex gap-2 ml-auto">
                    <Button v-if="!item.read" icon="pi pi-check" class="p-button-rounded p-button-text p-button-sm" v-tooltip="'Marcar como lida'" @click="markAsRead(item)" />
                    <Button icon="pi pi-trash" class="p-button-rounded p-button-text p-button-danger p-button-sm" v-tooltip="'Excluir'" @click="deleteNotification(item.id)" />
                </div>
            </div>
        </div>
    </div>
</template>