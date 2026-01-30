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
const coordinators = ref([]); // Lista de coordenadores
const planDialog = ref(false);
const deleteDialog = ref(false);
const loading = ref(true);
const submitted = ref(false);

const filters = ref({ global: { value: null, matchMode: FilterMatchMode.CONTAINS } });

// --- CARREGAR DADOS ---
const loadData = async () => {
    loading.value = true;
    try {
        // 1. Carrega Planos
        const resPlans = await api.get('lesson-plans/?page_size=100');
        let allPlans = resPlans.data.results;

        if (route.query.assignment) {
            const filterId = parseInt(route.query.assignment);
            plans.value = allPlans.filter(p => p.assignment === filterId);
        } else {
            plans.value = allPlans;
        }

        // 2. Carrega Atribuições
        const resAssign = await api.get('assignments/?page_size=100');
        assignments.value = resAssign.data.results.map(a => ({
            id: a.id,
            label: `${a.subject_name} - ${a.classroom_name}`
        }));

        // 3. NOVO: Carrega Coordenadores
        // Ajuste a URL se for 'academic/coordinators/' ou apenas 'coordinators/' conforme sua rota
        const resCoords = await api.get('coordinators/'); 
        
        const rawList = resCoords.data.results || resCoords.data;
        
        // AQUI ESTÁ A CORREÇÃO: Criamos o campo 'label' manualmente
        coordinators.value = rawList.map(u => ({
            id: u.id,
            label: u.full_name || u.first_name || u.username // Usa o nome completo, ou primeiro nome, ou usuário
        }));

    } catch (e) {
        console.error("Erro ao carregar:", e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha na conexão' });
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

    let preSelectedId = null;
    if (route.query.assignment) {
        preSelectedId = parseInt(route.query.assignment);
    }

    plan.value = {
        start_date: new Date(curr.setDate(first)),
        end_date: new Date(curr.setDate(last)),
        status: 'DRAFT',
        assignment: preSelectedId,
        recipients: [], // Mantido
        description: '', // Desenvolvimento
        attachment: null
    };
    submitted.value = false;
    planDialog.value = true;
};

const editPlan = (item) => {
    plan.value = { ...item };
    
    // Tratamento de Datas
    if (plan.value.start_date && typeof plan.value.start_date === 'string') 
        plan.value.start_date = new Date(plan.value.start_date + 'T00:00:00');
    if (plan.value.end_date && typeof plan.value.end_date === 'string') 
        plan.value.end_date = new Date(plan.value.end_date + 'T00:00:00');
        
    planDialog.value = true;
};

const onFileSelect = (event) => {
    plan.value.attachment = event.files[0];
};

const savePlan = async (forceSubmit = false) => {
    submitted.value = true;

    if (!plan.value.assignment || !plan.value.topic || !plan.value.start_date) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha Turma, Data e Tópico.', life: 3000 });
        return;
    }

    // --- USANDO FORMDATA (Obrigatório para Arquivos) ---
    const formData = new FormData();
    formData.append('assignment', plan.value.assignment);
    formData.append('topic', plan.value.topic);
    formData.append('description', plan.value.description || ''); // Editor Content
    
    // Se tiver destinatários (array), envia (pode precisar de ajuste no backend para ManyToMany)
    if (plan.value.recipients && Array.isArray(plan.value.recipients)) {
       // formData.append('recipients', JSON.stringify(plan.value.recipients)); // Opcional
    }

    const formatDate = (d) => {
        if (!d) return '';
        if (d instanceof Date) return d.toISOString().split('T')[0];
        return d;
    };
    formData.append('start_date', formatDate(plan.value.start_date));
    formData.append('end_date', formatDate(plan.value.end_date));

    if (forceSubmit) {
        formData.append('status', 'SUBMITTED');
    } else {
        formData.append('status', plan.value.status || 'DRAFT');
    }

    // Anexo (Só envia se for File novo)
    if (plan.value.attachment instanceof File) {
        formData.append('attachment', plan.value.attachment);
    }

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
        console.error(error);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar.', life: 3000 });
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
const onSearch = () => { /* Busca via v-model */ };

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
                
                <Column header="Anexo" style="width: 5%">
                    <template #body="slotProps">
                        <a v-if="slotProps.data.attachment" :href="slotProps.data.attachment" target="_blank" class="text-primary" v-tooltip.top="'Baixar Anexo'">
                            <i class="pi pi-paperclip text-xl"></i>
                        </a>
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
                        <label class="block font-bold mb-3">Enviar para (Coordenadores)</label>
                        <MultiSelect 
                            v-model="plan.recipients" 
                            :options="coordinators" 
                            optionLabel="label" 
                            optionValue="id" 
                            placeholder="Selecione..." 
                            display="chip"
                            fluid
                        />
                        <small class="text-gray-500">Notificar coordenadores específicos (opcional).</small>
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
                        <label class="block font-bold mb-3">Anexar Planejamento/Atividade (PDF, Office, Img)</label>
                        <FileUpload 
                            mode="basic" 
                            name="attachment" 
                            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,image/*" 
                            :maxFileSize="5000000" 
                            @select="onFileSelect" 
                            :auto="false" 
                            chooseLabel="Escolher Arquivo" 
                            class="w-full"
                        />
                        <div v-if="plan.attachment && typeof plan.attachment === 'string'" class="mt-2 p-2 border border-gray-200 rounded flex items-center gap-2">
                            <i class="pi pi-check-circle text-green-500"></i>
                            <span class="text-sm">Arquivo salvo: </span>
                            <a :href="plan.attachment" target="_blank" class="text-primary font-bold hover:underline">Visualizar</a>
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
                <div class="flex align-items-center justify-content-center">
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