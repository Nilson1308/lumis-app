<script setup>
import { ref, onMounted, computed, watch, onUnmounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';
import api from '@/service/api';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import listPlugin from '@fullcalendar/list';
import ptBrLocale from '@fullcalendar/core/locales/pt-br';
import Calendar from 'primevue/calendar';

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

// Verifica se o usuário pode EDITAR um evento (para cor diferente quando só leitura)
function canEditEvent(eventProps) {
    if (!eventProps) return false;
    const user = authStore.user;
    if (!user) return false;
    if (authStore.isAdmin || authStore.isCoordinator) return true;
    if (authStore.isSecretary) {
        if (['EXAM', 'ASSIGNMENT'].includes(eventProps.event_type)) {
            return eventProps.created_by === user.id;
        }
        return true;
    }
    if (authStore.isTeacher) return eventProps.created_by === user.id;
    return false; // Responsáveis: só leitura
}

// Detecção de mobile
const isMobile = ref(window.innerWidth < 768);

const updateMobile = () => {
    isMobile.value = window.innerWidth < 768;
};

onMounted(() => {
    window.addEventListener('resize', updateMobile);
    updateMobile();
});

onUnmounted(() => {
    window.removeEventListener('resize', updateMobile);
});

// --- FULLCALENDAR OPTIONS ---
const calendarOptions = computed(() => ({
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin],
    initialView: isMobile.value ? 'listWeek' : 'timeGridWeek',
    locale: ptBrLocale,
    headerToolbar: isMobile.value ? {
        left: 'prev,next',
        center: 'title',
        right: ''
    } : {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,listMonth'
    },
    height: isMobile.value ? 'auto' : undefined,
    aspectRatio: isMobile.value ? 1.2 : 1.8,
    editable: false,
    selectable: true,
    dayMaxEvents: true,
    select: handleDateSelect,
    eventClick: handleEventClick,
    events: fetchEventsFromApi,
    eventDisplay: 'block',
    eventTimeFormat: {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    }
}));

