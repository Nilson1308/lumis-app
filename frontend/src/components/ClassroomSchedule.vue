<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

// FullCalendar Imports
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import ptBrLocale from '@fullcalendar/core/locales/pt-br';

const props = defineProps({
    classroomId: { type: [String, Number], required: true },
    readOnly: { type: Boolean, default: false }
});

const toast = useToast();

/** Mensagem amigável para erros da API de grade (ex.: 403 da coordenação). */
const scheduleApiError = (e, fallback) => {
    const status = e.response?.status;
    const d = e.response?.data;
    if (status === 403) {
        return (
            (typeof d?.detail === 'string' && d.detail) ||
            'Sem permissão: a grade horária só pode ser alterada pela coordenação, direção ou secretaria.'
        );
    }
    if (status === 400 && d?.non_field_errors?.[0]) return d.non_field_errors[0];
    if (typeof d?.detail === 'string' && d.detail) return d.detail;
    return fallback;
};

const events = ref([]);
const assignments = ref([]);
const dialogVisible = ref(false);
const loading = ref(false);
/** Força o FullCalendar a redesenhar quando os eventos chegam da API. */
const calendarRenderKey = ref(0);
/** null = criar; número = editar horário existente */
const editingScheduleId = ref(null);

const DAY_OPTIONS = [
    { label: 'Segunda-feira', value: 1 },
    { label: 'Terça-feira', value: 2 },
    { label: 'Quarta-feira', value: 3 },
    { label: 'Quinta-feira', value: 4 },
    { label: 'Sexta-feira', value: 5 },
    { label: 'Sábado', value: 6 },
    { label: 'Domingo', value: 0 }
];

const newSchedule = ref({
    classroom: null,
    assignment: null,
    day_of_week: null,
    start_time: null,
    end_time: null
});

const dialogHeader = computed(() =>
    editingScheduleId.value ? 'Editar horário' : 'Nova aula'
);

const parseTimeStringToDate = (t) => {
    if (!t) return null;
    if (t instanceof Date) return t;
    const parts = String(t).split(':');
    const h = Number(parts[0]) || 0;
    const m = Number(parts[1]) || 0;
    const s = Number(parts[2]) || 0;
    const d = new Date();
    d.setHours(h, m, s, 0);
    return d;
};

const resetDialog = () => {
    editingScheduleId.value = null;
    newSchedule.value = {
        classroom: props.classroomId,
        assignment: null,
        day_of_week: 1,
        start_time: null,
        end_time: null
    };
};

const refreshAll = () => {
    loadSchedule();
    loadAssignments();
};

// Detecção de mobile
const isMobile = ref(window.innerWidth < 768);

const updateMobile = () => {
    isMobile.value = window.innerWidth < 768;
};

onUnmounted(() => {
    window.removeEventListener('resize', updateMobile);
});

const calendarOptions = computed(() => ({
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
    initialView: isMobile.value ? 'listWeek' : 'timeGridWeek',
    locale: ptBrLocale,
    headerToolbar: false,
    dayHeaderFormat: isMobile.value ? { weekday: 'short' } : { weekday: 'long' },
    allDaySlot: false,
    slotMinTime: '07:00:00',
    slotMaxTime: '18:00:00',
    weekends: false,
    slotDuration: '00:15:00', 
    slotLabelInterval: isMobile.value ? '02:00' : '01:00',
    expandRows: true,
    height: isMobile.value ? 'auto' : undefined,
    aspectRatio: isMobile.value ? 1.0 : 1.8,
    selectMirror: true,
    selectable: !props.readOnly,
    editable: false, 
    select: (info) => handleDateSelect(info),
    eventClick: (info) => handleEventClick(info),
    events: events.value,
    eventDisplay: 'block',
    eventTimeFormat: {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    }
}));

const loadSchedule = async () => {
    if (!props.classroomId) return;
    loading.value = true;
    try {
        const res = await api.get(
            `schedules/?classroom=${props.classroomId}&page_size=500`
        );
        const raw = res.data?.results ?? res.data;
        const list = Array.isArray(raw) ? raw : [];
        events.value = list.map((item) => ({
            id: item.id,
            title: `${item.subject_name}\n(${item.teacher_name})`,
            daysOfWeek: [item.day_of_week],
            startTime: item.start_time,
            endTime: item.end_time,
            backgroundColor: '#3B82F6',
            borderColor: '#3B82F6',
            extendedProps: { ...item }
        }));
        calendarRenderKey.value += 1;
    } catch (e) {
        toast.add({
            severity: 'error',
            summary: 'Erro',
            detail: scheduleApiError(e, 'Erro ao carregar grade.'),
            life: 4000
        });
    } finally {
        loading.value = false;
    }
};

