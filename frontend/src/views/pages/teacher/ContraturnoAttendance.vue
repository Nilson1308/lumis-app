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

const contraturnoId = route.params.id;

// --- ESTADOS ---
const contraturno = ref(null);
const students = ref([]);
const loading = ref(true);
const saving = ref(false);
const weeklyDates = ref([]);
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

// --- CARREGAR DADOS ---
const loadContraturnoData = async () => {
    loading.value = true;
    try {
        // 1. Pega dados do contraturno
        const resContraturno = await api.get(`contraturno-classrooms/${contraturnoId}/`);
        contraturno.value = resContraturno.data;

        // 2. Carrega alunos de período integral da turma
        // Usa endpoint específico para buscar apenas alunos de período integral
        let fullTimeEnrollments = [];
        try {
            const resEnroll = await api.get(`enrollments/full_time_by_classroom/?classroom=${contraturno.value.classroom}`);
            fullTimeEnrollments = resEnroll.data || [];
        } catch (error) {
            // Fallback: busca todos e filtra no frontend
            console.warn('Endpoint específico não disponível, usando fallback', error);
            const resEnroll = await api.get(`enrollments/?classroom=${contraturno.value.classroom}&page_size=100`);
            fullTimeEnrollments = (resEnroll.data.results || resEnroll.data || []).filter(
                e => e.student_is_full_time === true
            );
        }

        if (fullTimeEnrollments.length === 0) {
            toast.add({ 
                severity: 'warn', 
                summary: 'Atenção', 
                detail: 'Nenhum aluno de período integral encontrado nesta turma. Verifique se o aluno está marcado como período integral.', 
                life: 5000 
            });
        }

        // 3. Prepara a lista base (assumindo Presença = True inicialmente)
        const initialStudents = fullTimeEnrollments.map(s => ({
            id: s.id, // ID da Matrícula (Enrollment)
            student_name: s.student_name,
            present: true // Padrão: Veio no contraturno
        }));

        students.value = initialStudents;

        // 4. Verifica se JÁ teve chamada nesta data
        await checkExistingAttendance();
        
        // 5. Carrega datas da semana
        await loadWeeklyDates();

    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados do contraturno', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- CARREGAR DATAS DA SEMANA ---
const loadWeeklyDates = async () => {
    if (!contraturno.value) return;
    
    try {
        const res = await api.get(`contraturno-attendances/weekly_dates/?contraturno_classroom=${contraturnoId}`);
        weeklyDates.value = res.data || [];
    } catch (e) {
        console.error("Erro ao carregar datas da semana", e);
        weeklyDates.value = [];
    }
};

// --- VERIFICAR CHAMADA EXISTENTE ---
const checkExistingAttendance = async () => {
    if (!contraturno.value) return;
    
    const dateStr = formatDateForAPI(attendanceDate.value);

    try {
        // Busca registros deste contraturno nesta data
        const res = await api.get(`contraturno-attendances/by_contraturno/?contraturno_classroom=${contraturnoId}&date=${dateStr}`);
        
        const existingRecords = res.data;
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
    saving.value = true;
    try {
        const dateStr = formatDateForAPI(attendanceDate.value);
        
        const payload = {
            contraturno_classroom: parseInt(contraturnoId),
            date: dateStr,
            records: students.value.map(s => ({
                enrollment_id: s.id,
                present: s.present
            }))
        };

        await api.post('contraturno-attendances/bulk_save/', payload);
        
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Chamada do contraturno salva!', life: 3000 });
        
        // Marca como realizado
        attendanceRecorded.value = true;
        students.value.forEach(s => s.recorded = true);
        
        // Recarrega para garantir sincronia
        await checkExistingAttendance();
        
    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Erro', detail: error.response?.data?.error || 'Erro ao salvar chamada.', life: 3000 });
    } finally {
        saving.value = false;
    }
};

const goBack = () => {
    router.go(-1);
};

onMounted(() => {
    loadContraturnoData();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            
            <div class="flex flex-col md:flex-row justify-between items-center mb-4" v-if="contraturno">
                <div class="flex items-center mb-3 md:mb-0">
                    <Button icon="pi pi-arrow-left" class="p-button-text mr-2" @click="goBack" />
                    <div>
                        <span class="block text-xl font-bold">Contraturno - {{ contraturno.classroom_name }}</span>
                        <span class="text-600">{{ contraturno.contraturno_period_display }}</span>
                    </div>
                </div>

                <div class="flex flex-col md:flex-row items-center gap-3">
                    <label class="block font-bold">Data:</label>
                    <DatePicker v-model="attendanceDate" dateFormat="dd/mm/yy" showIcon fluid />
                    <Button label="Salvar Chamada" icon="pi pi-check" :loading="saving" @click="saveAttendance" />
                </div>
            </div>

            <!-- Calendário Semanal -->
            <div v-if="contraturno" class="mb-4">
                <WeeklyCalendar 
                    :attendance-dates="weeklyDates" 
                    :current-date="attendanceDate"
                    @update:current-date="attendanceDate = $event"
                />
            </div>

            <DataTable :value="students" :loading="loading" responsiveLayout="scroll" size="small" stripedRows>
                <template #empty>Nenhum aluno de período integral nesta turma.</template>

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
                :is-contraturno="true"
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
