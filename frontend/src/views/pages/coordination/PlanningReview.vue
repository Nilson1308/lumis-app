<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const route = useRoute();
const toast = useToast();
const plans = ref([]);
const loading = ref(true);

// Controle do Dialog de Avaliação
const reviewDialog = ref(false);
const currentPlan = ref({});
const feedbackText = ref('');

// Listas para Filtros
const teachers = ref([]);
const classrooms = ref([]);
const subjects = ref([]);

const unsubscribeDialog = ref(false);

// Filtros Ativos
const filters = ref({
    status: null,
    teacher: null,
    classroom: null,
    subject: null,
    assignment: null
});

// Paginação
const totalRecords = ref(0);
const lazyParams = ref({
    first: 0,
    rows: 10,
    page: 0
});

const statusOptions = ref([
    {label: 'Rascunho', value: 'DRAFT'},
    {label: 'Enviado', value: 'SUBMITTED'},
    {label: 'Aprovado', value: 'APPROVED'},
    {label: 'Correção', value: 'RETURNED'}
]);

onMounted(() => {
    loadFilterOptions(); 
    loadPlans();         
});

const loadFilterOptions = async () => {
    try {
        const { data: assignments } = await api.get('assignments/?page_size=1000');
        
        const uniqueTeachers = new Map();
        assignments.results.forEach(a => uniqueTeachers.set(a.teacher, a.teacher_name));
        teachers.value = Array.from(uniqueTeachers, ([id, name]) => ({ id, name }));

        const uniqueClasses = new Map();
        assignments.results.forEach(a => uniqueClasses.set(a.classroom, a.classroom_name));
        classrooms.value = Array.from(uniqueClasses, ([id, name]) => ({ id, name }));

        const uniqueSubjects = new Map();
        assignments.results.forEach(a => uniqueSubjects.set(a.subject, a.subject_name));
        subjects.value = Array.from(uniqueSubjects, ([id, name]) => ({ id, name }));

    } catch (e) {
        console.error("Erro ao carregar filtros", e);
    }
};

const loadPlans = async () => {
    loading.value = true;
    try {
        // --- PAGINAÇÃO ---
        const page = lazyParams.value.page + 1; // Django começa em 1
        const pageSize = lazyParams.value.rows;
        
        let query = `lesson-plans/?page=${page}&page_size=${pageSize}`;

        if (route.query.assignment) {
            query += `&assignment=${route.query.assignment}`;
        } else {
            if (filters.value.status) query += `&status=${filters.value.status}`;
            if (filters.value.teacher) query += `&assignment__teacher=${filters.value.teacher}`;
            if (filters.value.classroom) query += `&assignment__classroom=${filters.value.classroom}`;
            if (filters.value.subject) query += `&assignment__subject=${filters.value.subject}`;
        }

        const { data } = await api.get(query);
        
        plans.value = data.results;
        totalRecords.value = data.count; // Total real do banco
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados', life: 3000 });
    } finally {
        loading.value = false;
    }
};

const onPage = (event) => {
    lazyParams.value = event;
    loadPlans();
};

const clearFilters = () => {
    filters.value = { status: null, teacher: null, classroom: null, subject: null };
    lazyParams.value.first = 0;
    lazyParams.value.page = 0;
    loadPlans();
};

// --- ABRIR MODAL DE REVISÃO ---
const openReview = (plan) => {
    currentPlan.value = plan;
    feedbackText.value = plan.coordinator_feedback || ''; 
    reviewDialog.value = true;
};

const saveFeedback = async (status) => {
    try {
        await api.patch(`lesson-plans/${currentPlan.value.id}/`, {
            status: status,
            coordinator_feedback: feedbackText.value
        });
        toast.add({ severity: 'success', summary: 'Avaliado', detail: `Status definido como ${getStatusLabel(status)}`, life: 3000 });
        reviewDialog.value = false;
        loadPlans();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar avaliação', life: 3000 });
    }
};