const loadAssignments = async () => {
    if (!props.classroomId) return;
    try {
        const res = await api.get(`assignments/?classroom=${props.classroomId}&page_size=500`);
        const raw = res.data?.results ?? res.data;
        const list = Array.isArray(raw) ? raw : [];
        assignments.value = list.map((a) => {
            const subject = a.subject?.name || a.subject_name || 'Matéria s/ nome';
            let teacher = 'Sem Prof.';
            if (a.teacher) {
                if (typeof a.teacher === 'object') {
                    teacher = a.teacher.first_name || a.teacher.username;
                    if (a.teacher.first_name && a.teacher.last_name) {
                        teacher = `${a.teacher.first_name} ${a.teacher.last_name}`;
                    }
                } else {
                    teacher = a.teacher_name || 'Prof. ID ' + a.teacher;
                }
            }
            return { id: a.id, label: `${subject} - ${teacher}` };
        });
    } catch (e) {
        console.error("Erro ao carregar atribuições", e);
    }
};

const openNewDialogManual = () => {
    if (props.readOnly) return;
    resetDialog();
    dialogVisible.value = true;
};

const handleDateSelect = (selectInfo) => {
    if (props.readOnly) return;

    const start = selectInfo.start;
    const end = selectInfo.end;
    editingScheduleId.value = null;
    newSchedule.value = {
        classroom: props.classroomId,
        day_of_week: start.getDay(),
        start_time: start,
        end_time: end,
        assignment: null
    };
    dialogVisible.value = true;
    try {
        selectInfo.view.calendar.unselect();
    } catch {
        /* ignore */
    }
};

const openEditDialog = (raw) => {
    editingScheduleId.value = raw.id;
    newSchedule.value = {
        classroom: props.classroomId,
        assignment: raw.assignment,
        day_of_week: raw.day_of_week,
        start_time: parseTimeStringToDate(raw.start_time),
        end_time: parseTimeStringToDate(raw.end_time)
    };
    dialogVisible.value = true;
};

