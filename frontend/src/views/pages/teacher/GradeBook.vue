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
const periods = ref([]); // Lista de Bimestres
const selectedPeriod = ref(null); // Bimestre Selecionado (ID)
const loading = ref(true);

// --- DIALOG DE NOTA ---
const gradeDialog = ref(false);
const currentStudent = ref({});
const gradeForm = ref({
    name: '',
    value: null,
    weight: 1.0
});

// --- CARREGAR DEPENDÊNCIAS (Períodos) ---
const loadPeriods = async () => {
    try {
        const res = await api.get('periods/');
        periods.value = res.data.results || res.data;

        // Tenta achar o período ativo (is_active = true)
        const active = periods.value.find(p => p.is_active);
        
        if (active) {
            selectedPeriod.value = active.id;
        } else if (periods.value.length > 0) {
            // Se nenhum estiver ativo, pega o último (mais recente)
            selectedPeriod.value = periods.value[periods.value.length - 1].id;
        }
        
        // Só carrega a turma depois de ter um período definido
        if (selectedPeriod.value) {
            loadClassData();
        }
    } catch (e) {
        console.error("Erro ao carregar períodos");
    }
};

// --- CARREGAR DADOS DA TURMA ---
const loadClassData = async () => {
    if (!selectedPeriod.value) return; // Segurança

    console.log("BUSCANDO NOTAS DO PERÍODO ID:", selectedPeriod.value);

    loading.value = true;
    try {
        const resAssign = await api.get(`assignments/${assignmentId}/`);
        assignment.value = resAssign.data;

        const resEnroll = await api.get(`enrollments/?classroom=${assignment.value.classroom}&page_size=100`);
        
        // AGORA FILTRAMOS AS NOTAS PELO PERÍODO SELECIONADO
        const resGrades = await api.get(`grades/?enrollment__classroom=${assignment.value.classroom}&subject=${assignment.value.subject}&period=${selectedPeriod.value}&page_size=1000`);
        
        const allGrades = resGrades.data.results;

        students.value = resEnroll.data.results.map(enrollment => {
            const studentGrades = allGrades.filter(g => g.enrollment === enrollment.id);
            
            // Cálculo Média Ponderada
            let weightedSum = 0;
            let totalWeight = 0;
            studentGrades.forEach(g => {
                const val = parseFloat(g.value);
                const w = parseFloat(g.weight || 1);
                weightedSum += (val * w);
                totalWeight += w;
            });

            const avg = totalWeight > 0 ? (weightedSum / totalWeight).toFixed(1) : '-';

            return {
                ...enrollment,
                grades: studentGrades,
                average: avg
            };
        });

    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar diário.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// Se trocar o bimestre no dropdown, recarrega a tabela
watch(selectedPeriod, () => {
    loadClassData();
});

// --- AÇÕES ---
const openGradeDialog = (studentWrapper) => {
    currentStudent.value = studentWrapper;
    gradeForm.value = { name: '', value: null, weight: 1.0 };
    gradeDialog.value = true;
};

const saveGrade = async () => {
    if (!gradeForm.value.name || gradeForm.value.value === null) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha os dados.', life: 3000 });
        return;
    }

    try {
        const payload = {
            enrollment: currentStudent.value.id,
            subject: assignment.value.subject,
            name: gradeForm.value.name,
            value: gradeForm.value.value,
            weight: gradeForm.value.weight,
            period: selectedPeriod.value // <--- IMPORTANTE: Salva no bimestre atual
        };

        await api.post('grades/', payload);
        
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Nota lançada!', life: 3000 });
        gradeDialog.value = false;
        loadClassData();
        
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar nota.', life: 3000 });
    }
};

const goBack = () => {
    router.push({ name: 'my-classes' });
};

onMounted(() => {
    loadPeriods(); // Começa carregando os bimestres
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />

            <div class="flex flex-column md:flex-row justify-content-between align-items-center mb-4" v-if="assignment">
                <div class="flex align-items-center mb-3 md:mb-0">
                    <Button icon="pi pi-arrow-left" class="p-button-text mr-2" @click="goBack" />
                    <div>
                        <span class="block text-xl font-bold">{{ assignment.subject_name }}</span>
                        <span class="text-600">{{ assignment.classroom_name }}</span>
                    </div>
                </div>
                
                <div class="flex align-items-center gap-3">
                    <span class="font-bold">Período:</span>
                    <Dropdown 
                        v-model="selectedPeriod" 
                        :options="periods" 
                        optionLabel="name" 
                        optionValue="id" 
                        placeholder="Selecione..." 
                        class="w-12rem"
                    />
                </div>
            </div>

            <DataTable :value="students" :loading="loading" responsiveLayout="scroll" stripedRows>
                <template #empty>Nenhum aluno nesta turma.</template>

                <Column field="student_name" header="Aluno" sortable style="min-width: 200px"></Column>
                
                <Column header="Avaliações do Bimestre">
                    <template #body="slotProps">
                        <div class="flex gap-2 flex-wrap">
                            <span v-for="grade in slotProps.data.grades" :key="grade.id">
                                <Tag 
                                    :value="grade.value" 
                                    :severity="grade.value >= 6 ? 'success' : 'danger'" 
                                    v-tooltip.top="`${grade.name} (Peso: ${grade.weight})`" 
                                />
                            </span>
                            <span v-if="slotProps.data.grades.length === 0" class="text-500 text-sm italic">Sem notas neste bimestre</span>
                        </div>
                    </template>
                </Column>

                <Column field="average" header="Média Bim." style="width: 100px; text-align: center">
                    <template #body="slotProps">
                        <strong :class="{'text-red-500': slotProps.data.average < 6 && slotProps.data.average !== '-'}">
                            {{ slotProps.data.average }}
                        </strong>
                    </template>
                </Column>

                <Column header="Ação" style="width: 80px">
                    <template #body="slotProps">
                        <Button icon="pi pi-plus" class="p-button-rounded p-button-sm" v-tooltip.top="'Lançar Nota'" @click="openGradeDialog(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="gradeDialog" header="Lançar Nota" :modal="true" :style="{ width: '400px' }">
                <div class="p-fluid grid formgrid">
                    <div class="field col-12">
                        <label>Nome da Avaliação</label>
                        <InputText v-model="gradeForm.name" placeholder="Ex: Trabalho, Prova..." autofocus />
                    </div>
                    
                    <div class="field col-6">
                        <label>Nota (0-10)</label>
                        <InputNumber v-model="gradeForm.value" mode="decimal" :min="0" :max="10" :minFractionDigits="1" :maxFractionDigits="2" showButtons />
                    </div>

                    <div class="field col-6">
                        <label>Peso</label>
                        <InputNumber v-model="gradeForm.weight" mode="decimal" :min="0.1" :max="10" :step="0.5" showButtons suffix="x" />
                    </div>
                </div>
                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="gradeDialog = false" />
                    <Button label="Salvar" icon="pi pi-check" @click="saveGrade" />
                </template>
            </Dialog>

        </div>
    </div>
</template>