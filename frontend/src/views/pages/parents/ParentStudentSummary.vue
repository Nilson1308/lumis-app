<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const route = useRoute();
const router = useRouter();
const toast = useToast();

const loading = ref(true);
const studentId = ref(null);
const student = ref(null);
const diaryEntries = ref([]);
const absenceHistory = ref([]);
const reports = ref([]);
const calendarEvents = ref([]);

const weekLabel = computed(() => {
    const { monday } = getWeekRange();
    return monday.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
});

function getWeekRange() {
    const now = new Date();
    const day = now.getDay();
    const mondayOffset = day === 0 ? -6 : 1 - day;
    const monday = new Date(now);
    monday.setDate(now.getDate() + mondayOffset);
    monday.setHours(0, 0, 0, 0);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    sunday.setHours(23, 59, 59, 999);
    return { monday, sunday, startIso: monday.toISOString(), endIso: sunday.toISOString() };
}

const toPlainText = (html) => {
    if (!html) return '';
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return (doc.documentElement.textContent || '')
        .replace(/\u00A0/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
};

const snippet = (html, maxLen = 160) => {
    const t = toPlainText(html);
    if (!t) return '';
    return t.length > maxLen ? `${t.slice(0, maxLen)}…` : t;
};

const formatDate = (d) => {
    if (!d) return '';
    const s = typeof d === 'string' ? d : d;
    return new Date(String(s).slice(0, 10) + 'T12:00:00').toLocaleDateString('pt-BR');
};

const formatDateTime = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleString('pt-BR', {
        weekday: 'short',
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
};

const eventTypeLabel = (type) => {
    const map = {
        HOLIDAY: 'Feriado',
        SCHOOL_DAY: 'Dia letivo',
        EXAM: 'Prova',
        ASSIGNMENT: 'Entrega',
        EVENT: 'Evento',
        MEETING: 'Reunião'
    };
    return map[type] || type || 'Evento';
};

const filterEventsForFamily = (events, classroomId) => {
    return events
        .filter((e) => {
            if (e.target_audience === 'ALL') return true;
            if (e.target_audience === 'CLASSROOM' && classroomId && e.classroom === classroomId) return true;
            return false;
        })
        .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
};

const loadSummary = async () => {
    loading.value = true;
    try {
        const id = parseInt(route.params.id, 10);
        studentId.value = id;
        const { startIso, endIso } = getWeekRange();

        const childrenRes = await api.get('students/my-children/');
        const current = childrenRes.data.find((c) => c.id === id);
        if (!current) {
            toast.add({ severity: 'warn', summary: 'Acesso', detail: 'Aluno não encontrado na sua conta.' });
            router.push({ name: 'parent-dashboard' });
            return;
        }
        student.value = current;
        const classroomId = current.classroom_id ?? null;

        const [diaryRes, attRes, repRes, calRes] = await Promise.all([
            api.get(`students/${id}/class-diary/`),
            api.get(`students/${id}/attendance-report/`),
            api.get(`student-reports/?student=${id}&page_size=5`),
            api.get('calendar/', { params: { start: startIso, end: endIso } })
        ]);

        const diaryData = Array.isArray(diaryRes.data) ? diaryRes.data : diaryRes.data?.results || [];
        diaryEntries.value = diaryData.slice(0, 5);

        const hist = attRes.data?.history || [];
        absenceHistory.value = hist.slice(0, 5);

        const repData = repRes.data?.results || repRes.data || [];
        reports.value = repData.slice(0, 3);

        const rawCal = Array.isArray(calRes.data) ? calRes.data : [];
        calendarEvents.value = filterEventsForFamily(rawCal, classroomId).slice(0, 10);
    } catch (e) {
        console.error(e);
        toast.add({
            severity: 'error',
            summary: 'Erro',
            detail: 'Não foi possível carregar o resumo.',
            life: 4000
        });
    } finally {
        loading.value = false;
    }
};

const goBack = () => router.push({ name: 'parent-dashboard' });
const goDiary = () => router.push({ name: 'parent-class-diary', params: { id: studentId.value } });
const goAttendance = () => router.push({ name: 'parent-attendance', params: { id: studentId.value } });
const goReports = () => router.push({ name: 'parent-reports', params: { id: studentId.value } });
const goCalendar = () => router.push({ name: 'parent-calendar' });

onMounted(() => {
    loadSummary();
});
</script>

<template>
    <div class="grid grid-cols-12 gap-4 mb-2">
        <Toast />

        <div class="col-span-12">
            <div class="card mb-0">
                <div class="flex flex-col md:flex-row md:align-items-center md:justify-content-between gap-3">
                    <div class="flex align-items-center gap-2">
                        <Button icon="pi pi-arrow-left" class="p-button-rounded p-button-text" @click="goBack" />
                        <div>
                            <div class="text-500 text-sm">Resumo da semana</div>
                            <div class="text-900 font-bold text-xl">{{ student?.name || '…' }}</div>
                            <div class="text-600 text-sm">{{ student?.classroom_name }} · {{ weekLabel }}</div>
                        </div>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <Button label="Diário completo" icon="pi pi-bookmark" class="p-button-outlined p-button-sm" @click="goDiary" />
                        <Button label="Frequência" icon="pi pi-calendar-times" class="p-button-outlined p-button-sm" @click="goAttendance" />
                        <Button label="Calendário" icon="pi pi-calendar" class="p-button-outlined p-button-sm" @click="goCalendar" />
                    </div>
                </div>
            </div>
        </div>

        <div class="col-span-12 lg:col-span-4">
            <div class="card h-full">
                <h5 class="mt-0 mb-2">Calendário (esta semana)</h5>
                <p class="text-600 text-sm mb-3">Próximos eventos relevantes à turma do aluno e avisos gerais.</p>
                <div v-if="loading" class="text-500 text-sm">Carregando…</div>
                <ul v-else-if="calendarEvents.length" class="list-none p-0 m-0">
                    <li
                        v-for="ev in calendarEvents"
                        :key="ev.id"
                        class="py-2 border-bottom-1 surface-border last:border-none"
                    >
                        <div class="text-sm font-semibold text-900">{{ ev.title }}</div>
                        <div class="text-xs text-600">{{ formatDateTime(ev.start_time) }}</div>
                        <Tag :value="eventTypeLabel(ev.event_type)" severity="secondary" class="text-xs mt-1" />
                    </li>
                </ul>
                <p v-else class="text-500 text-sm m-0">Nenhum evento nesta semana.</p>
                <Button label="Abrir calendário completo" icon="pi pi-external-link" class="p-button-text p-button-sm mt-3 w-full" @click="goCalendar" />
            </div>
        </div>

        <div class="col-span-12 lg:col-span-4">
            <div class="card h-full">
                <h5 class="mt-0 mb-2">Diário de classe (recente)</h5>
                <div v-if="loading" class="text-500 text-sm">Carregando…</div>
                <ul v-else-if="diaryEntries.length" class="list-none p-0 m-0">
                    <li
                        v-for="row in diaryEntries"
                        :key="row.id"
                        class="py-2 border-bottom-1 surface-border last:border-none"
                    >
                        <div class="flex justify-content-between gap-2">
                            <span class="font-semibold text-900">{{ row.subject_name }}</span>
                            <span class="text-600 text-sm whitespace-nowrap">{{ formatDate(row.date) }}</span>
                        </div>
                        <div class="text-sm text-700 line-height-3 mt-1">{{ snippet(row.content, 160) }}</div>
                    </li>
                </ul>
                <p v-else class="text-500 text-sm m-0">Sem registros de aula recentes.</p>
                <Button label="Ver diário completo" icon="pi pi-angle-right" class="p-button-text p-button-sm mt-3 w-full" @click="goDiary" />
            </div>
        </div>

        <div class="col-span-12 lg:col-span-4">
            <div class="card h-full">
                <h5 class="mt-0 mb-2">Frequência (últimas ausências)</h5>
                <div v-if="loading" class="text-500 text-sm">Carregando…</div>
                <ul v-else-if="absenceHistory.length" class="list-none p-0 m-0">
                    <li
                        v-for="row in absenceHistory"
                        :key="row.id"
                        class="py-2 border-bottom-1 surface-border last:border-none"
                    >
                        <div class="flex justify-content-between gap-2">
                            <span class="font-semibold text-900">{{ row.subject }}</span>
                            <span class="text-600 text-sm">{{ formatDate(row.date) }}</span>
                        </div>
                        <div class="text-xs text-600 mt-1">
                            <span v-if="row.justified">Abonada</span>
                            <span v-else-if="row.justification_status === 'PENDING'">Justificativa em análise</span>
                            <span v-else-if="row.justification_status === 'REJECTED'">Justificativa recusada</span>
                            <span v-else>Sem justificativa</span>
                        </div>
                    </li>
                </ul>
                <p v-else class="text-500 text-sm m-0">Nenhuma ausência registrada.</p>
                <Button label="Ver frequência completa" icon="pi pi-angle-right" class="p-button-text p-button-sm mt-3 w-full" @click="goAttendance" />
            </div>
        </div>

        <div class="col-span-12">
            <div class="card">
                <h5 class="mt-0 mb-2">Relatórios pedagógicos (recentes)</h5>
                <div v-if="loading" class="text-500 text-sm">Carregando…</div>
                <div v-else-if="reports.length" class="grid grid-cols-12 gap-3">
                    <div
                        v-for="r in reports"
                        :key="r.id"
                        class="col-span-12 md:col-span-4"
                    >
                        <div class="p-3 border-1 surface-border border-round surface-hover cursor-pointer h-full" @click="goReports">
                            <div class="text-primary font-bold">{{ r.subject }}</div>
                            <div class="text-600 text-sm">{{ formatDate(r.date) }}</div>
                            <div class="text-sm text-700 mt-2 line-height-3">{{ snippet(r.content, 120) }}</div>
                        </div>
                    </div>
                </div>
                <p v-else class="text-500 text-sm m-0">Nenhum relatório disponível no momento.</p>
                <Button label="Ver todos os relatórios" icon="pi pi-angle-right" class="p-button-text p-button-sm mt-3" @click="goReports" />
            </div>
        </div>
    </div>
</template>
