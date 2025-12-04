<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();

// --- ESTADOS ---
const reports = ref([]);
const report = ref({});
const loading = ref(true);
const reportDialog = ref(false);
const deleteDialog = ref(false);
const submitted = ref(false);

// --- CARREGAR DADOS ---
const fetchReports = async () => {
    loading.value = true;
    try {
        const response = await api.get('weekly-reports/');
        reports.value = response.data.results;
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar relatórios', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES ---
const openNew = () => {
    // Sugere data de hoje e data de 5 dias atrás
    const today = new Date();
    const lastMonday = new Date();
    lastMonday.setDate(today.getDate() - 4);

    report.value = {
        start_date: lastMonday,
        end_date: today
    };
    submitted.value = false;
    reportDialog.value = true;
};

const editReport = (item) => {
    report.value = { ...item };
    // Converte strings para Date
    if (report.value.start_date) report.value.start_date = new Date(report.value.start_date);
    if (report.value.end_date) report.value.end_date = new Date(report.value.end_date);
    reportDialog.value = true;
};

const confirmDelete = (item) => {
    report.value = item;
    deleteDialog.value = true;
};

// --- AUXILIAR DATA ---
const formatDateAPI = (dateObj) => {
    if (!dateObj) return null;
    const offset = dateObj.getTimezoneOffset();
    return new Date(dateObj.getTime() - (offset*60*1000)).toISOString().split('T')[0];
}

// --- SALVAR ---
const saveReport = async () => {
    submitted.value = true;

    if (report.value.start_date && report.value.end_date && report.value.description) {
        const payload = { ...report.value };
        // Formata datas
        if (payload.start_date instanceof Date) payload.start_date = formatDateAPI(payload.start_date);
        if (payload.end_date instanceof Date) payload.end_date = formatDateAPI(payload.end_date);

        try {
            if (report.value.id) {
                await api.put(`weekly-reports/${report.value.id}/`, payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Relatório atualizado', life: 3000 });
            } else {
                await api.post('weekly-reports/', payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Relatório enviado', life: 3000 });
            }
            reportDialog.value = false;
            fetchReports();
        } catch (error) {
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar.', life: 3000 });
        }
    }
};

const deleteReport = async () => {
    try {
        await api.delete(`weekly-reports/${report.value.id}/`);
        deleteDialog.value = false;
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Relatório removido', life: 3000 });
        fetchReports();
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao remover', life: 3000 });
    }
};

onMounted(() => {
    fetchReports();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            <Toolbar class="mb-4">
                <template v-slot:start>
                    <div class="my-2">
                        <Button label="Novo Relatório Semanal" icon="pi pi-plus" class="mr-2" @click="openNew" />
                    </div>
                </template>
            </Toolbar>

            <DataTable :value="reports" :loading="loading" responsiveLayout="scroll" :paginator="true" :rows="10">
                <template #header>Relatórios Semanais</template>
                <template #empty>Nenhum relatório encontrado.</template>

                <Column header="Período" sortable style="width: 25%">
                    <template #body="slotProps">
                        {{ new Date(slotProps.data.start_date).toLocaleDateString('pt-BR') }} a 
                        {{ new Date(slotProps.data.end_date).toLocaleDateString('pt-BR') }}
                    </template>
                </Column>
                <Column field="author_name" header="Coordenadora" sortable style="width: 25%"></Column>
                <Column field="description" header="Resumo" style="width: 35%">
                    <template #body="slotProps">
                        <span class="text-overflow-ellipsis">{{ slotProps.data.description.substring(0, 60) }}...</span>
                    </template>
                </Column>
                
                <Column header="Ações" style="width: 15%">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editReport(slotProps.data)" v-tooltip.top="'Ver/Editar'" />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDelete(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="reportDialog" :style="{ width: '700px' }" header="Relatório Semanal" :modal="true" class="p-fluid">
                
                <div class="grid grid grid-cols-12 gap-4 mb-2">
                    <div class="col-span-12 xl:col-span-6">
                        <label class="mb-2 block font-bold">Data Início</label>
                        <Calendar v-model="report.start_date" dateFormat="dd/mm/yy" showIcon fluid />
                    </div>
                    <div class="col-span-12 xl:col-span-6">
                        <label class="mb-2 block font-bold">Data Fim</label>
                        <Calendar v-model="report.end_date" dateFormat="dd/mm/yy" showIcon fluid />
                    </div>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold">Resumo das Atividades</label>
                    <Textarea v-model="report.description" rows="8" autoResize placeholder="O que foi realizado nesta semana?" :class="{ 'p-invalid': submitted && !report.description }" fluid />
                    <small class="p-error" v-if="submitted && !report.description">Obrigatório.</small>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold text-red-500">Pendências / Pontos de Atenção</label>
                    <Textarea v-model="report.pending_issues" rows="4" autoResize placeholder="Algum problema não resolvido? Aluno crítico?" fluid />
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="reportDialog = false" />
                    <Button label="Enviar Relatório" icon="pi pi-send" @click="saveReport" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-center justify-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span>Excluir este relatório?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteReport" />
                </template>
            </Dialog>
        </div>
    </div>
</template>