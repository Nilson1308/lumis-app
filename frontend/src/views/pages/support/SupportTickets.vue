<script setup>
import { ref, onMounted, computed } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();

const tickets = ref([]);
const loading = ref(true);
const saving = ref(false);
const loadingDetail = ref(false);

const createDialogVisible = ref(false);
const detailDialogVisible = ref(false);
const selectedTicket = ref(null);

const attachmentFile = ref(null);
const attachmentInputRef = ref(null);
const attachmentLabel = ref('');

const form = ref({
    occurred_date: new Date(),
    occurred_time: '08:00',
    description: '',
});

const formatDateForApi = (date) => {
    if (!date) return '';
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const formatDateBR = (value) => {
    if (!value) return '';
    if (typeof value === 'string' && value.includes('-')) {
        const [y, m, d] = value.split('-');
        return `${d}/${m}/${y}`;
    }
    return new Date(value).toLocaleDateString('pt-BR');
};

const formatTimeBR = (value) => {
    if (!value) return '';
    return String(value).slice(0, 5);
};

const formatDateTimeBR = (value) => {
    if (!value) return '';
    return new Date(value).toLocaleString('pt-BR');
};

const statusSeverity = (status) => {
    const map = {
        OPEN: 'warn',
        IN_PROGRESS: 'info',
        RESOLVED: 'success',
        CANCELLED: 'secondary',
    };
    return map[status] || 'secondary';
};

const truncate = (text, max = 80) => {
    const cleaned = (text || '').trim();
    if (cleaned.length <= max) return cleaned;
    return `${cleaned.slice(0, max)}…`;
};

const loadTickets = async () => {
    loading.value = true;
    try {
        const { data } = await api.get('support-tickets/');
        tickets.value = data.results || data;
    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Não foi possível carregar os chamados.', life: 4000 });
        tickets.value = [];
    } finally {
        loading.value = false;
    }
};

const resetForm = () => {
    form.value = {
        occurred_date: new Date(),
        occurred_time: '08:00',
        description: '',
    };
    attachmentFile.value = null;
    attachmentLabel.value = '';
    if (attachmentInputRef.value) {
        attachmentInputRef.value.value = '';
    }
};

const onAttachmentInputChange = (event) => {
    const file = event.target?.files?.[0];
    attachmentFile.value = file instanceof File ? file : null;
    attachmentLabel.value = attachmentFile.value?.name || '';
};

const clearAttachment = () => {
    attachmentFile.value = null;
    attachmentLabel.value = '';
    if (attachmentInputRef.value) {
        attachmentInputRef.value.value = '';
    }
};

const openCreateDialog = () => {
    resetForm();
    createDialogVisible.value = true;
};

const submitTicket = async () => {
    const description = form.value.description?.trim();
    if (!form.value.occurred_date || !form.value.occurred_time || !description) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha data, hora e descrição.', life: 3500 });
        return;
    }

    saving.value = true;
    try {
        const fd = new FormData();
        fd.append('occurred_date', formatDateForApi(form.value.occurred_date));
        let timeValue = form.value.occurred_time;
        if (timeValue && timeValue.length === 5) {
            timeValue = `${timeValue}:00`;
        }
        fd.append('occurred_time', timeValue);
        fd.append('description', description);
        if (attachmentFile.value instanceof File) {
            fd.append('attachment', attachmentFile.value, attachmentFile.value.name);
        }

        await api.post('support-tickets/', fd);
        toast.add({ severity: 'success', summary: 'Chamado aberto', detail: 'Seu chamado foi registrado com sucesso.', life: 3500 });
        createDialogVisible.value = false;
        await loadTickets();
    } catch (error) {
        const data = error.response?.data;
        const msg = data?.description?.[0] || data?.attachment?.[0] || data?.detail || 'Erro ao abrir chamado.';
        toast.add({ severity: 'error', summary: 'Falha', detail: msg, life: 5000 });
    } finally {
        saving.value = false;
    }
};

const openTicketDetail = async (ticket) => {
    loadingDetail.value = true;
    detailDialogVisible.value = true;
    selectedTicket.value = null;
    try {
        const { data } = await api.get(`support-tickets/${ticket.id}/`);
        selectedTicket.value = data;
    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Não foi possível carregar o chamado.', life: 4000 });
        detailDialogVisible.value = false;
    } finally {
        loadingDetail.value = false;
    }
};

const attachmentUrl = computed(() => {
    const file = selectedTicket.value?.attachment;
    if (!file) return null;
    if (String(file).startsWith('http')) return file;
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    return `${origin}${file.startsWith('/') ? file : `/${file}`}`;
});

