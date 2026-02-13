<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { FilterMatchMode } from '@primevue/core/api'; 
import api from '@/service/api';

const toast = useToast();
const route = useRoute();
const router = useRouter();

const plans = ref([]);
const plan = ref({});
const assignments = ref([]); 
const coordinators = ref([]); 
const planDialog = ref(false);
const deleteDialog = ref(false);
const loading = ref(true);
const submitted = ref(false);

// Controle de Anexos
const fileUploadRef = ref(null);
const newAttachments = ref([]); // Arquivos novos selecionados para upload

const filters = ref({ global: { value: null, matchMode: FilterMatchMode.CONTAINS } });

// --- CARREGAR DADOS ---
const loadData = async () => {
    loading.value = true;
    try {
        const resPlans = await api.get('lesson-plans/?page_size=100');
        let allPlans = resPlans.data.results;

        if (route.query.assignment) {
            const filterId = parseInt(route.query.assignment);
            plans.value = allPlans.filter(p => p.assignment === filterId);
        } else {
            plans.value = allPlans;
        }

        const resAssign = await api.get('assignments/?page_size=100');
        assignments.value = resAssign.data.results.map(a => ({
            id: a.id,
            label: `${a.subject_name} - ${a.classroom_name}`
        }));

        const resCoords = await api.get('coordinators/'); 
        const rawList = resCoords.data.results || resCoords.data;
        coordinators.value = rawList.map(u => ({
            id: u.id,
            label: u.full_name || u.first_name || u.username
        }));

        // Lógica de notificação (abrir modal via URL)
        if (route.query.open === 'true' && route.query.assignment && route.query.date) {
             const targetDate = new Date(route.query.date + 'T00:00:00');
             const endDate = new Date(targetDate);
             endDate.setDate(targetDate.getDate() + 4);

             plan.value = {
                start_date: targetDate,
                end_date: endDate,
                status: 'DRAFT',
                assignment: parseInt(route.query.assignment),
                recipients: [],
                description: '',
                attachments: [] // Lista de anexos existentes
             };
             newAttachments.value = [];
             submitted.value = false;
             planDialog.value = true;
        }

    } catch (e) {
        console.error("Erro ao carregar:", e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha na conexão', life: 3000 });
    } finally {
        loading.value = false;
    }
};

watch(() => route.query.assignment, () => { loadData(); });

// --- AÇÕES ---
const openNew = () => {
    const curr = new Date();
    const first = curr.getDate() - curr.getDay() + 1; 
    const last = first + 4; 

    plan.value = {
        start_date: new Date(curr.setDate(first)),
        end_date: new Date(curr.setDate(last)),
        status: 'DRAFT',
        assignment: route.query.assignment ? parseInt(route.query.assignment) : null,
        recipients: [],
        description: '',
        attachments: [] // Backend deve retornar array de objetos {id, url, name}
    };
    newAttachments.value = [];
    submitted.value = false;
    planDialog.value = true;
};

const editPlan = (item) => {
    // Clona o item
    plan.value = { ...item };
    
    // Garante que attachments seja array
    if (!plan.value.attachments) plan.value.attachments = [];
    
    // Limpa novos anexos ao abrir edição
    newAttachments.value = []; 

    // Tratamento de Datas
    if (plan.value.start_date && typeof plan.value.start_date === 'string') 
        plan.value.start_date = new Date(plan.value.start_date + 'T00:00:00');
    if (plan.value.end_date && typeof plan.value.end_date === 'string') 
        plan.value.end_date = new Date(plan.value.end_date + 'T00:00:00');
        
    planDialog.value = true;
};

// --- UPLOAD: máx 5 arquivos, 5MB total ---
const MAX_FILE_COUNT = 5;
const MAX_TOTAL_SIZE = 5 * 1024 * 1024; // 5 MB (soma de todos os arquivos)

const onFileSelect = (event) => {
    const files = event.files;

    const allowedExtensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png'];
    const allowedMimeTypes = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'image/jpeg',
        'image/jpg',
        'image/png'
    ];

    if (!files || files.length === 0) return;

    // 1. Validação de Quantidade
    if (newAttachments.value.length + files.length > MAX_FILE_COUNT) {
        toast.add({
            severity: 'error',
            summary: 'Limite de Arquivos Excedido',
            detail: `Você pode anexar no máximo ${MAX_FILE_COUNT} arquivos. Você já tem ${newAttachments.value.length} arquivo(s) selecionado(s).`,
            life: 6000
        });
        if (fileUploadRef.value?.clear) fileUploadRef.value.clear();
        return;
    }

    // 2. Validação de Extensão (arquivo por arquivo)
    const invalidFiles = [];
    for (let file of files) {
        const fileName = file.name.toLowerCase();
        const fileExtension = fileName.includes('.') ? '.' + fileName.split('.').pop() : '';
        const isValidExtension = fileExtension && allowedExtensions.includes(fileExtension);
        const isValidMimeType = file.type && allowedMimeTypes.includes(file.type);

        if (!isValidExtension && !isValidMimeType) {
            invalidFiles.push({
                reason: 'extension',
                message: `O arquivo "${file.name}" não é permitido. Extensões: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, JPG, JPEG, PNG`
            });
        }
    }
    if (invalidFiles.length > 0) {
        invalidFiles.forEach(f => toast.add({ severity: 'error', summary: 'Tipo não permitido', detail: f.message, life: 6000 }));
        if (fileUploadRef.value?.clear) fileUploadRef.value.clear();
        return;
    }

    // 3. Validação de Tamanho Total (soma de todos os arquivos)
    const currentTotal = newAttachments.value.reduce((acc, f) => acc + f.size, 0);
    const newFilesTotal = [...files].reduce((acc, f) => acc + f.size, 0);
    const totalSize = currentTotal + newFilesTotal;

    if (totalSize > MAX_TOTAL_SIZE) {
        const totalMB = (totalSize / 1024 / 1024).toFixed(2);
        toast.add({
            severity: 'error',
            summary: 'Limite de Tamanho Excedido',
            detail: `O total dos arquivos não pode ultrapassar 5MB. Total atual: ${totalMB} MB. Ex.: 1 arquivo de 5MB ou 2 arquivos de 2MB.`,
            life: 6000
        });
        if (fileUploadRef.value?.clear) fileUploadRef.value.clear();
        return;
    }

    // Adiciona à lista
    files.forEach(f => {
        if (!newAttachments.value.some(existing => existing.name === f.name)) {
            newAttachments.value.push(f);
        }
    });
    if (fileUploadRef.value?.clear) fileUploadRef.value.clear();

    if (files.length > 0) {
        toast.add({ severity: 'success', summary: 'Arquivo(s) adicionado(s)', detail: `${files.length} arquivo(s) adicionado(s).`, life: 3000 });
    }
};

