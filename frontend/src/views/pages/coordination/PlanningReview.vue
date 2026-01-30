<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const plans = ref([]);
const loading = ref(true);
const feedbackDialog = ref(false);
const currentPlan = ref({});
const feedbackText = ref('');

// Listas para Filtros
const teachers = ref([]);
const classrooms = ref([]);
const subjects = ref([]);

// Filtros Ativos
const filters = ref({
    status: null,
    teacher: null,
    classroom: null,
    subject: null
});

const statusOptions = ref([
    {label: 'Rascunho', value: 'DRAFT'},
    {label: 'Enviado', value: 'SUBMITTED'},
    {label: 'Aprovado', value: 'APPROVED'},
    {label: 'Correção', value: 'RETURNED'}
]);

onMounted(() => {
    loadFilterOptions(); // Carrega listas para os dropdowns
    loadPlans();         // Carrega a tabela
});

// 1. Carrega opções dos dropdowns
const loadFilterOptions = async () => {
    try {
        // Carrega Professores (User com permissão ou TeacherAssignment distinto)
        // Se não tiver endpoint específico de teachers, pegamos assignments e extraímos uniques, 
        // mas o ideal é ter endpoints auxiliares. Vamos tentar endpoints padrão:
        
        // Professores (Tenta pegar usuários do grupo Professor ou lista simplificada)
        // Nota: Se não tiver endpoint 'teachers', precisará ajustar. 
        // Vou assumir que conseguimos extrair dos assignments ou usar endpoint de users.
        // Solução Rápida: Pegar assignments e filtrar únicos no front para popular os selects
        const { data: assignments } = await api.get('assignments/?page_size=1000');
        
        // Extrair Professores Únicos
        const uniqueTeachers = new Map();
        assignments.results.forEach(a => uniqueTeachers.set(a.teacher, a.teacher_name));
        teachers.value = Array.from(uniqueTeachers, ([id, name]) => ({ id, name }));

        // Extrair Turmas Únicas
        const uniqueClasses = new Map();
        assignments.results.forEach(a => uniqueClasses.set(a.classroom, a.classroom_name));
        classrooms.value = Array.from(uniqueClasses, ([id, name]) => ({ id, name }));

        // Extrair Matérias Únicas
        const uniqueSubjects = new Map();
        assignments.results.forEach(a => uniqueSubjects.set(a.subject, a.subject_name));
        subjects.value = Array.from(uniqueSubjects, ([id, name]) => ({ id, name }));

    } catch (e) {
        console.error("Erro ao carregar filtros", e);
    }
};

// 2. Carrega Planos com Filtros Aplicados
const loadPlans = async () => {
    loading.value = true;
    try {
        let query = 'lesson-plans/?';
        
        // Mapeia filtros do front para os filtros do Django (filterset_fields)
        if (filters.value.status) query += `&status=${filters.value.status}`;
        if (filters.value.teacher) query += `&assignment__teacher=${filters.value.teacher}`;
        if (filters.value.classroom) query += `&assignment__classroom=${filters.value.classroom}`;
        if (filters.value.subject) query += `&assignment__subject=${filters.value.subject}`;
        
        const { data } = await api.get(query);
        plans.value = data.results || data;
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados' });
    } finally {
        loading.value = false;
    }
};

const clearFilters = () => {
    filters.value = { status: null, teacher: null, classroom: null, subject: null };
    loadPlans();
};

const openFeedback = (plan) => {
    currentPlan.value = plan;
    feedbackText.value = plan.coordinator_feedback || '';
    feedbackDialog.value = true;
};

const saveFeedback = async (status) => {
    try {
        await api.patch(`lesson-plans/${currentPlan.value.id}/`, {
            status: status,
            coordinator_feedback: feedbackText.value
        });
        toast.add({ severity: 'success', summary: 'Sucesso', detail: `Status alterado para ${getStatusLabel(status)}` });
        feedbackDialog.value = false;
        loadPlans();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar feedback' });
    }
};

// Helpers Visuais
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
                    <Button icon="pi pi-filter-slash" class="p-button-outlined p-button-secondary" @click="clearFilters" v-tooltip="'Limpar Filtros'" />
                </div>
            </template>
        </Toolbar>

        <DataTable :value="plans" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
            <template #empty>Nenhum planejamento encontrado com esses filtros.</template>
            
            <Column field="start_date" header="Semana" sortable>
                <template #body="slotProps">
                    {{ new Date(slotProps.data.start_date + 'T00:00:00').toLocaleDateString('pt-BR') }}
                </template>
            </Column>
            <Column field="teacher_name" header="Professor" sortable></Column>
            <Column field="subject_name" header="Disciplina" sortable></Column>
            <Column field="classroom_name" header="Turma" sortable></Column>
            
            <Column header="Anexo">
                <template #body="slotProps">
                    <a v-if="slotProps.data.attachment" :href="slotProps.data.attachment" target="_blank" class="text-primary font-bold hover:underline">
                        <i class="pi pi-download mr-1"></i> Baixar
                    </a>
                    <span v-else class="text-gray-400 text-sm">--</span>
                </template>
            </Column>
            
            <Column field="status" header="Status">
                <template #body="slotProps">
                    <Tag :value="getStatusLabel(slotProps.data.status)" :severity="getSeverity(slotProps.data.status)" />
                </template>
            </Column>
            
            <Column header="Ações">
                <template #body="slotProps">
                    <Button icon="pi pi-comments" label="Avaliar" class="p-button-sm p-button-outlined" @click="openFeedback(slotProps.data)" />
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="feedbackDialog" header="Avaliação da Coordenação" :style="{width: '500px'}" :modal="true">
            <div class="field">
                <label class="font-bold block mb-2">Feedback / Orientação</label>
                <Textarea v-model="feedbackText" rows="6" class="w-full" placeholder="Escreva aqui o feedback para o professor..." />
            </div>
            <template #footer>
                <div class="flex justify-between w-full">
                    <Button label="Solicitar Correção" icon="pi pi-times" severity="warning" @click="saveFeedback('RETURNED')" />
                    <Button label="Aprovar" icon="pi pi-check" severity="success" @click="saveFeedback('APPROVED')" />
                </div>
            </template>
        </Dialog>
    </div>
</template>