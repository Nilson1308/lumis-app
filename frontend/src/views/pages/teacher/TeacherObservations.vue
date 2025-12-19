<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/service/api';

const route = useRoute();
const router = useRouter();
const observations = ref([]);
const loading = ref(true);
const selectedObservation = ref(null);
const dialogVisible = ref(false);

// Carrega observações desta turma específica
const fetchObservations = async () => {
    loading.value = true;
    try {
        const assignmentId = route.query.assignment;
        // Filtra pelo assignmentId
        const res = await api.get(`class-observations/?assignment=${assignmentId}`);
        observations.value = res.data.results || res.data;
    } catch (e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
};

const openObservation = async (obs) => {
    selectedObservation.value = obs;
    dialogVisible.value = true;

    // Marca como lida no backend se ainda não foi
    if (!obs.is_read) {
        try {
            await api.post(`class-observations/${obs.id}/mark-read/`);
            obs.is_read = true; // Atualiza visualmente na lista
        } catch (e) {
            console.error("Erro ao marcar como lido", e);
        }
    }
};

const goBack = () => router.push({ name: 'my-classes' });

onMounted(() => {
    fetchObservations();
});
</script>

<template>
    <div class="card">
        <div class="flex items-center gap-3 mb-4">
            <Button icon="pi pi-arrow-left" class="p-button-rounded p-button-text" @click="goBack" />
            <div>
                <span class="block text-xl font-bold">Feedbacks Pedagógicos</span>
                <span class="text-gray-500 text-sm">Histórico de Observações de Sala</span>
            </div>
        </div>

        <div v-if="loading" class="text-center p-4">Carregando...</div>
        
        <div v-else-if="observations.length === 0" class="text-center p-6 border-dashed border-1 border-gray-300 border-round">
            <i class="pi pi-inbox text-4xl text-gray-400 mb-3"></i>
            <p class="m-0 text-gray-600">Nenhum feedback recebido para esta turma.</p>
        </div>

        <div v-else class="flex flex-col gap-3">
            <div 
                v-for="obs in observations" 
                :key="obs.id"
                class="p-4 border-1 border-round cursor-pointer transition-colors hover:surface-100 flex justify-between items-center"
                :class="obs.is_read ? 'surface-card border-gray-200' : 'bg-blue-50 border-blue-200'"
                @click="openObservation(obs)"
            >
                <div class="flex items-center gap-3">
                    <div class="flex flex-col items-center justify-center w-16 px-2 border-r border-gray-300">
                        <span class="text-xl font-bold text-gray-700">{{ new Date(obs.date).getDate() }}</span>
                        <span class="text-xs uppercase text-gray-500">{{ new Date(obs.date).toLocaleString('default', { month: 'short' }) }}</span>
                    </div>
                    <div>
                        <div class="font-bold text-gray-800" :class="{'text-blue-600': !obs.is_read}">
                            Observação de Sala
                            <Badge v-if="!obs.is_read" value="Novo" severity="danger" class="ml-2"></Badge>
                        </div>
                        <div class="text-sm text-gray-600 mt-1">Realizada por Coordenação</div>
                    </div>
                </div>
                <i class="pi pi-chevron-right text-gray-400"></i>
            </div>
        </div>

        <Dialog v-model:visible="dialogVisible" header="Detalhes do Feedback" :modal="true" :style="{ width: '800px' }" class="p-fluid" maximizable>
            <div v-if="selectedObservation">
                <div class="flex justify-between mb-4 pb-3 border-b border-gray-100">
                    <span class="font-bold text-gray-500">Data: {{ new Date(selectedObservation.date).toLocaleDateString('pt-BR') }}</span>
                    <Rating :modelValue="selectedObservation.student_engagement" readonly :cancel="false" />
                </div>

                <div class="mb-4 w-auto">
                    <h6 class="text-green-600 font-bold mb-2"><i class="pi pi-thumbs-up mr-2"></i>Pontos Fortes</h6>
                    <div class="surface-100 p-3 border-round" v-html="selectedObservation.strong_points" style="overflow-wrap: break-word;"></div>
                </div>

                <div class="mb-4">
                    <h6 class="text-orange-600 font-bold mb-2"><i class="pi pi-bolt mr-2"></i>Pontos a Melhorar</h6>
                    <div class="surface-100 p-3 border-round" v-html="selectedObservation.points_to_improve" style="overflow-wrap: break-word;"></div>
                </div>
            </div>
            <template #footer>
                <Button label="Fechar" icon="pi pi-check" @click="dialogVisible = false" autofocus />
            </template>
        </Dialog>
    </div>
</template>