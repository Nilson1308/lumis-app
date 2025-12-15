<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/service/api';

const route = useRoute();
const router = useRouter();
const summary = ref([]);
const history = ref([]);
const loading = ref(true);

onMounted(async () => {
    try {
        const studentId = route.params.id;
        const response = await api.get(`students/${studentId}/attendance-report/`);
        summary.value = response.data.summary;
        history.value = response.data.history;
    } catch (e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
});

const goBack = () => router.push({ name: 'parent-dashboard' });
</script>

<template>
    <div class="grid">
        <div class="col-12">
            <div class="card">
                <div class="flex justify-content-between align-items-center mb-4">
                    <h5 class="m-0">Frequência e Faltas</h5>
                    <Button label="Voltar" icon="pi pi-arrow-left" class="p-button-text" @click="goBack" />
                </div>

                <div class="grid mt-3">
                    <div class="col-12 md:col-6 lg:col-3" v-for="item in summary" :key="item.subject">
                        <div class="surface-card shadow-2 p-3 border-round text-center">
                            <div class="text-900 font-medium mb-2">{{ item.subject }}</div>
                            <div class="text-2xl font-bold" :class="{'text-red-500': item.count > 5, 'text-green-500': item.count <= 5}">
                                {{ item.count }} Faltas
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-12">
            <div class="card">
                <h5>Histórico de Ausências</h5>
                <DataTable :value="history" :loading="loading" :paginator="true" :rows="5" responsiveLayout="scroll">
                    <Column field="date" header="Data">
                        <template #body="slotProps">
                            {{ new Date(slotProps.data.date).toLocaleDateString('pt-BR') }}
                        </template>
                    </Column>
                    <Column field="subject" header="Matéria/Aula"></Column>
                    <Column field="justified" header="Situação">
                        <template #body="slotProps">
                            <Tag :severity="slotProps.data.justified ? 'success' : 'danger'" 
                                 :value="slotProps.data.justified ? 'Justificada' : 'Não Justificada'" />
                        </template>
                    </Column>
                </DataTable>
            </div>
        </div>
    </div>
</template>