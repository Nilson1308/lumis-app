<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const reports = ref([]);
const loading = ref(true);
const reviewDialog = ref(false);
const selectedReport = ref({});
const coordinatorComment = ref('');

const loadData = async () => {
    loading.value = true;
    try {
        const res = await api.get('student-reports/');
        reports.value = res.data.results || res.data;
    } catch (e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
};

const openReview = (item) => {
    selectedReport.value = { ...item };
    coordinatorComment.value = item.coordinator_comment || '';
    reviewDialog.value = true;
};

const updateStatus = async (newStatus) => {
    try {
        await api.patch(`student-reports/${selectedReport.value.id}/`, {
            status: newStatus,
            visible_to_family: selectedReport.value.visible_to_family, // Salva o estado do checkbox
            coordinator_comment: coordinatorComment.value
        });
        toast.add({ severity: 'success', summary: 'Sucesso', detail: `Status alterado para ${newStatus}`, life: 3000 });
        reviewDialog.value = false;
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao atualizar.', life: 3000 });
    }
};

onMounted(() => {
    loadData();
});
</script>

<template>
    <div class="card">
        <Toast />
        <h5 class="mb-4">Gestão de Relatórios de Alunos</h5>

        <DataTable :value="reports" :loading="loading" :paginator="true" :rows="10">
            <Column field="date" header="Data">
                <template #body="slotProps">
                    {{ new Date(slotProps.data.date).toLocaleDateString('pt-BR') }}
                </template>
            </Column>
            <Column field="teacher_name" header="Professor"></Column>
            <Column field="student_name" header="Aluno"></Column>
            <Column field="subject" header="Assunto"></Column>
            <Column field="status" header="Status">
                <template #body="slotProps">
                    <Tag :value="slotProps.data.status" :severity="slotProps.data.status === 'APPROVED' ? 'success' : 'warning'" />
                </template>
            </Column>
            <Column field="visible_to_family" header="Visível Pais">
                <template #body="slotProps">
                    <i class="pi" :class="slotProps.data.visible_to_family ? 'pi-check-circle text-green-500' : 'pi-times-circle text-gray-400'"></i>
                </template>
            </Column>
            <Column header="Ação">
                <template #body="slotProps">
                    <Button icon="pi pi-eye" class="p-button-rounded" @click="openReview(slotProps.data)" />
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="reviewDialog" header="Análise do Relatório" :modal="true" :style="{ width: '800px' }" class="p-fluid" maximizable>
            <div class="grid grid-cols-2 gap-4 mb-3">
                <div><strong>Aluno:</strong> {{ selectedReport.student_name }}</div>
                <div><strong>Professor:</strong> {{ selectedReport.teacher_name }}</div>
            </div>
            <Divider/>
            <div class="text-xl font-bold p-4">{{ selectedReport.subject }}</div>
            <div class="surface-100 p-4 mb-4" v-html="selectedReport.content" style="max-height: 320px; overflow-wrap: break-word;"></div>
            <Divider/>
            <div class="grid grid-cols-12 gap-4">
                <div class="col-span-12 xl:col-span-6">
                    <label class="font-bold block mb-2">Visibilidade</label>
                    <div class="flex items-center">
                        <Checkbox v-model="selectedReport.visible_to_family" :binary="true" inputId="vis" />
                        <label for="vis" class="ml-2">Disponibilizar no Portal da Família se Aprovado</label>
                    </div>
                </div>
                <div class="col-span-12 xl:col-span-6">
                    <label class="font-bold block mb-2">Comentário Interno (Se rejeitar)</label>
                    <InputText v-model="coordinatorComment" placeholder="Motivo do ajuste..." fluid />
                </div>
            </div>
            
            <template #footer>
                <Button label="Solicitar Ajuste" icon="pi pi-times" class="p-button-danger p-button-text" @click="updateStatus('REJECTED')" />
                <Button label="Aprovar e Publicar" icon="pi pi-check" class="p-button-success" @click="updateStatus('APPROVED')" />
            </template>
        </Dialog>
    </div>
</template>