// Handler para erros do FileUpload (componente detecta problema antes do nosso handler)
const onFileError = (event) => {
    console.error('Erro no FileUpload:', event);
    if (event.files?.length > 0) {
        const file = event.files[0];
        if (file.size > MAX_TOTAL_SIZE) {
            toast.add({
                severity: 'error',
                summary: 'Arquivo muito grande',
                detail: `O arquivo "${file.name}" excede 5MB. Tamanho: ${(file.size / 1024 / 1024).toFixed(2)} MB`,
                life: 6000
            });
        } else {
            toast.add({
                severity: 'error',
                summary: 'Erro ao selecionar arquivo',
                detail: event.error || `Erro ao processar "${file.name}". Verifique o tipo de arquivo.`,
                life: 5000
            });
        }
    } else {
        toast.add({ severity: 'error', summary: 'Erro ao selecionar arquivo', detail: event.error || 'Erro desconhecido.', life: 5000 });
    }
    if (fileUploadRef.value?.clear) fileUploadRef.value.clear();
};

const removeNewAttachment = (index) => {
    newAttachments.value.splice(index, 1);
};

const savePlan = async (forceSubmit = false) => {
    submitted.value = true;

    // Validações básicas
    if (!plan.value.assignment || !plan.value.topic || !plan.value.start_date) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha Turma, Data e Tópico.', life: 3000 });
        submitted.value = false;
        return;
    }

    // Validação CRÍTICA: Se for enviar definitivo (SUBMITTED), coordenador é obrigatório
    if (forceSubmit) {
        let recipients = plan.value.recipients;
        
        // Garante que seja array
        if (!Array.isArray(recipients)) {
            recipients = [];
        }
        
        // Remove valores nulos/undefined
        recipients = recipients.filter(id => id != null && id !== undefined && id !== '');
        
        if (!recipients || recipients.length === 0) {
            toast.add({ 
                severity: 'error', 
                summary: 'Campo Obrigatório', 
                detail: 'É obrigatório selecionar pelo menos um coordenador para enviar o planejamento definitivo.', 
                life: 5000 
            });
            submitted.value = false;
            return; // IMPEDE o envio
        }
    }
    
    // Validação adicional: total dos arquivos <= 5MB
    const totalSize = newAttachments.value.reduce((acc, f) => acc + f.size, 0);
    if (totalSize > MAX_TOTAL_SIZE) {
        const totalMB = (totalSize / 1024 / 1024).toFixed(2);
        toast.add({
            severity: 'error',
            summary: 'Limite de tamanho excedido',
            detail: `O total dos arquivos é ${totalMB} MB. O limite é 5MB.`,
            life: 5000
        });
        submitted.value = false;
        return;
    }

    const formData = new FormData();
    formData.append('assignment', plan.value.assignment);
    formData.append('topic', plan.value.topic);
    formData.append('description', plan.value.description || '');
    
    // --- CORREÇÃO DO MULTISELECT DE COORDENADORES ---
    // Django espera múltiplas chaves 'recipients' para criar uma lista
    if (plan.value.recipients && Array.isArray(plan.value.recipients)) {
       plan.value.recipients.forEach(id => {
           formData.append('recipients', id);
       });
    }

    const formatDate = (d) => {
        if (!d) return '';
        if (d instanceof Date) return d.toISOString().split('T')[0];
        return d;
    };
    formData.append('start_date', formatDate(plan.value.start_date));
    formData.append('end_date', formatDate(plan.value.end_date));

    if (forceSubmit) formData.append('status', 'SUBMITTED');
    else formData.append('status', plan.value.status || 'DRAFT');

    // --- CORREÇÃO DOS ANEXOS MÚLTIPLOS ---
    // Envia cada arquivo como um item na lista 'attachments'
    // IMPORTANTE: O Backend precisa aceitar 'attachments' (plural) no request.FILES
    newAttachments.value.forEach(file => {
        formData.append('attachments', file);
    });

    try {
        const config = { headers: { 'Content-Type': 'multipart/form-data' } };
        
        if (plan.value.id) {
            await api.patch(`lesson-plans/${plan.value.id}/`, formData, config);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Atualizado', life: 3000 });
        } else {
            await api.post('lesson-plans/', formData, config);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Criado', life: 3000 });
        }
        planDialog.value = false;
        loadData();
    } catch (error) {
        console.error('Erro ao salvar planejamento:', error);
        
        // Extrai mensagem de erro específica do backend
        let errorMessage = 'Erro ao salvar planejamento.';
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
            } else if (error.response.data.recipients) {
                // Erro específico de recipients
                const recipientsError = error.response.data.recipients;
                errorMessage = Array.isArray(recipientsError) ? recipientsError[0] : recipientsError;
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
        submitted.value = false;
    }
};