onMounted(() => {
    loadTickets();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />

            <div class="flex flex-col md:flex-row justify-between align-items-start md:align-items-center gap-3 mb-4">
                <div>
                    <h2 class="font-bold text-900 m-0">Suporte</h2>
                    <p class="text-500 m-0 mt-1">Abra um chamado e acompanhe as respostas da equipe.</p>
                </div>
                <Button label="Novo chamado" icon="pi pi-plus" @click="openCreateDialog" />
            </div>

            <DataTable
                :value="tickets"
                :loading="loading"
                responsiveLayout="scroll"
                stripedRows
                rowHover
                @row-click="(e) => openTicketDetail(e.data)"
                class="cursor-pointer"
            >
                <template #empty>Nenhum chamado registrado.</template>

                <Column field="id" header="#" style="width: 4rem">
                    <template #body="{ data }">#{{ data.id }}</template>
                </Column>
                <Column header="Data / Hora" style="width: 9rem">
                    <template #body="{ data }">
                        {{ formatDateBR(data.occurred_date) }}
                        <span class="text-500"> {{ formatTimeBR(data.occurred_time) }}</span>
                    </template>
                </Column>
                <Column header="Descrição">
                    <template #body="{ data }">{{ truncate(data.description) }}</template>
                </Column>
                <Column header="Status" style="width: 9rem">
                    <template #body="{ data }">
                        <Tag :value="data.status_label" :severity="statusSeverity(data.status)" />
                    </template>
                </Column>
                <Column header="Respostas" style="width: 6rem; text-align: center">
                    <template #body="{ data }">
                        <Badge v-if="data.replies_count > 0" :value="data.replies_count" severity="info" />
                        <span v-else class="text-500">—</span>
                    </template>
                </Column>
                <Column header="Aberto em" style="width: 9rem">
                    <template #body="{ data }">{{ formatDateBR(data.created_at?.slice?.(0, 10) || data.created_at) }}</template>
                </Column>
            </DataTable>
        </div>

        <Dialog v-model:visible="createDialogVisible" header="Novo chamado" :modal="true" :style="{ width: '520px' }">
            <div class="flex flex-col gap-4">
                <div>
                    <label class="font-bold block mb-2">Data da ocorrência</label>
                    <DatePicker v-model="form.occurred_date" dateFormat="dd/mm/yy" showIcon fluid />
                </div>
                <div>
                    <label class="font-bold block mb-2">Hora</label>
                    <InputText v-model="form.occurred_time" type="time" fluid />
                </div>
                <div>
                    <label class="font-bold block mb-2">Descrição</label>
                    <Textarea v-model="form.description" rows="5" autoResize fluid placeholder="Descreva o problema ou solicitação..." />
                </div>
                <div>
                    <label class="font-bold block mb-2">Anexo (opcional)</label>
                    <div class="flex flex-wrap align-items-center gap-2">
                        <input
                            ref="attachmentInputRef"
                            type="file"
                            style="display: none"
                            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png,image/*"
                            @change="onAttachmentInputChange"
                        />
                        <Button
                            type="button"
                            label="Selecionar arquivo"
                            icon="pi pi-upload"
                            severity="secondary"
                            outlined
                            @click="attachmentInputRef?.click()"
                        />
                        <Button
                            v-if="attachmentFile"
                            type="button"
                            icon="pi pi-times"
                            severity="secondary"
                            text
                            rounded
                            v-tooltip.top="'Remover anexo'"
                            @click="clearAttachment"
                        />
                    </div>
                    <small v-if="attachmentLabel" class="text-600 block mt-1">{{ attachmentLabel }}</small>
                    <small class="text-500 block mt-1">Máx. 5 MB — PDF, Office ou imagem.</small>
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="createDialogVisible = false" />
                <Button label="Abrir chamado" icon="pi pi-check" :loading="saving" @click="submitTicket" />
            </template>
        </Dialog>

        <Dialog
            v-model:visible="detailDialogVisible"
            :header="selectedTicket ? `Chamado #${selectedTicket.id}` : 'Chamado'"
            :modal="true"
            :style="{ width: '640px' }"
        >
            <div v-if="loadingDetail" class="flex justify-content-center p-4">
                <ProgressSpinner style="width: 40px; height: 40px" />
            </div>
            <div v-else-if="selectedTicket" class="flex flex-col gap-4">
                <div class="flex flex-wrap gap-2 align-items-center">
                    <Tag :value="selectedTicket.status_label" :severity="statusSeverity(selectedTicket.status)" />
                    <span class="text-500 text-sm">
                        Ocorrência: {{ formatDateBR(selectedTicket.occurred_date) }} às {{ formatTimeBR(selectedTicket.occurred_time) }}
                    </span>
                </div>
                <div class="surface-100 border-round p-3">
                    <p class="m-0 white-space-pre-wrap">{{ selectedTicket.description }}</p>
                    <div v-if="attachmentUrl" class="mt-2">
                        <a :href="attachmentUrl" target="_blank" rel="noopener" class="text-primary">
                            <i class="pi pi-paperclip mr-1"></i> Baixar anexo
                        </a>
                    </div>
                </div>

                <div>
                    <h4 class="font-bold mt-0 mb-2">Respostas</h4>
                    <div v-if="!selectedTicket.replies?.length" class="text-500 text-sm">
                        Ainda não há respostas públicas. A equipe responderá em breve.
                    </div>
                    <div v-else class="flex flex-col gap-3">
                        <div
                            v-for="reply in selectedTicket.replies"
                            :key="reply.id"
                            class="border-left-3 border-primary pl-3"
                        >
                            <div class="text-sm font-semibold text-900">{{ reply.author_name }}</div>
                            <div class="text-xs text-500 mb-1">{{ formatDateTimeBR(reply.created_at) }}</div>
                            <p class="m-0 white-space-pre-wrap">{{ reply.message }}</p>
                        </div>
                    </div>
                </div>
            </div>
            <template #footer>
                <Button label="Fechar" icon="pi pi-times" class="p-button-text" @click="detailDialogVisible = false" />
            </template>
        </Dialog>
    </div>
</template>
