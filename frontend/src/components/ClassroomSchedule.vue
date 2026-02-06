<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

// FullCalendar Imports
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import ptBrLocale from '@fullcalendar/core/locales/pt-br';

const props = defineProps({
    classroomId: { type: [String, Number], required: true }
});

const toast = useToast();
const events = ref([]);
const assignments = ref([]); 
const dialogVisible = ref(false);
const loading = ref(false);

const newSchedule = ref({
    assignment: null,
    day_of_week: null,
    start_time: null,
    end_time: null
});

const calendarOptions = ref({
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
    initialView: 'timeGridWeek',
    locale: ptBrLocale,
    headerToolbar: false,
    dayHeaderFormat: { weekday: 'long' },
    allDaySlot: false,
    slotMinTime: '07:00:00',
    slotMaxTime: '18:00:00',
    weekends: false,
    slotDuration: '00:15:00', 
    slotLabelInterval: '01:00',
    expandRows: true,
    height: 'auto',
    selectMirror: true,
    selectable: true,
    editable: false, 
    select: (info) => handleDateSelect(info),
    eventClick: (info) => handleEventClick(info),
    events: events
});

const loadSchedule = async () => {
    loading.value = true;
    try {
        const res = await api.get(`schedules/?classroom=${props.classroomId}`);
        events.value = res.data.results.map(item => ({
            id: item.id,
            title: `${item.subject_name}\n(${item.teacher_name})`,
            daysOfWeek: [item.day_of_week],
            startTime: item.start_time,
            endTime: item.end_time,
            backgroundColor: '#3B82F6',
            borderColor: '#3B82F6',
            extendedProps: { ...item }
        }));
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar grade.' });
    } finally {
        loading.value = false;
    }
};

const loadAssignments = async () => {
    try {
        const res = await api.get(`assignments/?classroom=${props.classroomId}`);
        assignments.value = res.data.results.map(a => {
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

const handleDateSelect = (selectInfo) => {
    const start = selectInfo.start;
    const end = selectInfo.end;
    
    newSchedule.value = {
        classroom: props.classroomId,
        day_of_week: start.getDay(),
        start_time: start, 
        end_time: end,     
        assignment: null
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
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Selecione a matéria.' });
        return;
    }
    if (!newSchedule.value.start_time || !newSchedule.value.end_time) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Defina início e fim.' });
        return;
    }

    // Prepara payload com formatação segura
    const payload = {
        ...newSchedule.value,
        start_time: formatTime(newSchedule.value.start_time),
        end_time: formatTime(newSchedule.value.end_time)
    };

    try {
        await api.post('schedules/', payload);
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aula agendada!' });
        dialogVisible.value = false;
        loadSchedule();
    } catch (e) {
        const msg = e.response?.data?.non_field_errors?.[0] || 'Erro ao salvar. Verifique choque de horário.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg });
    }
};

const handleEventClick = (clickInfo) => {
    if (confirm(`Remover aula de ${clickInfo.event.title}?`)) {
        api.delete(`schedules/${clickInfo.event.id}/`)
            .then(() => {
                toast.add({ severity: 'success', summary: 'Removido', detail: 'Aula removida.' });
                clickInfo.event.remove();
            });
    }
};

onMounted(() => {
    if (props.classroomId) {
        loadAssignments();
        loadSchedule();
    }
});
</script>

<template>
    <div class="card p-0 overflow-hidden surface-0">
        <FullCalendar :options="calendarOptions" class="p-3" />

        <Dialog v-model:visible="dialogVisible" header="Configurar Aula" :modal="true" :style="{ width: '450px' }" class="p-fluid">
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
                <i class="pi pi-info-circle"></i> O dia da semana é definido automaticamente.
            </small>

            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="dialogVisible = false" />
                <Button label="Salvar Aula" icon="pi pi-check" @click="saveClass" />
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
</style>