<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const FilterMatchMode = {
    CONTAINS: 'contains'
};

const toast = useToast();
const requests = ref([]);
const loading = ref(true);

// Controle de Filtro (Abas)
const activeStatus = ref('PENDING'); // 'PENDING' ou 'ALL'

// Controle de Rejeição
const rejectDialog = ref(false);
const selectedRequest = ref(null);
const rejectionReason = ref('');

const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
});

const fetchRequests = async () => {
    loading.value = true;
    try {
        const res = await api.get('justifications/');
        requests.value = res.data.results || res.data;
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar solicitações.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES ---

const approveRequest = async (item) => {
    try {
        await api.patch(`justifications/${item.id}/`, { status: 'APPROVED' });
        toast.add({ severity: 'success', summary: 'Aprovado', detail: 'Falta justificada com sucesso.', life: 3000 });
        fetchRequests();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao aprovar.' });
    }
};

const openRejectDialog = (item) => {
    selectedRequest.value = item;
    rejectionReason.value = '';
    rejectDialog.value = true;
};

const confirmReject = async () => {
    if (!rejectionReason.value) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Informe o motivo da recusa.', life: 3000 });
        return;
    }
    try {
        await api.patch(`justifications/${selectedRequest.value.id}/`, { 
            status: 'REJECTED',
            rejection_reason: rejectionReason.value
        });
        toast.add({ severity: 'info', summary: 'Rejeitado', detail: 'Justificativa recusada.', life: 3000 });
        rejectDialog.value = false;
        fetchRequests();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao rejeitar.' });
    }
};

const openFile = (fileUrl) => {
    if (fileUrl) window.open(fileUrl, '_blank');
};

const getStatusLabel = (status) => {
    switch(status) {
        case 'PENDING': return 'Pendente';
        case 'APPROVED': return 'Aprovado';
        case 'REJECTED': return 'Recusado';
        default: return status;
    }
};

const getStatusSeverity = (status) => {
    switch(status) {
        case 'PENDING': return 'warning';
        case 'APPROVED': return 'success';
        case 'REJECTED': return 'danger';
        default: return 'info';
    }
};

onMounted(() => {
    fetchRequests();
});
</script>

<template>
    <div class="card">
        <Toast />
        <DataTable :value="requests" :filters="filters" :loading="loading" responsiveLayout="scroll" :paginator="true" :rows="10">

            <template #header>
                <div class="flex flex-wrap gap-2 items-center justify-between">
                    <h4 class="m-0">Análise de Justificativas</h4>
                    <IconField>
                        <InputIcon>
                            <i class="pi pi-search" />
                        </InputIcon>
                        <InputText v-model="filters['global'].value" placeholder="Buscar..." />
                    </IconField>
                </div>
            </template>

            <template #empty>Nenhuma solicitação encontrada.</template>

            <Column field="absence_date" header="Data da Falta" sortable>
                <template #body="slotProps">
                    {{ new Date(slotProps.data.absence_date).toLocaleDateString('pt-BR') }}
                </template>
            </Column>
            
            <Column field="student_name" header="Aluno" sortable>
                <template #body="slotProps">
                    <span class="font-bold">{{ slotProps.data.student_name }}</span>
                    <div class="text-sm text-gray-500">{{ slotProps.data.classroom_name }}</div>
                </template>
            </Column>

            <Column field="reason" header="Motivo / Documento">
                <template #body="slotProps">
                    <div>{{ slotProps.data.reason }}</div>
                    <div v-if="slotProps.data.file" class="mt-2">
                        <Button 
                            label="Ver Anexo" 
                            icon="pi pi-paperclip" 
                            class="p-button-outlined p-button-sm p-button-secondary" 
                            @click="openFile(slotProps.data.file)"
                        />
                    </div>
                    <div v-else class="text-sm text-gray-400 mt-1 italic">Sem anexo</div>
                </template>
            </Column>

            <Column field="status" header="Status" sortable>
                <template #body="slotProps">
                    <Tag :value="getStatusLabel(slotProps.data.status)" :severity="getStatusSeverity(slotProps.data.status)" />
                    <div v-if="slotProps.data.status === 'REJECTED'" class="text-xs text-red-500 mt-1">
                        Motivo: {{ slotProps.data.rejection_reason }}
                    </div>
                </template>
            </Column>

            <Column header="Ações" style="min-width: 150px">
                <template #body="slotProps">
                    <div v-if="slotProps.data.status === 'PENDING'" class="flex gap-2">
                        <Button icon="pi pi-check" class="p-button-rounded mr-2" @click="approveRequest(slotProps.data)" v-tooltip="'Aprovar'" />
                        <Button icon="pi pi-times" class="p-button-rounded" @click="openRejectDialog(slotProps.data)" v-tooltip="'Recusar'" />
                    </div>
                    <span v-else class="text-gray-400 text-sm">Concluído</span>
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="rejectDialog" header="Recusar Justificativa" :modal="true" :style="{ width: '400px' }">
            <div class="field">
                <label class="font-bold mb-2 block">Motivo da Recusa</label>
                <Textarea v-model="rejectionReason" rows="3" class="w-full" placeholder="Ex: Atestado ilegível, data incorreta..." autofocus />
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="rejectDialog = false" />
                <Button label="Confirmar Recusa" icon="pi pi-check" class="p-button-danger" @click="confirmReject" />
            </template>
        </Dialog>
    </div>
</template>