const confirmDelete = (item) => {
    plan.value = item;
    deleteDialog.value = true;
};

const deletePlan = async () => {
    try {
        await api.delete(`lesson-plans/${plan.value.id}/`);
        deleteDialog.value = false;
        plan.value = {};
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Removido', life: 3000 });
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao remover', life: 3000 });
    }
};

const getStatusSeverity = (status) => {
    switch (status) {
        case 'APPROVED': return 'success';
        case 'SUBMITTED': return 'info';
        case 'RETURNED': return 'warn';
        case 'DRAFT': return 'secondary';
        default: return null;
    }
};

const getStatusLabel = (status) => {
    const labels = { 'DRAFT': 'Rascunho', 'SUBMITTED': 'Enviado', 'APPROVED': 'Aprovado', 'RETURNED': 'Correção Solicitada' };
    return labels[status] || status;
};

const clearFilter = () => { router.push({ name: 'lesson-plans' }); };

onMounted(() => { loadData(); });
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            <Toolbar class="mb-4">
                <template v-slot:start>
                    <div class="my-2 flex flex-col md:flex-row gap-2">
                        <Button label="Novo Planejamento" icon="pi pi-plus" class=" mr-2" @click="openNew" />
                        
                        <Button 
                            v-if="route.query.assignment" 
                            label="Ver Todas as Turmas" 
                            icon="pi pi-filter-slash" 
                            class="p-button-outlined p-button-secondary" 
                            @click="clearFilter" 
                        />
                    </div>
                </template>
            </Toolbar>

            <DataTable :value="plans" :filters="filters" :loading="loading" responsiveLayout="scroll" :paginator="true" :rows="10">
                <template #header>
                    <div class="flex flex-wrap gap-2 items-center justify-between">
                        <h4 class="m-0">Meus Planejamentos Semanais</h4>
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText v-model="filters['global'].value" placeholder="Buscar..." />
                        </IconField>
                    </div>
                </template>
                <template #empty>Nenhum planejamento encontrado.</template>
                
                <Column field="start_date" header="Semana" sortable style="width: 15%">
                    <template #body="slotProps">
                        {{ new Date(slotProps.data.start_date + 'T00:00:00').toLocaleDateString('pt-BR') }}
                    </template>
                </Column>
                
                <Column field="classroom_name" header="Turma/Matéria" sortable style="width: 25%">
                    <template #body="slotProps">
                        <span class="font-bold">{{ slotProps.data.subject_name }}</span><br>
                        <span class="text-sm text-600">{{ slotProps.data.classroom_name }}</span>
                    </template>
                </Column>

                <Column field="topic" header="Tópico" sortable style="width: 25%"></Column>
                
                <Column header="Anexos" style="width: 10%">
                    <template #body="slotProps">
                        <div v-if="slotProps.data.attachments && slotProps.data.attachments.length > 0" class="flex gap-2">
                            <span v-if="slotProps.data.attachments.length === 1">
                                <a :href="slotProps.data.attachments[0].file || slotProps.data.attachments[0]" target="_blank" class="text-primary" v-tooltip.top="'Baixar'">
                                    <i class="pi pi-paperclip text-xl"></i>
                                </a>
                            </span>
                            <span v-else class="cursor-pointer text-primary font-bold" @click="editPlan(slotProps.data)" v-tooltip.top="'Ver arquivos'">
                                <i class="pi pi-folder text-xl mr-1"></i> {{ slotProps.data.attachments.length }}
                            </span>
                        </div>
                        <div v-else-if="slotProps.data.attachment">
                             <a :href="slotProps.data.attachment" target="_blank" class="text-primary">
                                <i class="pi pi-paperclip text-xl"></i>
                            </a>
                        </div>
                    </template>
                </Column>

                <Column field="status" header="Status" sortable style="width: 15%">
                    <template #body="slotProps">
                        <Tag :severity="getStatusSeverity(slotProps.data.status)" :value="getStatusLabel(slotProps.data.status)" />
                    </template>
                </Column>

                <Column header="Ações" style="width: 15%">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editPlan(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded p-button-warning" @click="confirmDelete(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="planDialog" :style="{ width: '900px' }" header="Semanário / Planejamento" :modal="true" class="p-fluid" maximizable>
                
                <div class="grid grid-cols-12 gap-4 mb-2">
                    <div class="col-span-12 xl:col-span-12">
                        <label class="block font-bold mb-3">Enviar para (Coordenadores) <span class="text-red-500" v-if="plan.status === 'SUBMITTED' || !plan.id">*</span></label>
                        <MultiSelect 
                            v-model="plan.recipients" 
                            :options="coordinators" 
                            optionLabel="label" 
                            optionValue="id" 
                            placeholder="Selecione pelo menos um coordenador" 
                            display="chip"
                            filter
                            :class="{ 'p-invalid': submitted && (plan.status === 'SUBMITTED' || !plan.id) && (!plan.recipients || plan.recipients.length === 0) }"
                            fluid
                        />
                        <small class="p-error" v-if="submitted && (plan.status === 'SUBMITTED' || !plan.id) && (!plan.recipients || plan.recipients.length === 0)">
                            Selecione pelo menos um coordenador para enviar o planejamento.
                        </small>
                        <small class="text-gray-500" v-else>Selecione quem deve receber este planejamento.</small>
                    </div>

                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-3">Turma / Matéria</label>
                        <Dropdown 
                            v-model="plan.assignment" 
                            :options="assignments" 
                            optionLabel="label" 
                            optionValue="id" 
                            placeholder="Selecione..." 
                            :class="{ 'p-invalid': submitted && !plan.assignment }"
                            filter
                            fluid
                            :disabled="!!route.query.assignment"
                        />
                        <small class="p-error" v-if="submitted && !plan.assignment">Obrigatório.</small>
                    </div>
                    
                    <div class="col-span-12 xl:col-span-3">
                        <label class="block font-bold mb-3">Início Semana</label>
                        <DatePicker v-model="plan.start_date" dateFormat="dd/mm/yy" showIcon fluid />
                    </div>
                    <div class="col-span-12 xl:col-span-3">
                        <label class="block font-bold mb-3">Fim Semana</label>
                        <DatePicker v-model="plan.end_date" dateFormat="dd/mm/yy" showIcon fluid />
                    </div>

                    <div class="col-span-12 xl:col-span-12">
                        <label class="block font-bold mb-3">Tópico Principal / Objetivo</label>
                        <InputText v-model="plan.topic" placeholder="Ex: Introdução à Álgebra" required="true" fluid />
                    </div>

                    <div class="col-span-12 xl:col-span-12">
                        <label class="block font-bold mb-3">Anexar Materiais (Máx 5 arquivos, 5MB total)</label>
                        <small class="text-gray-500 block mb-2">Extensões: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, JPG, JPEG, PNG. Ex.: 1 arquivo de 5MB ou 2 de 2MB.</small>
                        
                        <FileUpload 
                            ref="fileUploadRef"
                            mode="basic" 
                            name="attachments" 
                            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,image/*" 
                            :maxFileSize="5242880"
                            :fileLimit="5"
                            multiple
                            @select="onFileSelect"
                            @error="onFileError"
                            :auto="false" 
                            chooseLabel="Escolher Arquivos" 
                            class="w-full"
                        />
                        
                        <div v-if="newAttachments.length > 0" class="mt-3">
                            <h6 class="text-sm font-bold text-gray-700 mb-2">Novos arquivos para envio:</h6>
                            <ul class="list-none p-0 m-0">
                                <li v-for="(file, index) in newAttachments" :key="index" class="flex align-items-center justify-content-between p-2 surface-100 border-round mb-2">
                                    <div class="flex items-center gap-2">
                                        <i class="pi pi-file text-primary"></i>
                                        <span class="text-sm">{{ file.name }}</span>
                                        <span class="text-xs text-gray-500">({{ (file.size / 1024 / 1024).toFixed(2) }} MB)</span>
                                    </div>
                                    <Button icon="pi pi-times" class="p-button-rounded p-button-danger p-button-text p-button-sm" @click="removeNewAttachment(index)" />
                                </li>
                            </ul>
                        </div>

                        <div v-if="plan.attachments && plan.attachments.length > 0" class="mt-3">
                             <h6 class="text-sm font-bold text-gray-700 mb-2">Arquivos salvos:</h6>
                             <div v-for="att in plan.attachments" :key="att.id || att" class="p-2 border border-gray-200 rounded flex items-center gap-2 mb-1">
                                <i class="pi pi-check-circle text-green-500"></i>
                                <a :href="att.file || att" target="_blank" class="text-primary font-bold hover:underline flex-1 truncate">
                                    {{ att.name || 'Visualizar Anexo' }}
                                </a>
                             </div>
                        </div>
                    </div>

                    <div class="col-span-12 xl:col-span-12">
                        <label class="font-bold text-primary">Desenvolvimento da Aula (O que será feito?)</label>
                        <Editor v-model="plan.description" fluid editorStyle="height: 320px" />
                    </div>

                    <div class="col-span-12" v-if="plan.coordinator_feedback">
                        <label class="font-bold text-orange-500">Feedback da Coordenação:</label>
                        <div class="surface-ground p-3 border-round border-l-4 border-orange-500 mt-1">
                            {{ plan.coordinator_feedback }}
                        </div>
                    </div>
                </div>

                <template #footer>
                    <div class="flex justify-between w-full">
                        <Button label="Apagar" icon="pi pi-trash" class="p-button-text p-button-danger" @click="confirmDelete(plan)" v-if="plan.id" />
                        <div class="flex gap-2">
                            <Button label="Salvar Rascunho" icon="pi pi-save" class="p-button-secondary" @click="savePlan(false)" />
                            <Button label="Enviar Definitivo" icon="pi pi-send" class="p-button-primary" @click="savePlan(true)" />
                        </div>
                    </div>
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-items-center justify-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span>Remover este planejamento?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deletePlan" />
                </template>
            </Dialog>
        </div>
    </div>
</template>