// --- API ---
async function fetchEventsFromApi(info, successCallback, failureCallback) {
    try {
        const response = await api.get('calendar/', {
            params: { start: info.startStr, end: info.endStr }
        });
        
        const mappedEvents = response.data.map(e => {
            // Cores por tipo
            let color = '#3788d8';
            if (e.event_type === 'HOLIDAY') color = '#ef4444';
            if (e.event_type === 'EXAM') color = '#f59e0b';
            if (e.event_type === 'SCHOOL_DAY') color = '#22c55e';

            // Quando o usuário só pode LER (regra de negócio), usa cor mais suave
            const readOnly = !canEditEvent(e);
            if (readOnly) {
                color = '#9ca3af'; // cinza para eventos somente leitura
            }

            const isHoliday = e.event_type === 'HOLIDAY';
            const startStr = e.start_time || '';
            const endStr = e.end_time || '';

            return {
                id: e.id,
                title: e.title,
                start: isHoliday ? startStr.split('T')[0] : startStr,
                end: isHoliday ? (endStr ? endStr.split('T')[0] : startStr.split('T')[0]) : endStr,
                allDay: isHoliday, // Feriados = dia todo
                color,
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

// Indica se o evento é feriado (para usar formulário só data, sem horário)
const isHolidayEvent = computed(() => selectedEvent.value.event_type === 'HOLIDAY');

// Data para feriado (dia todo) - computed para dois vias
const holidayDate = computed({
    get() {
        const s = selectedEvent.value?.start_time;
        if (!s) return null;
        return s instanceof Date ? s : new Date(s);
    },
    set(val) {
        if (!val || !selectedEvent.value) return;
        const d = val instanceof Date ? val : new Date(val);
        const dateStr = d.toISOString().split('T')[0];
        selectedEvent.value.start_time = `${dateStr}T00:00:00`;
        selectedEvent.value.end_time = `${dateStr}T23:59:59`;
    }
});

// Datas com horário para Início e Fim - Calendar precisa de Date para formatar dd/mm/yyyy - HH:mm
const startTimeDate = computed({
    get() {
        const s = selectedEvent.value?.start_time;
        if (!s) return null;
        return s instanceof Date ? s : new Date(s);
    },
    set(val) {
        if (!selectedEvent.value) return;
        selectedEvent.value.start_time = val ? (val instanceof Date ? val.toISOString() : new Date(val).toISOString()) : null;
    }
});
const endTimeDate = computed({
    get() {
        const s = selectedEvent.value?.end_time;
        if (!s) return null;
        return s instanceof Date ? s : new Date(s);
    },
    set(val) {
        if (!selectedEvent.value) return;
        selectedEvent.value.end_time = val ? (val instanceof Date ? val.toISOString() : new Date(val).toISOString()) : null;
    }
});

// --- HANDLERS ---
function openNewEvent() {
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    selectedEvent.value = {
        title: '',
        start_time: `${today}T08:00:00`,
        end_time: `${today}T18:00:00`,
        event_type: 'EVENT',
        target_audience: 'ALL'
    };
    eventDialog.value = true;
}

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
    let startTime = props.start_time || '';
    let endTime = props.end_time || '';
    // Feriados podem vir sem hora; garante formato
    if (props.event_type === 'HOLIDAY') {
        if (startTime && startTime.length === 10) startTime += 'T00:00:00';
        if (endTime && endTime.length === 10) endTime += 'T23:59:59';
    }
    selectedEvent.value = {
        id: clickInfo.event.id,
        title: clickInfo.event.title,
        start_time: startTime,
        end_time: endTime,
        event_type: props.event_type,
        target_audience: props.target_audience,
        classroom: props.classroom,
        subject: props.subject,
        description: props.description,
        created_by: props.created_by
    };
    eventDialog.value = true;
}

// Quando mudar para HOLIDAY, ajusta para dia todo
watch(() => selectedEvent.value.event_type, (newType) => {
    if (newType === 'HOLIDAY' && selectedEvent.value.start_time) {
        const datePart = selectedEvent.value.start_time.split('T')[0] || selectedEvent.value.start_time.substring(0, 10);
        selectedEvent.value.start_time = `${datePart}T00:00:00`;
        selectedEvent.value.end_time = `${datePart}T23:59:59`;
    }
}, { flush: 'post' });

// Helpers para converter entre Date e string ISO
function toDate(val) {
    if (!val) return null;
    if (val instanceof Date) return val;
    if (typeof val === 'string') return new Date(val);
    return null;
}
function toISOString(val) {
    const d = toDate(val);
    return d ? d.toISOString() : '';
}

const saveEvent = async () => {
    loading.value = true;
    try {
        const payload = { ...selectedEvent.value };
        const start = toDate(payload.start_time);
        const end = toDate(payload.end_time);

        if (payload.event_type === 'HOLIDAY') {
            // Feriado = dia todo: início 00:00, fim 23:59
            const dateStr = start ? start.toISOString().split('T')[0] : payload.start_time?.split('T')[0];
            payload.start_time = `${dateStr}T00:00:00`;
            payload.end_time = `${dateStr}T23:59:59`;
        } else {
            payload.start_time = toISOString(start) || payload.start_time;
            payload.end_time = toISOString(end) || payload.end_time;
            if (payload.start_time && payload.start_time.length === 10) payload.start_time += 'T08:00:00';
            if (payload.end_time && payload.end_time.length === 10) payload.end_time += 'T18:00:00';
        }

        if (payload.id) {
            await api.put(`calendar/${payload.id}/`, payload);
            toast.add({ severity: 'success', summary: 'Atualizado', detail: 'Evento atualizado!', life: 3000 });
        } else {
            await api.post('calendar/', payload);
            toast.add({ severity: 'success', summary: 'Criado', detail: 'Evento criado!', life: 3000 });
        }
        eventDialog.value = false;
        window.location.reload();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Você não tem permissão para alterar este evento.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

const deleteEvent = async () => {
    try {
        await api.delete(`calendar/${selectedEvent.value.id}/`);
        toast.add({ severity: 'success', summary: 'Removido', detail: 'Evento excluído.', life: 3000 });
        eventDialog.value = false;
        deleteDialog.value = false;
        window.location.reload();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir.', life: 3000 });
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
        <div class="flex justify-between items-center mb-4">
            <h2 class="text-2xl font-bold text-primary m-0">Calendário Acadêmico</h2>
            <Button
                v-if="canCreate"
                label="Novo Evento"
                icon="pi pi-plus"
                class="p-button-primary"
                @click="openNewEvent"
            />
        </div>

        <FullCalendar :options="calendarOptions" />

        <Dialog 
            v-model:visible="eventDialog" 
            :header="selectedEvent.id ? (isEditable ? 'Editar Evento' : 'Detalhes do Evento') : 'Novo Evento'" 
            :modal="true" 
            class="p-fluid" 
            :style="{ width: isMobile ? '95vw' : '700px', maxWidth: '700px' }"
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
                <!-- Feriado = dia todo (só data) -->
                <div v-if="isHolidayEvent" class="grid grid-cols-12 gap-4 mb-2">
                    <div class="col-span-12 xl:col-span-12">
                        <label class="block font-bold mb-1">Data (dia todo)</label>
                        <Calendar v-model="holidayDate" dateFormat="dd/mm/yyyy" locale="pt-BR" showIcon fluid />
                    </div>
                </div>
                <!-- Outros tipos = data + horário -->
                <div v-else class="grid grid-cols-12 gap-4 mb-2">
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-1">Início</label>
                        <Calendar
                            v-model="startTimeDate"
                            showTime
                            hourFormat="24"
                            dateFormat="dd/mm/yyyy - HH:mm"
                            timeFormat="24"
                            locale="pt-BR"
                            showIcon
                            fluid
                        />
                    </div>
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-1">Fim</label>
                        <Calendar
                            v-model="endTimeDate"
                            showTime
                            hourFormat="24"
                            dateFormat="dd/mm/yyyy - HH:mm"
                            timeFormat="24"
                            locale="pt-BR"
                            showIcon
                            fluid
                        />
                    </div>
                </div>
                <div v-if="['EXAM', 'ASSIGNMENT'].includes(selectedEvent.event_type) || selectedEvent.target_audience === 'CLASSROOM'" class="grid grid-cols-12 gap-4 mb-2">
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