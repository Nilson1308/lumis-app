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
const checklistConfig = ref(null);
const students = ref([]);
const loading = ref(true);
const saving = ref(false);

// Data do Checklist (Padrão: Hoje)
const checklistDate = ref(new Date());

// Helper para formatar YYYY-MM-DD
const formatDateForAPI = (date) => {
    if (!date) return '';
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

// Helper para formatar HH:MM
const formatTime = (time) => {
    if (!time) return null;
    if (typeof time === 'string') {
        // Se já vem como "HH:MM:SS", pega só HH:MM
        return time.substring(0, 5);
    }
    return time;
};

// --- CARREGAR DADOS ---
const loadChecklistData = async () => {
    loading.value = true;
    try {
        // 1. Pega dados da atribuição (turma/matéria)
        const resAssign = await api.get(`assignments/${assignmentId}/`);
        assignment.value = resAssign.data;

        // 2. Verifica configuração de checklist do segmento
        try {
            const resConfig = await api.get(`checklist-configs/?segment=${assignment.value.classroom_segment}`);
            const configs = resConfig.data.results || resConfig.data;
            checklistConfig.value = Array.isArray(configs) ? configs.find(c => c.requires_checklist) : (configs?.requires_checklist ? configs : null);
        } catch (error) {
            console.error('Erro ao buscar configuração', error);
            checklistConfig.value = null;
        }

        if (!checklistConfig.value) {
            toast.add({ 
                severity: 'warn', 
                summary: 'Atenção', 
                detail: 'Este segmento não requer checklist diário.', 
                life: 5000 
            });
            router.go(-1);
            return;
        }

        // 3. Carrega alunos da turma
        const resEnroll = await api.get(`enrollments/?classroom=${assignment.value.classroom}&page_size=100`);
        
        // 4. Prepara lista inicial
        const initialStudents = resEnroll.data.results.map(s => ({
            id: s.id,
            student_name: s.student_name,
            had_lunch: null,
            had_snack: null,
            checkin_time: null,
            checkout_time: null,
            observation: ''
        }));

        students.value = initialStudents;

        // 5. Verifica se já existe checklist nesta data
        await checkExistingChecklist();

    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- VERIFICAR CHECKLIST EXISTENTE ---
const checkExistingChecklist = async () => {
    if (!assignment.value) return;
    
    const dateStr = formatDateForAPI(checklistDate.value);

    try {
        const res = await api.get(`student-checklists/by_classroom_date/?classroom=${assignment.value.classroom}&date=${dateStr}`);
        const existingRecords = res.data || [];

        students.value.forEach(student => {
            const record = existingRecords.find(r => r.enrollment === student.id);
            
            if (record) {
                student.had_lunch = record.had_lunch;
                student.had_snack = record.had_snack;
                student.checkin_time = formatTime(record.checkin_time);
                student.checkout_time = formatTime(record.checkout_time);
                student.observation = record.observation || '';
            }
        });

        if (existingRecords.length > 0) {
            toast.add({ severity: 'info', summary: 'Registro Encontrado', detail: 'Carregando checklist anterior.', life: 2000 });
        }

    } catch (e) {
        console.error("Erro ao verificar checklist", e);
    }
};

// Observa mudança na data
watch(checklistDate, () => {
    checkExistingChecklist();
});

// --- SALVAR (BULK) ---
const saveChecklist = async () => {
    saving.value = true;
    try {
        const dateStr = formatDateForAPI(checklistDate.value);
        
        // Helper para converter HH:MM para HH:MM:SS
        const formatTimeForAPI = (time) => {
            if (!time) return null;
            if (typeof time === 'string' && time.length === 5) {
                return time + ':00';
            }
            return time;
        };

        const payload = {
            classroom: assignment.value.classroom,
            date: dateStr,
            records: students.value.map(s => ({
                enrollment_id: s.id,
                had_lunch: checklistConfig.value.requires_lunch ? s.had_lunch : null,
                had_snack: checklistConfig.value.requires_snack ? s.had_snack : null,
                checkin_time: checklistConfig.value.requires_checkin ? formatTimeForAPI(s.checkin_time) : null,
                checkout_time: checklistConfig.value.requires_checkout ? formatTimeForAPI(s.checkout_time) : null,
                observation: s.observation || ''
            }))
        };

        await api.post('student-checklists/bulk_save/', payload);
        
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Checklist salvo!', life: 3000 });
        
        // Recarrega para garantir sincronia
        await checkExistingChecklist();
        
    } catch (error) {
        console.error(error);
        const msg = error.response?.data?.error || 'Erro ao salvar checklist.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 3000 });
    } finally {
        saving.value = false;
    }
};

const goBack = () => {
    router.go(-1);
};

onMounted(() => {
    loadChecklistData();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            
            <div class="flex flex-col md:flex-row justify-between items-center mb-4" v-if="assignment && checklistConfig">
                <div class="flex items-center mb-3 md:mb-0">
                    <Button icon="pi pi-arrow-left" class="p-button-text mr-2" @click="goBack" />
                    <div>
                        <span class="block text-xl font-bold">Checklist Diário</span>
                        <span class="text-600">{{ assignment.classroom_name }}</span>
                    </div>
                </div>

                <div class="flex flex-col md:flex-row items-center gap-3">
                    <label class="block font-bold">Data:</label>
                    <DatePicker v-model="checklistDate" dateFormat="dd/mm/yy" showIcon fluid />
                    <Button label="Salvar Checklist" icon="pi pi-check" :loading="saving" @click="saveChecklist" />
                </div>
            </div>

            <div v-if="!checklistConfig && !loading" class="text-center p-4">
                <i class="pi pi-info-circle text-4xl text-600 mb-3"></i>
                <p class="text-lg">Este segmento não requer checklist diário.</p>
            </div>

            <DataTable 
                v-if="checklistConfig"
                :value="students" 
                :loading="loading" 
                responsiveLayout="scroll" 
                size="small" 
                stripedRows
                :scrollable="true"
                scrollHeight="600px"
            >
                <template #empty>Nenhum aluno nesta turma.</template>

                <Column field="student_name" header="Aluno" :frozen="true" style="min-width: 200px" sortable></Column>
                
                <Column v-if="checklistConfig.requires_lunch" header="Almoço" style="width: 120px">
                    <template #body="slotProps">
                        <div class="flex justify-content-center">
                            <ToggleButton 
                                v-model="slotProps.data.had_lunch" 
                                onLabel="Sim" 
                                offLabel="Não"
                                onIcon="pi pi-check" 
                                offIcon="pi pi-times"
                                class="w-full"
                                :class="{
                                    'p-button-success': slotProps.data.had_lunch === true,
                                    'p-button-danger': slotProps.data.had_lunch === false
                                }"
                            />
                        </div>
                    </template>
                </Column>

                <Column v-if="checklistConfig.requires_snack" header="Lanche" style="width: 120px">
                    <template #body="slotProps">
                        <div class="flex justify-content-center">
                            <ToggleButton 
                                v-model="slotProps.data.had_snack" 
                                onLabel="Sim" 
                                offLabel="Não"
                                onIcon="pi pi-check" 
                                offIcon="pi pi-times"
                                class="w-full"
                                :class="{
                                    'p-button-success': slotProps.data.had_snack === true,
                                    'p-button-danger': slotProps.data.had_snack === false
                                }"
                            />
                        </div>
                    </template>
                </Column>

                <Column v-if="checklistConfig.requires_checkin" header="Entrada" style="width: 150px">
                    <template #body="slotProps">
                        <InputText 
                            v-model="slotProps.data.checkin_time" 
                            placeholder="HH:MM"
                            class="w-full"
                            type="time"
                        />
                    </template>
                </Column>

                <Column v-if="checklistConfig.requires_checkout" header="Saída" style="width: 150px">
                    <template #body="slotProps">
                        <InputText 
                            v-model="slotProps.data.checkout_time" 
                            placeholder="HH:MM"
                            class="w-full"
                            type="time"
                        />
                    </template>
                </Column>

                <Column header="Observação" style="min-width: 200px">
                    <template #body="slotProps">
                        <InputText 
                            v-model="slotProps.data.observation" 
                            placeholder="Observações..."
                            class="w-full"
                        />
                    </template>
                </Column>
            </DataTable>
        </div>
    </div>
</template>