// --- CORREÇÃO DA FORMATAÇÃO DE HORA ---
const formatTime = (date) => {
    if (!date) return null;
    if (typeof date === 'string') return date; // Já é string "HH:MM:SS"
    
    // Extrai manualmente Hora e Minuto e força "00" nos segundos
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}:00`;
};

const saveClass = async () => {
    if (!newSchedule.value.assignment) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Selecione a matéria.', life: 3000 });
        return;
    }
    if (!newSchedule.value.start_time || !newSchedule.value.end_time) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Defina início e fim.', life: 3000 });
        return;
    }

    const payload = {
        classroom: Number(props.classroomId),
        assignment: newSchedule.value.assignment,
        day_of_week: newSchedule.value.day_of_week,
        start_time: formatTime(newSchedule.value.start_time),
        end_time: formatTime(newSchedule.value.end_time)
    };

    try {
        if (editingScheduleId.value) {
            await api.patch(`schedules/${editingScheduleId.value}/`, payload);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Horário atualizado.', life: 3000 });
        } else {
            await api.post('schedules/', payload);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aula agendada!', life: 3000 });
        }
        dialogVisible.value = false;
        resetDialog();
        loadSchedule();
    } catch (e) {
        toast.add({
            severity: 'error',
            summary: 'Erro',
            detail: scheduleApiError(e, 'Erro ao salvar. Verifique choque de horário.'),
            life: 4000
        });
    }
};

const handleEventClick = (clickInfo) => {
    if (props.readOnly) return;
    const raw = clickInfo.event.extendedProps;
    openEditDialog(raw);
};

const deleteCurrentSchedule = async () => {
    if (!editingScheduleId.value) return;
    if (!confirm('Remover este horário da grade?')) return;
    try {
        await api.delete(`schedules/${editingScheduleId.value}/`);
        toast.add({ severity: 'success', summary: 'Removido', detail: 'Horário removido.', life: 3000 });
        dialogVisible.value = false;
        resetDialog();
        loadSchedule();
    } catch (e) {
        toast.add({
            severity: 'error',
            summary: 'Erro',
            detail: scheduleApiError(e, 'Não foi possível remover o horário.'),
            life: 4000
        });
    }
};

watch(
    () => props.classroomId,
    (id) => {
        if (id) {
            loadAssignments();
            loadSchedule();
        } else {
            events.value = [];
            assignments.value = [];
        }
    },
    { immediate: true }
);

onMounted(() => {
    window.addEventListener('resize', updateMobile);
    updateMobile();
});
</script>

<template>
    <div class="card p-0 overflow-hidden surface-0">
        <div v-if="readOnly" class="p-3 bg-blue-50 border-round-top">
            <div class="flex align-items-center gap-2 text-blue-700">
                <i class="pi pi-info-circle"></i>
                <span class="text-sm font-medium"
                    >Modo somente leitura — a edição da grade é feita pela coordenação, direção ou secretaria.</span>
            </div>
        </div>
        <div
            v-if="!readOnly"
            class="flex flex-wrap align-items-center justify-content-between gap-2 px-3 pt-3 border-bottom-1 surface-border"
        >
            <span class="text-600 text-sm line-height-3" style="max-width: 42rem">
                Gestão: use «Nova aula» ou arraste no calendário para criar; clique num bloco para editar ou excluir.
            </span>
            <div class="flex flex-wrap gap-2">
                <Button
                    label="Atualizar"
                    icon="pi pi-refresh"
                    class="p-button-outlined p-button-sm"
                    :loading="loading"
                    @click="refreshAll"
                />
                <Button label="Nova aula" icon="pi pi-plus" class="p-button-sm" @click="openNewDialogManual" />
            </div>
        </div>
        <FullCalendar
            :key="`sched-${props.classroomId}-${calendarRenderKey}`"
            :options="calendarOptions"
            class="p-3"
        />

        <Dialog
            v-model:visible="dialogVisible"
            :header="dialogHeader"
            :modal="true"
            :style="{ width: isMobile ? '95vw' : '480px', maxWidth: '95vw' }"
            class="p-fluid"
            @hide="resetDialog"
        >
            <div class="field mb-3">
                <label class="font-bold">Dia da semana</label>
                <Dropdown
                    v-model="newSchedule.day_of_week"
                    :options="DAY_OPTIONS"
                    optionLabel="label"
                    optionValue="value"
                    placeholder="Dia"
                    class="w-full"
                />
            </div>
            <div class="field mb-3">
                <label class="font-bold">Matéria / Professor</label>
                <Dropdown 
                    v-model="newSchedule.assignment" 
                    :options="assignments" 
                    optionLabel="label" 
                    optionValue="id" 
                    placeholder="Selecione..." 
                    class="w-full" 
                    autofocus
                    filter
                />
            </div>

            <div class="grid grid-cols-12 gap-3">
                <div class="col-span-6">
                    <label class="font-bold block mb-2">Início</label>
                    <DatePicker 
                        v-model="newSchedule.start_time" 
                        timeOnly 
                        hourFormat="24" 
                        :stepMinute="5"
                        placeholder="00:00"
                        showIcon
                        fluid
                        iconDisplay="input"
                    />
                </div>
                <div class="col-span-6">
                    <label class="font-bold block mb-2">Fim</label>
                    <DatePicker 
                        v-model="newSchedule.end_time" 
                        timeOnly 
                        hourFormat="24" 
                        :stepMinute="5"
                        placeholder="00:00"
                        showIcon
                        fluid
                        iconDisplay="input"
                    />
                </div>
            </div>
            
            <small class="block mt-2 text-500">
                <i class="pi pi-info-circle"></i>
                Ao criar pelo calendário, o dia é preenchido pelo slot; pode alterar antes de guardar.
            </small>

            <template #footer>
                <div class="flex flex-wrap justify-content-between gap-2 w-full">
                    <Button
                        v-if="editingScheduleId"
                        label="Excluir"
                        icon="pi pi-trash"
                        severity="danger"
                        class="p-button-outlined"
                        @click="deleteCurrentSchedule"
                    />
                    <span v-else></span>
                    <div class="flex gap-2">
                        <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="dialogVisible = false" />
                        <Button :label="editingScheduleId ? 'Guardar' : 'Agendar'" icon="pi pi-check" @click="saveClass" />
                    </div>
                </div>
            </template>
        </Dialog>
    </div>
</template>

<style>
.fc .fc-timegrid-slot {
    height: 2.5em !important; 
}

.fc-event-main {
    padding: 2px 4px;
    font-size: 0.85rem;
    font-weight: 500;
}

/* Mobile optimizations */
@media (max-width: 768px) {
    .fc {
        font-size: 0.75rem !important;
    }
    
    .fc .fc-timegrid-slot {
        height: 2em !important;
    }
    
    .fc-event-main {
        padding: 1px 2px;
        font-size: 0.7rem;
        line-height: 1.2;
    }
    
    .fc .fc-list-event {
        font-size: 0.85rem;
    }
    
    .fc .fc-list-event-time {
        font-size: 0.75rem;
    }
    
    .fc-toolbar-title {
        font-size: 1rem !important;
    }
}

/* Tablet optimizations */
@media (min-width: 769px) and (max-width: 1024px) {
    .fc {
        font-size: 0.85rem !important;
    }
}
</style>