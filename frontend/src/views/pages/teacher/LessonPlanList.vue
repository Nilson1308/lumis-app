<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const FilterMatchMode = { CONTAINS: 'contains' };

const toast = useToast();
const route = useRoute();
const router = useRouter();

const plans = ref([]);
const plan = ref({});
const assignments = ref([]); 
const planDialog = ref(false);
const deleteDialog = ref(false);
const loading = ref(true);
const submitted = ref(false);
const coordinators = ref([]);

const filters = ref({ global: { value: null, matchMode: FilterMatchMode.CONTAINS } });

// --- CARREGAR DADOS ---
const loadData = async () => {
    loading.value = true;
    try {
        // 1. Carrega Planos
        const resPlans = await api.get('lesson-plans/?page_size=100');
        let allPlans = resPlans.data.results;

        // Filtro Inteligente (URL)
        if (route.query.assignment) {
            // FORÇA INTEIRO
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
        const resCoords = await api.get('coordinators/');
        coordinators.value = resCoords.data.results.map(u => ({
            id: u.id,
            // Mostra "Nome (Email)" ou só Nome
            label: u.first_name || u.username
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

    // PEGA ID DA URL COM SEGURANÇA
    let preSelectedId = null;
    if (route.query.assignment) {
        preSelectedId = parseInt(route.query.assignment);
        console.log("ID Pré-selecionado:", preSelectedId); // Depuração
    }

    plan.value = {
        start_date: new Date(curr.setDate(first)),
        end_date: new Date(curr.setDate(last)),
        status: 'DRAFT',
        assignment: preSelectedId,
        recipients: []
    };
    submitted.value = false;
    planDialog.value = true;
};

// ... Manter editPlan, confirmDelete, etc ...

const savePlan = async (forceSubmit = false) => {
    submitted.value = true;

    // LOG PARA DEPURAÇÃO
    console.log("Tentando salvar:", plan.value);

    if (!plan.value.assignment || !plan.value.topic || !plan.value.start_date) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha Turma, Data e Tópico.', life: 3000 });
        return;
    }

    const payload = { ...plan.value };
    
    // Ajuste de data seguro
    const formatDate = (d) => {
        if (!d) return null;
        if (d instanceof Date) return d.toISOString().split('T')[0];
        return d;
    };
    
    payload.start_date = formatDate(payload.start_date);
    payload.end_date = formatDate(payload.end_date);

    if (forceSubmit) payload.status = 'SUBMITTED';

    try {
        if (plan.value.id) {
            await api.put(`lesson-plans/${plan.value.id}/`, payload);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Atualizado', life: 3000 });
        } else {
            await api.post('lesson-plans/', payload);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Criado', life: 3000 });
        }
        planDialog.value = false;
        loadData();
    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar.', life: 3000 });
    }
};

// ... Resto das funções (deletePlan, helpers, onMounted) ...
// (Mantenha o resto igual ao anterior)
const editPlan = (item) => {
    plan.value = { ...item };
    if (plan.value.start_date) plan.value.start_date = new Date(plan.value.start_date + 'T00:00:00');
    if (plan.value.end_date) plan.value.end_date = new Date(plan.value.end_date + 'T00:00:00');
    planDialog.value = true;
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
        case 'RETURNED': return 'warning';
        case 'DRAFT': return 'secondary';
        default: return null;
    }
};

const getStatusLabel = (status) => {
    const labels = { 'DRAFT': 'Rascunho', 'SUBMITTED': 'Enviado', 'APPROVED': 'Visto', 'RETURNED': 'Revisar' };
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
                        <div class="flex gap-2">
                            <IconField>
                                <InputIcon>
                                    <i class="pi pi-search" />
                                </InputIcon>
                                <InputText v-model="filters['global'].value" placeholder="Buscar..." @input="onSearch" />
                            </IconField>
                        </div>
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

                <Column field="topic" header="Tópico" sortable style="width: 30%"></Column>
                
                <Column field="status" header="Status" sortable style="width: 15%">
                    <template #body="slotProps">
                        <Tag :severity="getStatusSeverity(slotProps.data.status)" :value="getStatusLabel(slotProps.data.status)" />
                    </template>
                </Column>

                <Column header="Ações" style="width: 15%">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded  mr-2" @click="editPlan(slotProps.data)" />
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
                        <small class="text-500">Deixe vazio para salvar apenas como rascunho pessoal.</small>
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
                        <label class="font-bold text-primary">Desenvolvimento da Aula (O que será feito?)</label>
                        <Editor v-model="plan.description" fluid editorStyle="height: 320px" />
                    </div>

                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-3">Recursos Didáticos</label>
                        <Editor v-model="plan.resources" fluid editorStyle="height: 160px" />
                    </div>

                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-3">Lição de Casa / Fixação</label>
                        <Editor v-model="plan.homework" fluid editorStyle="height: 160px" />
                    </div>

                    <div class="field col-12" v-if="plan.coordinator_note">
                        <label class="font-bold text-orange-500">Nota da Coordenação:</label>
                        <div class="surface-ground p-3 border-round">
                            {{ plan.coordinator_note }}
                        </div>
                    </div>
                </div>

                <template #footer>
                    <div class="flex justify-content-between">
                        <Button label="Apagar" icon="pi pi-trash" class="p-button-text p-button-danger" @click="confirmDelete(plan)" v-if="plan.id" />
                        <div>
                            <Button label="Salvar Rascunho" icon="pi pi-save" class="p-button-secondary mr-2" @click="savePlan(false)" />
                            <Button label="Enviar para Coordenação" icon="pi pi-send" class="p-button-primary" @click="savePlan(true)" />
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