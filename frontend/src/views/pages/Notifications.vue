<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth'; // Store correta
import api from '@/service/api'; // API correta
import DataView from 'primevue/dataview';
import Button from 'primevue/button';
import Tag from 'primevue/tag';

const notificacoes = ref([]); 
const loading = ref(true);
const router = useRouter();
const authStore = useAuthStore();

const fetchNotificacoes = async () => {
    loading.value = true;
    try {
        const response = await api.get('notifications/');
        
        let data = response.data;
        // Normaliza se vier paginado ({ results: [...] }) ou lista direta
        if (data.results) data = data.results;
        
        notificacoes.value = Array.isArray(data) ? data : [];

    } catch (error) {
        console.error('Erro ao buscar notificações:', error);
        notificacoes.value = [];
    } finally {
        loading.value = false;
    }
};

const marcarTodasLidas = async () => {
    loading.value = true;
    try {
        await api.patch('notifications/mark_all_read/');
        // Atualiza localmente para evitar refetch desnecessário
        notificacoes.value.forEach(n => n.read = true);
    } catch (error) {
        console.error("Erro ao marcar todas como lidas:", error);
    } finally {
        loading.value = false;
    }
};

const onNotificationClick = async (notif) => {
    try {
        if (!notif.read) {
            await api.patch(`notifications/${notif.id}/mark_read/`);
            const index = notificacoes.value.findIndex(n => n.id === notif.id);
            if (index !== -1) {
                notificacoes.value[index].read = true;
            }
        }
        if (notif.link) {
            router.push(notif.link);
        }
    } catch (error) {
        console.error("Erro ao marcar notificação como lida:", error);
    }
};

// Helpers Visuais (Mesma lógica do Bell para consistência)
const getIconInfo = (titulo) => {
    const t = (titulo || '').toLowerCase();
    if (t.includes('atraso') || t.includes('pendente')) {
        return { icon: 'pi pi-exclamation-triangle', bgClass: 'bg-red-100 text-red-500' };
    }
    if (t.includes('sucesso') || t.includes('aprovado')) {
        return { icon: 'pi pi-check-circle', bgClass: 'bg-green-100 text-green-500' };
    }
    // Default
    return { icon: 'pi pi-bell', bgClass: 'bg-blue-100 text-blue-500' };
};

const formatarData = (dataString) => {
    if (!dataString) return '';
    return new Date(dataString).toLocaleString('pt-BR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
};

onMounted(() => {
    if (authStore.token) {
        fetchNotificacoes();
    } else {
        loading.value = false;
    }
});
</script>

<template>
    <div class="card">
        <div class="flex justify-between items-center mb-4">
            <h4 class="m-0 font-bold text-xl">Todas as Notificações</h4>
            <Button 
                label="Marcar todas como lidas" 
                icon="pi pi-check-circle" 
                class="p-button-outlined p-button-secondary p-button-sm" 
                @click="marcarTodasLidas" 
                :loading="loading"
                :disabled="notificacoes.length === 0"
            />
        </div>

        <DataView :value="notificacoes" layout="list" :loading="loading" dataKey="id">
            <template #empty>
                <div class="flex items-center justify-center bg-blue-100 dark:bg-blue-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                    <i class="pi pi-bell-slash text-4xl mb-3 text-gray-400"></i>
                    <span class="font-medium">Nenhuma notificação encontrada.</span>
                </div>
            </template>

            <template #list="slotProps">
                <div v-for="(item, index) in slotProps.items" :key="item.id" class="col-12">
                    
                    <div 
                        class="flex flex-col md:flex-row items-start p-4 gap-4 w-full cursor-pointer hover:surface-100 transition-colors border-bottom-1 surface-border"
                        :class="{ 'opacity-60': item.read, 'bg-blue-50': !item.read }"
                        @click="onNotificationClick(item)"
                    >
                        <div class="flex items-center justify-center rounded-border" 
                                :class="getIconInfo(item.title).bgClass" style="width: 2.5rem; height: 2.5rem">
                            <i class="pi text-xl" :class="getIconInfo(item.title).icon"></i>
                        </div>

                        <div class="flex flex-col gap-2 flex-grow-1">
                            <div class="flex items-center gap-2">
                                <span class="text-base font-bold text-900">{{ item.title }}</span>
                                <Tag v-if="!item.read" value="Nova" severity="info" class="text-xs px-2"></Tag>
                            </div>
                            <span class="text-700 line-height-3">{{ item.message }}</span>
                            <span class="text-sm text-500 mt-1 flex items-center gap-1">
                                <i class="pi pi-clock text-xs"></i>
                                {{ formatarData(item.created_at) }}
                            </span>
                        </div>

                        <i class="pi pi-chevron-right text-gray-400 self-center hidden md:block"></i>
                    </div>

                </div>
            </template>
        </DataView>
    </div>
</template>

<style scoped>
/* Remove padding padrão do DataView para ficar full-width */
:deep(.p-dataview-content) {
    background: transparent !important;
    border: none !important;
}
:deep(.p-dataview .p-dataview-header) {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}
</style>