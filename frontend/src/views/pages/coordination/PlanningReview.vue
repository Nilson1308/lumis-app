<script setup>
import { ref, onMounted } from 'vue';
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

// Filtros Ativos
const filters = ref({
    status: null,
    teacher: null,
    classroom: null,
    subject: null,
    assignment: null
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
        let query = 'lesson-plans/?';

        // --- FILTRO DE SEGURANÇA ---
        // Se quisermos ver apenas os "meus" planos para revisar, 
        // o backend deve filtrar automaticamente pelo usuário logado se ele não for superuser.
        // Mas podemos forçar um status inicial se quiser, ex: &status=SUBMITTED
        
        if (route.query.assignment) {
            query += `&assignment=${route.query.assignment}`;
        } else {
            if (filters.value.status) query += `&status=${filters.value.status}`;
            if (filters.value.teacher) query += `&assignment__teacher=${filters.value.teacher}`;
            if (filters.value.classroom) query += `&assignment__classroom=${filters.value.classroom}`;
            if (filters.value.subject) query += `&assignment__subject=${filters.value.subject}`;
        }

        const { data } = await api.get(query);
        
        // --- FILTRO CLIENT-SIDE PROVISÓRIO ---
        // Se o backend retornar tudo, filtramos aqui para mostrar apenas o que tem o ID do usuário atual em 'recipients'
        // Mas o ideal é o backend já mandar filtrado.
        // Vou assumir que o backend manda filtrado ou manda tudo e o coord vê tudo.
        
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

// --- ABRIR MODAL DE REVISÃO ---
const openReview = (plan) => {
    currentPlan.value = plan;
    feedbackText.value = plan.coordinator_feedback || ''; // Carrega feedback anterior se houver
    reviewDialog.value = true;
};

const saveFeedback = async (status) => {
    try {
        await api.patch(`lesson-plans/${currentPlan.value.id}/`, {
            status: status,
            coordinator_feedback: feedbackText.value
        });
        toast.add({ severity: 'success', summary: 'Avaliado', detail: `Status definido como ${getStatusLabel(status)}` });
        reviewDialog.value = false;
        loadPlans();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar avaliação' });
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
                    <Button icon="pi pi-filter-slash" class="p-button-outlined p-button-secondary" @click="clearFilters" v-tooltip="'Limpar'" />
                </div>
            </template>
        </Toolbar>

        <DataTable :value="plans" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
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
            
            <Column header="Ações">
                <template #body="slotProps">
                    <Button icon="pi pi-eye" label="Revisar" class="p-button-sm" @click="openReview(slotProps.data)" />
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="reviewDialog" header="Revisão do Planejamento" :style="{width: '800px'}" :modal="true" maximizable>
            <div class="grid grid-cols-12 gap-4">
                <div class="col-span-12 md:col-span-8">
                    <div class="mb-3">
                        <span class="text-sm text-gray-500 block">Tópico / Objetivo</span>
                        <h3 class="m-0 font-bold text-xl">{{ currentPlan.topic }}</h3>
                    </div>
                    
                    <div class="mb-4">
                        <span class="text-sm text-gray-500 block mb-1">Desenvolvimento</span>
                        <div class="surface-100 p-3 border-round" v-html="currentPlan.description || 'Sem descrição.'"></div>
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
                        <Button label="Aprovar Plano" icon="pi pi-check" class="p-button-success w-full" @click="saveFeedback('APPROVED')" />
                        <Button label="Solicitar Correção" icon="pi pi-refresh" class="p-button-warning w-full" @click="saveFeedback('RETURNED')" />
                    </div>
                </div>
            </div>
        </Dialog>
    </div>
</template>