<script setup>
import { ref, onMounted, computed } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';
import api from '@/service/api';
// ... imports do FullCalendar mantidos ...
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import listPlugin from '@fullcalendar/list';
import ptBrLocale from '@fullcalendar/core/locales/pt-br';

const toast = useToast();
const authStore = useAuthStore();

// Estados
const events = ref([]);
const loading = ref(false);
const eventDialog = ref(false);
const deleteDialog = ref(false);
const selectedEvent = ref({});
const classrooms = ref([]);
const subjects = ref([]);

// --- PERMISSÕES VISUAIS ---
const canCreate = computed(() => {
    return authStore.isAdmin || authStore.isCoordinator || authStore.isSecretary || authStore.isTeacher;
});

const isEditable = computed(() => {
    // 1. Se for novo e tenho permissão de criar -> True
    if (!selectedEvent.value.id) return canCreate.value;

    // 2. Admin e Coordenador -> True sempre
    if (authStore.isAdmin || authStore.isCoordinator) return true;

    // 3. Secretaria -> Depende do tipo
    if (authStore.isSecretary) {
        // Se for Prova ou Trabalho...
        if (['EXAM', 'ASSIGNMENT'].includes(selectedEvent.value.event_type)) {
             // ...só edita se foi ela quem criou (comparação simplificada, idealmente checaria ID)
             // Se 'created_by' vier nulo (legado) ou for diferente, assume false para segurança visual
             return selectedEvent.value.created_by === authStore.user?.id;
        }
        return true; // Pode editar Feriados, Eventos, etc.
    }

    // 4. Professor -> Só se ele criou
    if (authStore.isTeacher) {
        return selectedEvent.value.created_by === authStore.user?.id;
    }

    return false;
});

// --- FULLCALENDAR OPTIONS ---
const calendarOptions = ref({
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin],
    initialView: 'timeGridWeek',
    locale: ptBrLocale,
    headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,listMonth'
    },
    editable: false, // Desliguei o drag&drop global para evitar confusão de permissão
    selectable: true,
    dayMaxEvents: true,
    select: handleDateSelect,
    eventClick: handleEventClick,
    events: fetchEventsFromApi
});

// --- API ---
async function fetchEventsFromApi(info, successCallback, failureCallback) {
    try {
        const response = await api.get('calendar/', {
            params: { start: info.startStr, end: info.endStr }
        });
        
        const mappedEvents = response.data.map(e => {
            let color = '#3788d8';
            if (e.event_type === 'HOLIDAY') color = '#ef4444';
            if (e.event_type === 'EXAM') color = '#f59e0b';
            if (e.event_type === 'SCHOOL_DAY') color = '#22c55e';
            
            // Destaque visual para o Professor: Se é meu, borda mais grossa ou cor diferente?
            // Por enquanto mantemos padrão.
            
            return {
                id: e.id,
                title: e.title,
                start: e.start_time,
                end: e.end_time,
                color: color,
                extendedProps: { ...e } 
            };
        });
        successCallback(mappedEvents);
    } catch (error) {
        failureCallback(error);
    }
}

// Carregar dependências (somente para quem edita)
const loadDependencies = async () => {
    // Carrega sempre para garantir que os nomes (labels) apareçam na visualização
    try {
        const [resClasses, resSubjects] = await Promise.all([
            api.get('classrooms/?page_size=100'),
            api.get('subjects/?page_size=100')
        ]);
        classrooms.value = resClasses.data.results;
        subjects.value = resSubjects.data.results;
    } catch (e) {
        console.error("Erro ao carregar turmas/matérias", e);
    }
};

// --- HANDLERS ---
function handleDateSelect(selectInfo) {
    if (!canCreate.value) return; // Pais clicam na data e nada acontece

    selectedEvent.value = {
        title: '',
        start_time: selectInfo.startStr,
        end_time: selectInfo.endStr,
        event_type: 'EVENT',
        target_audience: 'ALL'
    };
    eventDialog.value = true;
}

function handleEventClick(clickInfo) {
    const props = clickInfo.event.extendedProps;
    selectedEvent.value = {
        id: clickInfo.event.id,
        title: clickInfo.event.title,
        start_time: props.start_time,
        end_time: props.end_time,
        event_type: props.event_type,
        target_audience: props.target_audience,
        classroom: props.classroom,
        subject: props.subject,
        description: props.description,
        created_by: props.created_by // <--- Importante recuperar aqui
    };
    eventDialog.value = true;
}

const saveEvent = async () => {
    loading.value = true;
    try {
        const payload = { ...selectedEvent.value };
        if (payload.start_time.length === 10) payload.start_time += 'T08:00:00';
        if (payload.end_time && payload.end_time.length === 10) payload.end_time += 'T18:00:00';

        if (payload.id) {
            await api.put(`calendar/${payload.id}/`, payload);
            toast.add({ severity: 'success', summary: 'Atualizado', detail: 'Evento atualizado!' });
        } else {
            await api.post('calendar/', payload);
            toast.add({ severity: 'success', summary: 'Criado', detail: 'Evento criado!' });
        }
        eventDialog.value = false;
        window.location.reload();
    } catch (e) {
        // Se o backend bloquear (403), mostramos aqui
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Você não tem permissão para alterar este evento.' });
    } finally {
        loading.value = false;
    }
};