const getSeverity = (status) => {
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

const unsubscribePlan = async () => {
    if (!confirm("Tem certeza que deseja sair da lista de destinatários deste plano? Você deixará de vê-lo.")) return;

    try {
        await api.post(`lesson-plans/${currentPlan.value.id}/unsubscribe/`);
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Você deixou de acompanhar este plano.', life: 3000 });
        reviewDialog.value = false;
        loadPlans(); // Recarrega a lista (o plano deve sumir)
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao processar solicitação.', life: 3000 });
    }
};

// 1. Apenas abre o modal
const confirmUnsubscribe = () => {
    unsubscribeDialog.value = true;
};

// 2. Executa a ação real (Chamada no botão "Sim" do Dialog)
const executeUnsubscribe = async () => {
    try {
        await api.post(`lesson-plans/${currentPlan.value.id}/unsubscribe/`);
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Você deixou de acompanhar este plano.', life: 3000 });
        
        unsubscribeDialog.value = false; // Fecha confirmação
        reviewDialog.value = false;      // Fecha o modal do plano
        loadPlans();                     // Atualiza a lista
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao processar solicitação.', life: 3000 });
    }
};
</script>

<template>
    <div class="card">
        <h4>Análise de Planejamentos</h4>
        
        <Toolbar class="mb-4">
            <template #start>
                <div class="flex flex-wrap gap-2 items-center">
                    <Dropdown 
                        v-model="filters.teacher" 
                        :options="teachers" 
                        optionLabel="name" 
                        optionValue="id" 
                        placeholder="Professor" 
                        showClear 
                        filter 
                        class="w-40 md:w-56"
                    />
                    <Dropdown 
                        v-model="filters.classroom" 
                        :options="classrooms" 
                        optionLabel="name" 
                        optionValue="id" 
                        placeholder="Turma" 
                        showClear 
                        filter 
                        class="w-32 md:w-40"
                    />
                    <Dropdown 
                        v-model="filters.status" 
                        :options="statusOptions" 
                        optionLabel="label" 
                        optionValue="value" 
                        placeholder="Status" 
                        showClear 
                        class="w-32 md:w-40"
                    />
                    <Button icon="pi pi-search" label="Filtrar" @click="loadPlans" />
                    <Button icon="pi pi-filter-slash" class="p-button-outlined p-button-secondary" @click="clearFilters" v-tooltip="'Limpar'" />
                </div>
            </template>
        </Toolbar>

        <DataTable 
            :value="plans" 
            :loading="loading" 
            :paginator="true" 
            :rows="10" 
            :totalRecords="totalRecords"
            :lazy="true"
            :first="lazyParams.first"
            @page="onPage"
            responsiveLayout="scroll"
        >
            <template #empty>Nenhum planejamento encontrado.</template>
            
            <Column field="start_date" header="Semana" sortable>
                <template #body="slotProps">
                    {{ new Date(slotProps.data.start_date + 'T00:00:00').toLocaleDateString('pt-BR') }}
                </template>
            </Column>
            <Column field="teacher_name" header="Professor" sortable></Column>
            <Column field="subject_name" header="Disciplina" sortable></Column>
            <Column field="classroom_name" header="Turma" sortable></Column>
            
            <Column header="Anexos">
                <template #body="slotProps">
                    <div v-if="slotProps.data.attachments && slotProps.data.attachments.length > 0" class="flex gap-2">
                        <span v-if="slotProps.data.attachments.length === 1">
                            <a :href="slotProps.data.attachments[0].file" target="_blank" class="text-primary" v-tooltip.top="'Baixar'">
                                <i class="pi pi-paperclip text-xl"></i>
                            </a>
                        </span>
                        <span v-else class="text-primary font-bold cursor-pointer" @click="openReview(slotProps.data)" v-tooltip.top="'Ver todos'">
                            <i class="pi pi-folder text-xl mr-1"></i> {{ slotProps.data.attachments.length }}
                        </span>
                    </div>
                    <div v-else-if="slotProps.data.attachment">
                         <a :href="slotProps.data.attachment" target="_blank" class="text-primary">
                            <i class="pi pi-paperclip text-xl"></i>
                        </a>
                    </div>
                    <span v-else class="text-gray-400">-</span>
                </template>
            </Column>
            
            <Column field="status" header="Status">
                <template #body="slotProps">
                    <Tag :value="getStatusLabel(slotProps.data.status)" :severity="getSeverity(slotProps.data.status)" />
                </template>
            </Column>
            <Column header="Enviado em">
                <template #body="slotProps">
                    <span v-if="slotProps.data.updated_at">
                        {{ new Date(slotProps.data.updated_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) }}
                    </span>
                    <span v-else class="text-gray-400">-</span>
                </template>
            </Column>
            
            <Column header="Ações">
                <template #body="slotProps">
                    <Button icon="pi pi-eye" label="Revisar" class="p-button-sm" @click="openReview(slotProps.data)" />
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="reviewDialog" header="Revisão do Planejamento" :style="{width: '900px'}" :modal="true" maximizable>
            <div class="grid grid-cols-12 gap-4">
                <div class="col-span-12 md:col-span-8">
                    <div class="mb-3">
                        <span class="text-sm text-gray-500 block">Tópico / Objetivo</span>
                        <h3 class="m-0 font-bold text-xl">{{ currentPlan.topic }}</h3>
                        <span v-if="currentPlan.updated_at" class="text-sm text-600 mt-2 block">
                            <i class="pi pi-clock mr-1"></i> Enviado em {{ new Date(currentPlan.updated_at).toLocaleString('pt-BR', { dateStyle: 'long', timeStyle: 'short' }) }}
                        </span>
                    </div>
                    
                    <div class="mb-4">
                        <span class="text-sm text-gray-500 block mb-1">Desenvolvimento</span>
                        
                        <div class="surface-100 p-3 border-round overflow-auto max-h-[500px]">
                            <div v-html="currentPlan.description || 'Sem descrição.'" class="html-content"></div>
                        </div>
                    </div>

                    <div v-if="(currentPlan.attachments && currentPlan.attachments.length) || currentPlan.attachment" class="mb-4">
                        <span class="text-sm text-gray-500 block mb-2">Arquivos Anexados</span>
                        <div v-if="currentPlan.attachments">
                            <div v-for="att in currentPlan.attachments" :key="att.id" class="flex items-center gap-2 mb-2 p-2 surface-50 border-round">
                                <i class="pi pi-file text-primary"></i>
                                <a :href="att.file" target="_blank" class="font-bold text-primary hover:underline">
                                    {{ att.name || 'Download Anexo' }}
                                </a>
                                <span class="text-xs text-gray-500 ml-auto">{{ new Date(att.uploaded_at).toLocaleDateString() }}</span>
                            </div>
                        </div>
                        <div v-if="currentPlan.attachment" class="flex items-center gap-2 p-2 surface-50 border-round">
                             <i class="pi pi-file text-primary"></i>
                             <a :href="currentPlan.attachment" target="_blank" class="font-bold text-primary hover:underline">Arquivo Único (Antigo)</a>
                        </div>
                    </div>
                </div>

                <div class="col-span-12 md:col-span-4 border-l-1 border-gray-200 pl-0 md:pl-4">
                    <div class="mb-3">
                        <label class="font-bold block mb-2">Feedback para o Professor</label>
                        <Textarea v-model="feedbackText" rows="8" class="w-full" placeholder="Descreva correções necessárias ou elogios..." />
                    </div>
                    
                    <div class="flex flex-col gap-2">
                        <Button label="Aprovar Plano" icon="pi pi-check" class="p-button w-full" @click="saveFeedback('APPROVED')" />
                        <Button label="Solicitar Correção" icon="pi pi-refresh" class="p-button p-button-outlined w-full" @click="saveFeedback('RETURNED')" />
                        <Button 
                            label="Deixar de Acompanhar" 
                            icon="pi pi-sign-out" 
                            class="p-button p-button-outlined w-full mt-4" 
                            @click="confirmUnsubscribe"
                            v-tooltip.top="'Remove você da lista de destinatários deste plano'"
                        />
                    </div>
                </div>
            </div>
        </Dialog>

        <Dialog v-model:visible="unsubscribeDialog" :style="{ width: '450px' }" header="Confirmar Saída" :modal="true">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle text-yellow-500 text-4xl" />
                <span class="line-height-3">
                    Tem certeza que deseja <b>deixar de acompanhar</b> este planejamento?
                    <br>
                    <small class="text-gray-500">Ele deixará de aparecer na sua lista de pendências.</small>
                </span>
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="unsubscribeDialog = false" />
                <Button label="Sim, Sair" icon="pi pi-sign-out" class="p-button-warning" @click="executeUnsubscribe" autofocus />
            </template>
        </Dialog>
    </div>
</template>

<style>
/* CSS para formatar tabelas dentro do v-html do editor */
.html-content table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1rem;
}
.html-content th, .html-content td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}
.html-content th {
    background-color: #f4f4f4;
    font-weight: bold;
}
</style>