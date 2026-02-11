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
const coordinators = ref([]); // Lista de coordenadores para seleção
const attachmentFile = ref(null); // Arquivo anexo selecionado
const fileUploadRef = ref(null); // Referência ao componente FileUpload

// --- CARREGAR DADOS ---
const fetchReports = async () => {
    loading.value = true;
    try {
        const response = await api.get('weekly-reports/');
        reports.value = response.data.results || response.data;
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar relatórios', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// Carregar lista de coordenadores
const loadCoordinators = async () => {
    try {
        const response = await api.get('coordinators/');
        const rawList = response.data.results || response.data;
        coordinators.value = rawList.map(u => ({
            id: u.id,
            label: u.full_name || `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username
        }));
    } catch (error) {
        console.error('Erro ao carregar coordenadores:', error);
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
        end_date: today,
        recipient_ids: [],
        description: '',
        pending_issues: ''
    };
    attachmentFile.value = null;
    if (fileUploadRef.value && fileUploadRef.value.clear) {
        fileUploadRef.value.clear();
    }
    submitted.value = false;
    reportDialog.value = true;
};

const editReport = (item) => {
    report.value = { ...item };
    // Converte strings para Date
    if (report.value.start_date) report.value.start_date = new Date(report.value.start_date);
    if (report.value.end_date) report.value.end_date = new Date(report.value.end_date);
    // Garante que recipient_ids seja um array
    if (report.value.recipient_ids && !Array.isArray(report.value.recipient_ids)) {
        report.value.recipient_ids = [];
    } else if (!report.value.recipient_ids) {
        report.value.recipient_ids = [];
    }
    attachmentFile.value = null;
    if (fileUploadRef.value && fileUploadRef.value.clear) {
        fileUploadRef.value.clear();
    }
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


// Handler para seleção de arquivo
const onFileSelect = (event) => {
    const file = event.files && event.files.length > 0 ? event.files[0] : null;
    
    if (file) {
        const maxSize = 2 * 1024 * 1024; // 2MB
        
        // Valida tamanho ANTES de aceitar
        if (file.size > maxSize) {
            toast.add({ 
                severity: 'error', 
                summary: 'Arquivo muito grande', 
                detail: `O arquivo anexo não pode ser maior que 2MB. Tamanho atual: ${(file.size / 1024 / 1024).toFixed(2)} MB`, 
                life: 5000 
            });
            // Limpa o arquivo selecionado
            attachmentFile.value = null;
            // Limpa o componente FileUpload
            if (fileUploadRef.value && fileUploadRef.value.clear) {
                fileUploadRef.value.clear();
            }
            return;
        }
        
        // Aceita o arquivo
        attachmentFile.value = file;
    }
};

// Handler para erro do FileUpload
const onFileError = (event) => {
    console.error('Erro no FileUpload:', event);
    if (event.files && event.files.length > 0) {
        const file = event.files[0];
        if (file.size > 2 * 1024 * 1024) {
            toast.add({ 
                severity: 'error', 
                summary: 'Arquivo muito grande', 
                detail: 'O arquivo anexo não pode ser maior que 2MB. Tamanho: ' + (file.size / 1024 / 1024).toFixed(2) + ' MB', 
                life: 5000 
            });
        } else {
            toast.add({ 
                severity: 'error', 
                summary: 'Erro', 
                detail: event.error || 'Erro ao selecionar arquivo', 
                life: 3000 
            });
        }
    }
    attachmentFile.value = null;
};

// --- SALVAR ---
const saveReport = async () => {
    submitted.value = true;

    // Validações básicas
    if (!report.value.start_date || !report.value.end_date || !report.value.description) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha todos os campos obrigatórios.', life: 3000 });
        submitted.value = false;
        return;
    }

    // Validação CRÍTICA de coordenadores - verifica de múltiplas formas
    let recipientIds = report.value.recipient_ids;
    
    // Garante que seja array
    if (!Array.isArray(recipientIds)) {
        recipientIds = [];
    }
    
    // Remove valores nulos/undefined
    recipientIds = recipientIds.filter(id => id != null && id !== undefined && id !== '');
    
    // Validação final
    if (!recipientIds || recipientIds.length === 0) {
        toast.add({ 
            severity: 'error', 
            summary: 'Campo Obrigatório', 
            detail: 'É obrigatório selecionar pelo menos um coordenador para envio do relatório.', 
            life: 5000 
        });
        submitted.value = false;
        return; // IMPEDE o envio
    }

    // Validação de arquivo se houver
    if (attachmentFile.value) {
        const maxSize = 2 * 1024 * 1024; // 2MB
        if (attachmentFile.value.size > maxSize) {
            toast.add({ 
                severity: 'error', 
                summary: 'Arquivo muito grande', 
                detail: `O arquivo anexo não pode ser maior que 2MB. Tamanho atual: ${(attachmentFile.value.size / 1024 / 1024).toFixed(2)} MB`, 
                life: 5000 
            });
            submitted.value = false;
            return; // IMPEDE o envio
        }
    }

    try {
        const formData = new FormData();
        
        // Campos do formulário
        formData.append('start_date', formatDateAPI(report.value.start_date));
        formData.append('end_date', formatDateAPI(report.value.end_date));
        formData.append('description', report.value.description);
        if (report.value.pending_issues) {
            formData.append('pending_issues', report.value.pending_issues);
        }
        
        // Coordenadores destinatários (OBRIGATÓRIO - já validado acima)
        recipientIds.forEach(id => {
            formData.append('recipient_ids', id);
        });
        
        // Arquivo anexo (se houver)
        if (attachmentFile.value) {
            formData.append('attachment', attachmentFile.value);
        }

        if (report.value.id) {
            await api.patch(`weekly-reports/${report.value.id}/`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Relatório atualizado', life: 3000 });
        } else {
            await api.post('weekly-reports/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Relatório enviado', life: 3000 });
        }
        reportDialog.value = false;
        attachmentFile.value = null;
        if (fileUploadRef.value && fileUploadRef.value.clear) {
            fileUploadRef.value.clear();
        }
        fetchReports();
    } catch (error) {
        console.error('Erro ao salvar relatório:', error);
        // Extrai mensagem de erro específica do backend
        let errorMessage = 'Erro ao salvar relatório.';
        if (error.response && error.response.data) {
            // Tenta pegar mensagem de erro do Django REST Framework
            if (error.response.data.detail) {
                errorMessage = error.response.data.detail;
            } else if (error.response.data.error) {
                errorMessage = error.response.data.error;
            } else if (error.response.data.message) {
                errorMessage = error.response.data.message;
            } else if (typeof error.response.data === 'string') {
                errorMessage = error.response.data;
            } else if (Array.isArray(error.response.data)) {
                errorMessage = error.response.data.join(', ');
            } else if (error.response.data.non_field_errors) {
                errorMessage = error.response.data.non_field_errors.join(', ');
            } else {
                // Tenta pegar primeiro erro de campo encontrado
                const firstError = Object.values(error.response.data)[0];
                if (Array.isArray(firstError)) {
                    errorMessage = firstError[0];
                } else if (typeof firstError === 'string') {
                    errorMessage = firstError;
                }
            }
        } else if (error.message) {
            errorMessage = error.message;
        }
        toast.add({ severity: 'error', summary: 'Erro ao Salvar', detail: errorMessage, life: 5000 });
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
    loadCoordinators();
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

            <Dialog v-model:visible="reportDialog" :style="{ width: '800px' }" header="Relatório Semanal" :modal="true" class="p-fluid" maximizable>
                
                <div class="grid grid-cols-12 gap-4 mb-2">
                    <div class="col-span-12 xl:col-span-6">
                        <label class="mb-2 block font-bold">Data Início</label>
                        <DatePicker v-model="report.start_date" dateFormat="dd/mm/yy" showIcon fluid />
                    </div>
                    <div class="col-span-12 xl:col-span-6">
                        <label class="mb-2 block font-bold">Data Fim</label>
                        <DatePicker v-model="report.end_date" dateFormat="dd/mm/yy" showIcon fluid />
                    </div>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold">Resumo das Atividades</label>
                    <Editor v-model="report.description" rows="8" autoResize placeholder="O que foi realizado nesta semana?" :class="{ 'p-invalid': submitted && !report.description }" fluid editorStyle="height: 320px" />
                    <small class="p-error" v-if="submitted && !report.description">Obrigatório.</small>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold text-red-500">Pendências / Pontos de Atenção</label>
                    <Editor v-model="report.pending_issues" rows="4" autoResize placeholder="Algum problema não resolvido? Aluno crítico?" fluid editorStyle="height: 320px" />
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold">Enviar para Coordenadores <span class="text-red-500">*</span></label>
                    <MultiSelect 
                        v-model="report.recipient_ids" 
                        :options="coordinators" 
                        optionLabel="label" 
                        optionValue="id" 
                        placeholder="Selecione pelo menos um coordenador" 
                        filter
                        :class="{ 'p-invalid': submitted && (!report.recipient_ids || report.recipient_ids.length === 0) }"
                        fluid
                    />
                    <small class="p-error" v-if="submitted && (!report.recipient_ids || report.recipient_ids.length === 0)">Selecione pelo menos um coordenador.</small>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold">Anexo (Opcional - Máximo 2MB)</label>
                    <FileUpload 
                        ref="fileUploadRef"
                        mode="basic" 
                        :maxFileSize="2097152"
                        accept="*/*"
                        :auto="false"
                        chooseLabel="Selecionar Arquivo"
                        @select="onFileSelect"
                        @error="onFileError"
                        :showUploadButton="false"
                        :showCancelButton="false"
                        class="w-full"
                    />
                    <small v-if="attachmentFile" class="text-sm text-gray-500 block mt-2">
                        Arquivo selecionado: {{ attachmentFile.name }} ({{ (attachmentFile.size / 1024 / 1024).toFixed(2) }} MB)
                        <Button icon="pi pi-times" class="p-button-text p-button-sm ml-2" @click="attachmentFile = null; fileUploadRef?.clear()" v-tooltip="'Remover arquivo'" />
                    </small>
                    <small v-else class="text-sm text-gray-400 block mt-1">
                        Nenhum arquivo selecionado
                    </small>
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