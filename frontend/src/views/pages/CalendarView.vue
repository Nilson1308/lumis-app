<script setup>
import { ref, onMounted, computed, watch, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
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

const VIEW_MODE_STORAGE_KEY = 'lumis.calendarViewMode';

const toast = useToast();
const authStore = useAuthStore();
const route = useRoute();

const fullCalendarRef = ref(null);

/**
 * UI só leitura / tabela mensal: rota do portal família OU responsável sem perfil staff.
 * (API continua a filtrar eventos no servidor.)
 */
const usesFamilySchoolCalendarUi = computed(() => {
    if (route.name === 'parent-calendar') {
        return true;
    }
    if (!authStore.user) return false;
    const guardian = authStore.isGuardian;
    const staff =
        authStore.isTeacher ||
        authStore.isCoordinator ||
        authStore.isSecretary ||
        authStore.isAdmin;
    return guardian && !staff;
});

function readStoredViewMode() {
    try {
        return localStorage.getItem(VIEW_MODE_STORAGE_KEY) === 'managerial' ? 'managerial' : 'visual';
    } catch {
        return 'visual';
    }
}

/** Visual: tabela por mês. Gerencial: FullCalendar (só fora do portal família). */
const viewMode = ref(readStoredViewMode());
/** Mês exibido na tabela (visual); qualquer dia do mês serve como âncora. */
const tableMonth = ref(new Date());
const tableEventsRaw = ref([]);
const tableLoading = ref(false);
const tableSearch = ref('');
/** Tipos selecionados (vazio = todos os tipos). */
const tableTypeFilter = ref([]);

// Estados
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

function eventTypeColor(eventType) {
    switch (eventType) {
        case 'HOLIDAY':
            return '#ef4444';
        case 'EXAM':
            return '#f59e0b';
        case 'SCHOOL_DAY':
            return '#22c55e';
        case 'MEETING':
            return '#8b5cf6';
        case 'ASSIGNMENT':
            return '#6366f1';
        default:
            return '#3788d8';
    }
}

function eventTypeSeverity(eventType) {
    switch (eventType) {
        case 'HOLIDAY':
            return 'danger';
        case 'EXAM':
            return 'warn';
        case 'SCHOOL_DAY':
            return 'success';
        case 'MEETING':
            return 'secondary';
        case 'ASSIGNMENT':
            return 'info';
        default:
            return 'info';
    }
}

// Detecção de mobile
const isMobile = ref(window.innerWidth < 768);

const updateMobile = () => {
    isMobile.value = window.innerWidth < 768;
};

onUnmounted(() => {
    window.removeEventListener('resize', updateMobile);
});

// --- FULLCALENDAR (modo gerencial: semana/lista conforme ecrã) ---
const calendarOptions = computed(() => ({
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin],
    initialView: isMobile.value ? 'listWeek' : 'timeGridWeek',
    locale: ptBrLocale,
    headerToolbar: isMobile.value
        ? {
              left: 'prev,next',
              center: 'title',
              right: ''
          }
        : {
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,timeGridWeek,listMonth'
          },
    height: isMobile.value ? 'auto' : 'min(78vh, 900px)',
    aspectRatio: isMobile.value ? 1.2 : 1.55,
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

        const mappedEvents = response.data.map((e) => {
            const color = eventTypeColor(e.event_type);

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
        await refreshCalendars();
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
        await refreshCalendars();
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

function monthRangeIsoLocal(anchor) {
    const y = anchor.getFullYear();
    const m = anchor.getMonth();
    const start = new Date(y, m, 1, 0, 0, 0, 0);
    const end = new Date(y, m + 1, 0, 23, 59, 59, 999);
    return { start: start.toISOString(), end: end.toISOString() };
}

const visibleMonthTitle = computed(() => {
    const d = tableMonth.value;
    const raw = d.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
    return raw.charAt(0).toUpperCase() + raw.slice(1);
});

const tableRows = computed(() => {
    let rows = [...tableEventsRaw.value];
    if (tableTypeFilter.value?.length) {
        const set = new Set(tableTypeFilter.value);
        rows = rows.filter((r) => set.has(r.event_type));
    }
    const q = (tableSearch.value || '').trim().toLowerCase();
    if (q) {
        rows = rows.filter((r) => {
            const t = (r.title || '').toLowerCase();
            const d = (r.description || '').toLowerCase();
            return t.includes(q) || d.includes(q);
        });
    }
    rows.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    return rows;
});

function visualRowClass(data) {
    const t = (data?.event_type || 'EVENT').toLowerCase();
    return `calendar-visual-row calendar-visual-row--${t}`;
}

function clearVisualFilters() {
    tableSearch.value = '';
    tableTypeFilter.value = [];
}

async function loadTableMonthEvents() {
    tableLoading.value = true;
    try {
        const { start, end } = monthRangeIsoLocal(tableMonth.value);
        const res = await api.get('calendar/', { params: { start, end } });
        const raw = res.data;
        tableEventsRaw.value = Array.isArray(raw) ? raw : raw?.results ?? [];
    } catch (e) {
        console.error(e);
        toast.add({
            severity: 'error',
            summary: 'Erro',
            detail: 'Não foi possível carregar os eventos deste mês.',
            life: 4000
        });
        tableEventsRaw.value = [];
    } finally {
        tableLoading.value = false;
    }
}

function shiftTableMonth(delta) {
    const d = new Date(tableMonth.value);
    d.setMonth(d.getMonth() + delta);
    tableMonth.value = d;
}

function formatWhenCell(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    const wd = d.toLocaleDateString('pt-BR', { weekday: 'short' });
    const datePart = d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
    const cap = wd.charAt(0).toUpperCase() + wd.slice(1);
    return `${cap} · ${datePart}`;
}

function formatTimeCell(iso, eventType) {
    if (!iso) return '—';
    if (eventType === 'HOLIDAY') {
        return 'Dia inteiro';
    }
    return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function formatEndCell(iso, eventType) {
    if (!iso) return '—';
    if (eventType === 'HOLIDAY') {
        return '—';
    }
    return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function openEventFromApiRow(row) {
    let startTime = row.start_time || '';
    let endTime = row.end_time || '';
    if (row.event_type === 'HOLIDAY') {
        if (startTime && startTime.length === 10) startTime += 'T00:00:00';
        if (endTime && endTime.length === 10) endTime += 'T23:59:59';
    }
    selectedEvent.value = {
        id: row.id,
        title: row.title,
        start_time: startTime,
        end_time: endTime,
        event_type: row.event_type,
        target_audience: row.target_audience,
        classroom: row.classroom,
        subject: row.subject,
        description: row.description,
        created_by: row.created_by
    };
    eventDialog.value = true;
}

function onTableRowClick(ev) {
    openEventFromApiRow(ev.data);
}

watch(usesFamilySchoolCalendarUi, (fam) => {
    if (fam) {
        viewMode.value = 'visual';
        loadTableMonthEvents();
    }
}, { immediate: true });

watch(viewMode, (v) => {
    if (usesFamilySchoolCalendarUi.value) {
        return;
    }
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, v);
    if (v === 'visual') {
        loadTableMonthEvents();
    } else {
        queueMicrotask(() => fullCalendarRef.value?.getApi?.()?.refetchEvents?.());
    }
});

watch(tableMonth, () => {
    if (usesFamilySchoolCalendarUi.value || viewMode.value === 'visual') {
        loadTableMonthEvents();
    }
});

async function refreshCalendars() {
    if (!usesFamilySchoolCalendarUi.value) {
        try {
            fullCalendarRef.value?.getApi?.()?.refetchEvents?.();
        } catch (_) {
            /* ignore */
        }
    }
    if (usesFamilySchoolCalendarUi.value || viewMode.value === 'visual') {
        await loadTableMonthEvents();
    }
}

onMounted(() => {
    window.addEventListener('resize', updateMobile);
    updateMobile();
    if (!usesFamilySchoolCalendarUi.value) {
        loadDependencies();
    }
    if (usesFamilySchoolCalendarUi.value || viewMode.value === 'visual') {
        loadTableMonthEvents();
    }
});
</script>

<template>
    <div class="card calendar-page">
        <Toast />
        <div class="calendar-page__header flex flex-wrap justify-between items-center gap-4 mb-4">
            <div class="min-w-[200px] flex-1">
                <h2 class="calendar-page__title m-0">
                    {{ usesFamilySchoolCalendarUi ? 'Calendário escolar' : 'Calendário Acadêmico' }}
                </h2>
                <p
                    v-if="!usesFamilySchoolCalendarUi && viewMode === 'managerial'"
                    class="text-muted-color m-0 mt-2 max-w-lg text-sm leading-relaxed"
                >
                    Grade semanal ou mensal para cruzar horários e planear com a equipa.
                </p>
            </div>
            <div v-if="!usesFamilySchoolCalendarUi" class="flex flex-wrap items-center gap-2">
                <div class="calendar-view-toggle" role="group" aria-label="Tipo de visualização">
                    <button
                        type="button"
                        class="calendar-view-toggle__btn"
                        :class="{ 'calendar-view-toggle__btn--active': viewMode === 'visual' }"
                        @click="viewMode = 'visual'"
                    >
                        <i class="pi pi-palette text-sm" aria-hidden="true" />
                        <span>Visual</span>
                    </button>
                    <button
                        type="button"
                        class="calendar-view-toggle__btn"
                        :class="{ 'calendar-view-toggle__btn--active': viewMode === 'managerial' }"
                        @click="viewMode = 'managerial'"
                    >
                        <i class="pi pi-calendar text-sm" aria-hidden="true" />
                        <span>Gerencial</span>
                    </button>
                </div>
                <Button
                    v-if="canCreate"
                    label="Novo evento"
                    icon="pi pi-plus"
                    size="small"
                    outlined
                    severity="secondary"
                    class="shrink-0"
                    @click="openNewEvent"
                />
            </div>
        </div>

        <div v-show="usesFamilySchoolCalendarUi || viewMode === 'visual'" class="calendar-visual-table">
            <div
                class="visual-month-strip mb-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 sm:px-4 dark:border-surface-700 dark:bg-surface-900"
            >
                <Button
                    icon="pi pi-chevron-left"
                    text
                    rounded
                    size="small"
                    severity="secondary"
                    class="visual-month-strip__chev shrink-0"
                    aria-label="Mês anterior"
                    @click="shiftTableMonth(-1)"
                />
                <div class="min-w-0 flex-1 text-center">
                    <h3 class="visual-month-strip__title m-0 text-base font-semibold text-surface-900 sm:text-lg dark:text-surface-0">
                        {{ visibleMonthTitle }}
                    </h3>
                    <p class="text-muted-color m-0 mt-0.5 text-xs">
                        {{ tableRows.length }}
                        {{ tableRows.length === 1 ? 'evento' : 'eventos' }}
                        <span v-if="tableTypeFilter.length || tableSearch.trim()"> · filtros ativos</span>
                    </p>
                </div>
                <Button
                    icon="pi pi-chevron-right"
                    text
                    rounded
                    size="small"
                    severity="secondary"
                    class="visual-month-strip__chev shrink-0"
                    aria-label="Próximo mês"
                    @click="shiftTableMonth(1)"
                />
            </div>

            <div class="calendar-visual-filters mb-4 flex flex-wrap items-center gap-3">
                <div class="flex min-w-[min(100%,16rem)] flex-1 flex-col gap-2">
                    <label class="text-xs font-semibold uppercase tracking-wide text-muted-color">Tipos de evento</label>
                    <MultiSelect
                        v-model="tableTypeFilter"
                        :options="eventTypes"
                        optionLabel="label"
                        optionValue="value"
                        display="chip"
                        filter
                        placeholder="Todos os tipos"
                        :maxSelectedLabels="2"
                        class="w-full"
                    />
                </div>
                <div class="flex min-w-[min(100%,18rem)] flex-1 flex-col gap-2">
                    <label class="text-xs font-semibold uppercase tracking-wide text-muted-color">Procurar</label>
                    <IconField iconPosition="left" class="w-full">
                        <InputIcon>
                            <i class="pi pi-search" />
                        </InputIcon>
                        <InputText v-model="tableSearch" placeholder="Título ou descrição…" fluid />
                    </IconField>
                </div>
                <Button
                    label="Limpar filtros"
                    icon="pi pi-filter-slash"
                    text
                    size="small"
                    type="button"
                    class="shrink-0 self-center sm:self-auto"
                    :disabled="!tableSearch.trim() && !tableTypeFilter.length"
                    @click="clearVisualFilters"
                />
            </div>

            <DataTable
                :value="tableRows"
                :loading="tableLoading"
                stripedRows
                responsiveLayout="scroll"
                paginator
                :rows="15"
                :rowsPerPageOptions="[15, 30, 60]"
                sortMode="multiple"
                removableSort
                dataKey="id"
                :rowClass="visualRowClass"
                class="p-datatable-sm calendar-visual-datatable"
                @row-click="onTableRowClick"
            >
                <Column field="start_time" header="Quando" sortable style="min-width: 10rem">
                    <template #body="{ data }">
                        <span class="font-medium text-900">{{ formatWhenCell(data.start_time) }}</span>
                    </template>
                </Column>
                <Column header="Início" style="min-width: 5rem">
                    <template #body="{ data }">
                        {{ formatTimeCell(data.start_time, data.event_type) }}
                    </template>
                </Column>
                <Column header="Fim" style="min-width: 5rem">
                    <template #body="{ data }">
                        {{ formatEndCell(data.end_time, data.event_type) }}
                    </template>
                </Column>
                <Column field="title" header="Evento" sortable style="min-width: 14rem" />
                <Column field="event_type" header="Tipo" sortable style="min-width: 9rem">
                    <template #body="{ data }">
                        <Tag
                            :value="getLabel(eventTypes, data.event_type)"
                            :severity="eventTypeSeverity(data.event_type)"
                            class="text-xs"
                        />
                    </template>
                </Column>
                <Column field="target_audience" header="Público" sortable style="min-width: 9rem">
                    <template #body="{ data }">
                        <span class="text-sm">{{ getLabel(targetAudiences, data.target_audience) }}</span>
                    </template>
                </Column>
                <Column field="class_name" header="Turma" style="min-width: 7rem">
                    <template #body="{ data }">
                        <span class="text-sm text-700">{{ data.class_name || '—' }}</span>
                    </template>
                </Column>
            </DataTable>
        </div>

        <div v-show="!usesFamilySchoolCalendarUi && viewMode === 'managerial'" class="calendar-gerencial-host">
            <FullCalendar ref="fullCalendarRef" :options="calendarOptions" />
        </div>

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

<style scoped>
.calendar-page__title {
    font-size: clamp(1.35rem, 2.5vw, 1.75rem);
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(120deg, var(--p-primary-600, #7e22ce), var(--p-primary-400, #c084fc));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

.calendar-view-toggle {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem;
    border-radius: 999px;
    background: var(--p-surface-100, #f4f4f5);
    border: 1px solid var(--p-content-border-color, #e4e4e7);
    gap: 0.125rem;
}

.calendar-view-toggle__btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    border: 1px solid transparent;
    border-radius: 999px;
    padding: 0.55rem 1.1rem;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--p-text-muted-color, #71717a);
    background: transparent;
    cursor: pointer;
    transition:
        background 0.2s ease,
        color 0.2s ease,
        box-shadow 0.2s ease,
        transform 0.15s ease;
}

.calendar-view-toggle__btn:hover:not(.calendar-view-toggle__btn--active) {
    color: var(--p-text-color, #18181b);
    background: color-mix(in srgb, var(--p-surface-0, #fff) 70%, transparent);
}

.calendar-view-toggle__btn--active {
    color: var(--p-primary-color, #7c3aed);
    background: color-mix(in srgb, var(--p-primary-50, #faf5ff) 100%, transparent);
    border: 1px solid color-mix(in srgb, var(--p-primary-200, #e9d5ff) 90%, transparent);
    box-shadow: none;
}

.calendar-view-toggle__btn--active :is(i, .pi) {
    color: var(--p-primary-color, #7c3aed);
}

.visual-month-strip__title {
    letter-spacing: -0.02em;
}

.calendar-visual-datatable :deep(tbody tr) {
    cursor: pointer;
    transition: background 0.15s ease;
}

.calendar-visual-datatable :deep(tbody tr.calendar-visual-row td:first-child) {
    box-shadow: inset 4px 0 0 0 var(--row-accent, #a1a1aa);
}

.calendar-visual-datatable :deep(tbody tr.calendar-visual-row--holiday td:first-child) {
    --row-accent: #ef4444;
}
.calendar-visual-datatable :deep(tbody tr.calendar-visual-row--exam td:first-child) {
    --row-accent: #f59e0b;
}
.calendar-visual-datatable :deep(tbody tr.calendar-visual-row--school_day td:first-child) {
    --row-accent: #22c55e;
}
.calendar-visual-datatable :deep(tbody tr.calendar-visual-row--meeting td:first-child) {
    --row-accent: #8b5cf6;
}
.calendar-visual-datatable :deep(tbody tr.calendar-visual-row--assignment td:first-child) {
    --row-accent: #6366f1;
}
.calendar-visual-datatable :deep(tbody tr.calendar-visual-row--event td:first-child) {
    --row-accent: #3b82f6;
}
</style>