const deleteEvent = async () => {
    try {
        await api.delete(`calendar/${selectedEvent.value.id}/`);
        toast.add({ severity: 'success', summary: 'Removido', detail: 'Evento excluído.' });
        eventDialog.value = false;
        deleteDialog.value = false;
        window.location.reload();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir.' });
    }
};

// Helpers de Visualização
const getLabel = (list, val) => list.find(i => i.value === val || i.id === val)?.label || list.find(i => i.id === val)?.name || val;

const eventTypes = [
    { label: 'Feriado / Recesso', value: 'HOLIDAY' },
    { label: 'Dia Letivo Especial', value: 'SCHOOL_DAY' },
    { label: 'Prova / Avaliação', value: 'EXAM' },
    { label: 'Entrega de Trabalho', value: 'ASSIGNMENT' },
    { label: 'Evento / Festa', value: 'EVENT' },
    { label: 'Reunião', value: 'MEETING' }
];
const targetAudiences = [
    { label: 'Toda a Escola', value: 'ALL' },
    { label: 'Apenas Professores', value: 'TEACHERS' },
    { label: 'Turma Específica', value: 'CLASSROOM' }
];

onMounted(() => loadDependencies());
</script>

<template>
    <div class="card">
        <Toast />
        <h2 class="text-2xl font-bold mb-4 text-primary">Calendário Acadêmico</h2>

        <FullCalendar :options="calendarOptions" />

        <Dialog 
            v-model:visible="eventDialog" 
            :header="selectedEvent.id ? (isEditable ? 'Editar Evento' : 'Detalhes do Evento') : 'Novo Evento'" 
            :modal="true" 
            class="p-fluid" 
            :style="{ width: '700px' }"
        >
            
            <div v-if="isEditable">
                <div class="mb-2">
                    <label class="block font-bold mb-1">Título</label>
                    <InputText v-model="selectedEvent.title" required autofocus fluid />
                </div>
                <div class="grid grid-cols-12 gap-4 mb-2">
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-1">Tipo</label>
                        <Dropdown v-model="selectedEvent.event_type" :options="eventTypes" optionLabel="label" optionValue="value" fluid />
                    </div>
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-1">Público</label>
                        <Dropdown v-model="selectedEvent.target_audience" :options="targetAudiences" optionLabel="label" optionValue="value" fluid />
                    </div>
                </div>
                <div v-if="['EXAM', 'ASSIGNMENT', 'CLASSROOM'].includes(selectedEvent.event_type) || selectedEvent.target_audience === 'CLASSROOM'" class="grid grid-cols-12 gap-4 mb-2">
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-1">Turma</label>
                        <Dropdown v-model="selectedEvent.classroom" :options="classrooms" optionLabel="name" optionValue="id" filter fluid />
                    </div>
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-1">Matéria</label>
                        <Dropdown v-model="selectedEvent.subject" :options="subjects" optionLabel="name" optionValue="id" filter fluid />
                    </div>
                </div>
                <div class="mb-2">
                    <label class="block font-bold mb-1">Descrição</label>
                    <Textarea v-model="selectedEvent.description" rows="3" autoResize fluid />
                </div>
            </div>

            <div v-else class="text-lg">
                <div class="mb-3">
                    <span class="block text-500 text-sm">O Que</span>
                    <span class="font-bold text-xl">{{ selectedEvent.title }}</span>
                </div>
                
                <div class="flex gap-4 mb-3">
                    <div>
                        <span class="block text-500 text-sm">Tipo</span>
                        <Tag :value="getLabel(eventTypes, selectedEvent.event_type)" severity="info" />
                    </div>
                    <div>
                        <span class="block text-500 text-sm">Data</span>
                        <span class="font-medium">{{ new Date(selectedEvent.start_time).toLocaleDateString() }}</span>
                    </div>
                </div>

                <div v-if="selectedEvent.description" class="mb-3 bg-surface-50 p-3 border-round">
                    <span class="block text-500 text-sm mb-1">Detalhes</span>
                    <p class="m-0 line-height-3">{{ selectedEvent.description }}</p>
                </div>

                <div v-if="selectedEvent.classroom" class="mb-3">
                    <span class="block text-500 text-sm">Turma / Matéria</span>
                    <span class="font-medium">
                        {{ getLabel(classrooms, selectedEvent.classroom) }}
                        <span v-if="selectedEvent.subject"> - {{ getLabel(subjects, selectedEvent.subject) }}</span>
                    </span>
                </div>
            </div>

            <template #footer>
                <div class="flex justify-between w-full">
                    <Button v-if="isEditable && selectedEvent.id" label="Excluir" icon="pi pi-trash" class="p-button-danger p-button-text" @click="deleteDialog = true" />
                    <div v-else></div>
                    
                    <div class="flex gap-2">
                        <Button :label="isEditable ? 'Cancelar' : 'Fechar'" icon="pi pi-times" class="p-button-text" @click="eventDialog = false" />
                        <Button v-if="isEditable" label="Salvar" icon="pi pi-check" @click="saveEvent" :loading="loading" />
                    </div>
                </div>
            </template>
        </Dialog>

        <Dialog v-model:visible="deleteDialog" header="Confirmar" :modal="true" :style="{ width: '350px' }">
             <div class="flex items-center justify-center">
                <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                <span>Excluir este evento?</span>
            </div>
            <template #footer>
                <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                <Button label="Sim" icon="pi pi-check" class="p-button-text p-button-danger" @click="deleteEvent" />
            </template>
        </Dialog>

    </div>
</template>