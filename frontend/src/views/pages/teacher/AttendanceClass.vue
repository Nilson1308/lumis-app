<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const route = useRoute();
const router = useRouter();
const toast = useToast();

const assignmentId = route.params.id;

// --- ESTADOS ---
const assignment = ref(null);
const students = ref([]);
const loading = ref(true);
const saving = ref(false);

// Data da Chamada (Padrão: Hoje)
const attendanceDate = ref(new Date());

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
const loadClassData = async () => {
    loading.value = true;
    try {
        // 1. Pega dados da turma/matéria
        const resAssign = await api.get(`assignments/${assignmentId}/`);
        assignment.value = resAssign.data;

        // 2. Carrega alunos da turma
        const resEnroll = await api.get(`enrollments/?classroom=${assignment.value.classroom}&page_size=100`);
        
        // 3. Prepara a lista base (assumindo Presença = True inicialmente)
        const initialStudents = resEnroll.data.results.map(s => ({
            id: s.id, // ID da Matrícula (Enrollment)
            student_name: s.student_name,
            present: true // Padrão: Veio na aula
        }));

        students.value = initialStudents;

        // 4. Verifica se JÁ teve chamada nesta data
        await checkExistingAttendance();

    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar turma', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- VERIFICAR CHAMADA EXISTENTE ---
const checkExistingAttendance = async () => {
    if (!assignment.value) return;
    
    // Mostra loading rápido na tabela para dar feedback visual
    // (opcional, mas bom pra UX)
    
    const dateStr = formatDateForAPI(attendanceDate.value);

    try {
        // Busca registros dessa matéria, nessa turma, nessa data
        const res = await api.get(`attendance/?subject=${assignment.value.subject}&date=${dateStr}&enrollment__classroom=${assignment.value.classroom}`);
        
        const existingRecords = res.data.results;

        // Atualiza o estado visual
        students.value.forEach(student => {
            // Tenta achar o registro de presença para este aluno (enrollment)
            const record = existingRecords.find(r => r.enrollment === student.id);
            
            if (record) {
                // Se achou registro, usa o valor do banco
                student.present = record.present;
            } else {
                // Se não achou (ex: aluno novo ou dia sem chamada), assume Presente
                student.present = true;
            }
        });

        if (existingRecords.length > 0) {
            toast.add({ severity: 'info', summary: 'Registro Encontrado', detail: 'Carregando chamada anterior.', life: 2000 });
        }

    } catch (e) {
        console.error("Erro ao verificar chamada", e);
    }
};

// Observa mudança na data para recarregar dados
watch(attendanceDate, () => {
    checkExistingAttendance();
});

// --- SALVAR (BULK) ---
const saveAttendance = async () => {
    saving.value = true;
    try {
        const dateStr = formatDateForAPI(attendanceDate.value);
        
        const payload = {
            subject: assignment.value.subject,
            date: dateStr,
            records: students.value.map(s => ({
                enrollment_id: s.id,
                present: s.present
            }))
        };

        await api.post('attendance/bulk_save/', payload);
        
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Chamada salva!', life: 3000 });
        
        // Recarrega para garantir sincronia (opcional)
        await checkExistingAttendance();
        
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar chamada.', life: 3000 });
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
                    <DatePicker v-model="attendanceDate" dateFormat="dd/mm/yy" showIcon fluid />
                    <Button label="Salvar Chamada" icon="pi pi-check" :loading="saving" @click="saveAttendance" />
                </div>
            </div>

            <DataTable :value="students" :loading="loading" responsiveLayout="scroll" size="small" stripedRows>
                <template #empty>Nenhum aluno nesta turma.</template>

                <Column field="student_name" header="Aluno" sortable></Column>
                
                <Column header="Presença" style="width: 20%">
                    <template #body="slotProps">
                        <ToggleButton 
                            v-model="slotProps.data.present" 
                            onLabel="Presente" 
                            offLabel="Faltou"
                            onIcon="pi pi-check" 
                            offIcon="pi pi-times"
                            class="w-full sm:w-10rem"
                            :class="{ 'p-button-danger': !slotProps.data.present, 'p-button-success': slotProps.data.present }"
                        />
                    </template>
                </Column>
            </DataTable>
        </div>
    </div>
</template>