<script setup>
import { ref, onMounted, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';
import WeeklyCalendar from '@/components/WeeklyCalendar.vue';
import AttendanceStatsDialog from '@/components/AttendanceStatsDialog.vue';

const route = useRoute();
const router = useRouter();
const toast = useToast();

const assignmentId = route.params.id;

// --- ESTADOS ---
const assignment = ref(null);
const students = ref([]);
const loading = ref(true);
const saving = ref(false);
const weeklyDates = ref([]);
const classSchedules = ref([]);
const scheduledWeekdays = ref([]);
const nonTeachingDates = ref([]);
const pendingAttendance = ref([]);
const pendingRange = ref(null);
const statsDialogVisible = ref(false);
const selectedStudent = ref(null);

// Data da Chamada (Padrão: Hoje)
const attendanceDate = ref(new Date());
const attendanceRecorded = ref(false);

// Helper para formatar YYYY-MM-DD sem problemas de fuso
const formatDateForAPI = (date) => {
    if (!date) return '';
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const formatDateBR = (dateValue) => {
    if (!dateValue) return '';
    const raw = typeof dateValue === 'string' ? dateValue : formatDateForAPI(dateValue);
    const [year, month, day] = raw.split('-');
    if (!year || !month || !day) return raw;
    return `${day}/${month}/${year}`;
};

const getWeekdayNumber = (date) => {
    const d = new Date(date);
    return d.getDay(); // 0=Domingo ... 6=Sábado
};

const hasScheduleRestriction = computed(() => scheduledWeekdays.value.length > 0);
const nonTeachingDatesSet = computed(() => new Set(nonTeachingDates.value));

const disabledWeekdays = computed(() => {
    if (!hasScheduleRestriction.value) return [];
    const allowed = new Set(scheduledWeekdays.value);
    return [0, 1, 2, 3, 4, 5, 6].filter((day) => !allowed.has(day));
});

const isSelectedDateAllowed = computed(() => {
    if (!attendanceDate.value) return true;
    const dateStr = formatDateForAPI(attendanceDate.value);
    if (nonTeachingDatesSet.value.has(dateStr)) return false;
    if (!hasScheduleRestriction.value) return true;
    return scheduledWeekdays.value.includes(getWeekdayNumber(attendanceDate.value));
});

const disabledSpecificDates = computed(() =>
    nonTeachingDates.value
        .map((dateStr) => {
            const [year, month, day] = dateStr.split('-').map(Number);
            return new Date(year, month - 1, day);
        })
);

const scheduleSummary = computed(() => {
    if (!classSchedules.value.length) return '';
    return classSchedules.value
        .map((item) => `${item.day_label} ${item.start} - ${item.end}`)
        .join(' | ');
});

// --- CARREGAR DADOS ---
const loadClassData = async () => {
    loading.value = true;
    try {
        // 1. Pega dados da turma/matéria
        const resAssign = await api.get(`assignments/${assignmentId}/`);
        assignment.value = resAssign.data;

        // 2. Carrega alunos da turma (page_size alto para turma inteira)
        const resEnroll = await api.get(`enrollments/`, {
            params: { classroom: assignment.value.classroom, page_size: 1000 }
        });
        
        // 3. Prepara a lista base (assumindo Presença = True inicialmente)
        const initialStudents = resEnroll.data.results.map(s => ({
            id: s.id, // ID da Matrícula (Enrollment)
            student_name: s.student_name,
            present: true // Padrão: Veio na aula
        }));

        students.value = initialStudents;
        await loadClassSchedules();
        await loadNonTeachingDatesForCurrentMonth();
        ensureAllowedDateSelection();
        await loadPendingAttendance();

        // 4. Verifica se JÁ teve chamada nesta data
        await checkExistingAttendance();
        
        // 5. Carrega datas da semana
        await loadWeeklyDates();

    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar turma', life: 3000 });
    } finally {
        loading.value = false;
    }
};

const loadNonTeachingDatesForCurrentMonth = async () => {
    if (!assignment.value || !attendanceDate.value) return;
    const d = new Date(attendanceDate.value);
    const year = d.getFullYear();
    const month = d.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    try {
        const res = await api.get('attendance/non-teaching-dates/', {
            params: {
                classroom: assignment.value.classroom,
                start_date: formatDateForAPI(firstDay),
                end_date: formatDateForAPI(lastDay),
            },
        });
        const dates = Array.isArray(res.data) ? res.data : (res.data?.dates || []);
        nonTeachingDates.value = Array.isArray(dates) ? dates : [];
    } catch (error) {
        console.error('Erro ao carregar dias não letivos', error);
        nonTeachingDates.value = [];
    }
};

const loadPendingAttendance = async () => {
    try {
        const res = await api.get('attendance/pending-by-assignment/', {
            params: { assignment: Number(assignmentId) }
        });
        pendingAttendance.value = res.data?.pending_dates || [];
        pendingRange.value = res.data?.date_range || null;
    } catch (error) {
        console.error('Erro ao carregar pendências de frequência', error);
        pendingAttendance.value = [];
        pendingRange.value = null;
    }
};

const loadClassSchedules = async () => {
    if (!assignment.value) return;
    try {
        const res = await api.get('schedules/', {
            params: {
                classroom: assignment.value.classroom,
                page_size: 1000
            }
        });
        const rows = (res.data?.results || res.data || [])
            .filter((item) => Number(item.assignment) === Number(assignmentId));

        const dayLabels = {
            0: 'Dom',
            1: 'Seg',
            2: 'Ter',
            3: 'Qua',
            4: 'Qui',
            5: 'Sex',
            6: 'Sáb'
        };

        classSchedules.value = rows.map((item) => ({
            day: item.day_of_week,
            day_label: dayLabels[item.day_of_week] || String(item.day_of_week),
            start: String(item.start_time || '').slice(0, 5),
            end: String(item.end_time || '').slice(0, 5)
        }));

        scheduledWeekdays.value = [...new Set(rows.map((item) => item.day_of_week))];
    } catch (error) {
        console.error('Erro ao carregar grade horária da atribuição', error);
        classSchedules.value = [];
        scheduledWeekdays.value = [];
    }
};

const ensureAllowedDateSelection = () => {
    if (!attendanceDate.value) return;
    if (isSelectedDateAllowed.value) return;

    const base = new Date(attendanceDate.value);
    for (let i = 0; i < 21; i++) {
        const candidate = new Date(base);
        candidate.setDate(base.getDate() + i);
        const candidateStr = formatDateForAPI(candidate);
        const allowedBySchedule = !hasScheduleRestriction.value || scheduledWeekdays.value.includes(candidate.getDay());
        const isHoliday = nonTeachingDatesSet.value.has(candidateStr);
        if (allowedBySchedule && !isHoliday) {
            attendanceDate.value = candidate;
            toast.add({
                severity: 'info',
                summary: 'Data ajustada',
                detail: 'A chamada foi posicionada para o próximo dia letivo com aula desta matéria.',
                life: 3500
            });
            return;
        }
    }
};

// --- CARREGAR DATAS COM CHAMADA (mês visualizado) ---
const loadWeeklyDates = async () => {
    if (!assignment.value) return;

    const refDate = attendanceDate.value || new Date();
    const month = refDate.getMonth() + 1;
    const year = refDate.getFullYear();

    try {
        const res = await api.get(`attendance/weekly_dates/`, {
            params: {
                subject: assignment.value.subject,
                classroom: assignment.value.classroom,
                month,
                year
            }
        });
        weeklyDates.value = res.data || [];
    } catch (e) {
        console.error("Erro ao carregar datas de chamada", e);
        weeklyDates.value = [];
    }
};

// --- VERIFICAR CHAMADA EXISTENTE (endpoint daily-log SEM paginação) ---
const checkExistingAttendance = async () => {
    if (!assignment.value) return;
    if (!isSelectedDateAllowed.value) {
        attendanceRecorded.value = false;
        students.value.forEach((student) => {
            student.present = true;
            student.recorded = false;
        });
        return;
    }

    const dateStr = formatDateForAPI(attendanceDate.value);

    try {
        const res = await api.get('attendance/daily-log/', {
            params: {
                date: dateStr,
                classroom: assignment.value.classroom,
                subject: assignment.value.subject
            }
        });

        const existingRecords = Array.isArray(res.data) ? res.data : [];
        attendanceRecorded.value = existingRecords.length > 0;

        // Atualiza o estado visual
        students.value.forEach(student => {
            // Tenta achar o registro de presença para este aluno (enrollment)
            const record = existingRecords.find(r => r.enrollment === student.id);
            
            if (record) {
                // Se achou registro, usa o valor do banco
                student.present = record.present;
                student.recorded = true;
            } else {
                // Se não achou (ex: aluno novo ou dia sem chamada), assume Presente
                student.present = true;
                student.recorded = false;
            }
        });

        if (existingRecords.length > 0) {
            toast.add({ severity: 'info', summary: 'Registro Encontrado', detail: 'Carregando chamada anterior.', life: 2000 });
        }

        // Recarrega datas da semana
        await loadWeeklyDates();

    } catch (e) {
        console.error("Erro ao verificar chamada", e);
    }
};

// Observa mudança na data para recarregar dados
watch(attendanceDate, () => {
    loadNonTeachingDatesForCurrentMonth();
    ensureAllowedDateSelection();
    checkExistingAttendance();
    loadWeeklyDates();
});

// --- ABRIR DIALOG DE ESTATÍSTICAS ---
const openStatsDialog = (student) => {
    selectedStudent.value = student;
    statsDialogVisible.value = true;
};

// --- SALVAR (BULK) ---
const saveAttendance = async () => {
    if (!isSelectedDateAllowed.value) {
        toast.add({
            severity: 'warn',
            summary: 'Data inválida para chamada',
            detail: 'Selecione um dia letivo em que esta matéria possui aula na grade.',
            life: 4500
        });
        return;
    }

    saving.value = true;
    try {
        const dateStr = formatDateForAPI(attendanceDate.value);
        
        const payload = {
            assignment: Number(assignmentId),
            classroom: assignment.value.classroom,
            subject: assignment.value.subject,
            date: dateStr,
            records: students.value.map(s => ({
                enrollment_id: s.id,
                present: s.present
            }))
        };

        await api.post('attendance/bulk_save/', payload);
        
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Chamada salva!', life: 3000 });
        
        // Marca como realizado
        attendanceRecorded.value = true;
        students.value.forEach(s => s.recorded = true);
        
        // Recarrega para garantir sincronia
        await checkExistingAttendance();
        await loadPendingAttendance();
        
    } catch (error) {
        const msg = error.response?.data?.error || error.response?.data?.detail || error.message || 'Erro ao salvar chamada.';
        toast.add({ severity: 'error', summary: 'Falha ao Salvar', detail: msg, life: 5000 });
    } finally {
        saving.value = false;
    }
};

const goBack = () => {
    router.go(-1);
};

onMounted(() => {
    loadClassData();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            
            <div class="flex flex-col md:flex-row justify-between items-center mb-4" v-if="assignment">
                <div class="flex items-center mb-3 md:mb-0">
                    <Button icon="pi pi-arrow-left" class="p-button-text mr-2" @click="goBack" />
                    <div>
                        <span class="block text-xl font-bold">{{ assignment.subject_name }}</span>
                        <span class="text-600">{{ assignment.classroom_name }}</span>
                    </div>
                </div>

                <div class="flex flex-col md:flex-row items-center gap-3">
                    <label class="block font-bold">Data da Aula:</label>
                    <DatePicker
                        v-model="attendanceDate"
                        dateFormat="dd/mm/yy"
                        showIcon
                        fluid
                        :disabledDays="disabledWeekdays"
                        :disabledDates="disabledSpecificDates"
                    />
                    <Button label="Salvar Chamada" icon="pi pi-check" :loading="saving" @click="saveAttendance" />
                </div>
            </div>

            <Message v-if="hasScheduleRestriction" severity="info" class="mb-3">
                Grade desta matéria: {{ scheduleSummary }}
            </Message>
            <Message v-if="hasScheduleRestriction && !isSelectedDateAllowed" severity="warn" class="mb-3">
                A data selecionada não e um dia letivo valido para esta matéria (grade/calendário).
            </Message>
            <Message v-if="pendingAttendance.length > 0" severity="warn" class="mb-3">
                Existem {{ pendingAttendance.length }} data(s) com chamada pendente ate hoje
                <span v-if="pendingRange">
                    (periodo {{ pendingRange.start_br || formatDateBR(pendingRange.start) }} a {{ pendingRange.end_br || formatDateBR(pendingRange.end) }}).
                </span>
                Primeiras pendencias:
                {{ pendingAttendance.slice(0, 5).map((item) => item.date_br || formatDateBR(item.date)).join(', ') }}
            </Message>

            <!-- Calendário Semanal -->
            <div v-if="assignment" class="mb-4">
                <WeeklyCalendar 
                    :attendance-dates="weeklyDates" 
                    :current-date="attendanceDate"
                    @update:current-date="attendanceDate = $event"
                />
            </div>

            <DataTable :value="students" :loading="loading" responsiveLayout="scroll" size="small" stripedRows>
                <template #empty>Nenhum aluno nesta turma.</template>

                <Column header="Aluno" sortable>
                    <template #body="slotProps">
                        <div class="flex items-center gap-2">
                            <Button 
                                icon="pi pi-chart-bar" 
                                class="p-button-text p-button-sm p-button-rounded p-button-info"
                                @click="openStatsDialog(slotProps.data)"
                                v-tooltip.top="'Ver estatísticas de frequência'"
                            />
                            <span>{{ slotProps.data.student_name }}</span>
                        </div>
                    </template>
                </Column>
                
                <Column header="Presença" style="width: 20%">
                    <template #body="slotProps">
                        <ToggleButton 
                            v-model="slotProps.data.present" 
                            onLabel="Presente" 
                            offLabel="Faltou"
                            onIcon="pi pi-check" 
                            offIcon="pi pi-times"
                            class="w-full sm:w-10rem attendance-toggle"
                            :class="{
                                'attendance-not-recorded': !slotProps.data.recorded && slotProps.data.present,
                                'attendance-present': slotProps.data.recorded && slotProps.data.present,
                                'attendance-absent': !slotProps.data.present
                            }"
                        />
                    </template>
                </Column>
            </DataTable>

            <!-- Dialog de Estatísticas -->
            <AttendanceStatsDialog
                v-model:visible="statsDialogVisible"
                :enrollment-id="selectedStudent?.id"
                :student-name="selectedStudent?.student_name"
                :subject-id="assignment?.subject"
                :is-contraturno="false"
            />
        </div>
    </div>
</template>

<style scoped>
:deep(.attendance-toggle) {
    transition: all 0.3s ease;
}

/* Não registrado - padrão cinza */
:deep(.attendance-not-recorded) {
    background-color: white !important;
    border-color: #9ca3af !important;
    color: #374151 !important;
}

:deep(.attendance-not-recorded:hover) {
    background-color: #f3f4f6 !important;
    border-color: #6b7280 !important;
}

:deep(.attendance-not-recorded .p-button-label),
:deep(.attendance-not-recorded .p-button-icon) {
    color: #374151 !important;
}

/* Presente - azul com texto azul */
:deep(.attendance-present) {
    background-color: white !important;
    border-color: #3b82f6 !important;
    border-width: 2px !important;
    color: #3b82f6 !important;
}

:deep(.attendance-present:hover) {
    background-color: #eff6ff !important;
    border-color: #2563eb !important;
}

:deep(.attendance-present .p-button-label),
:deep(.attendance-present .p-button-icon) {
    color: #3b82f6 !important;
}

/* Faltou - roxo com texto branco */
:deep(.attendance-absent) {
    background-color: #9333ea !important;
    border-color: #9333ea !important;
    color: white !important;
}

:deep(.attendance-absent:hover) {
    background-color: #7e22ce !important;
    border-color: #7e22ce !important;
}

:deep(.attendance-absent .p-button-label),
:deep(.attendance-absent .p-button-icon) {
    color: white !important;
}
</style>