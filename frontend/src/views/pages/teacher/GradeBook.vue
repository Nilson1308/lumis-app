<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const route = useRoute();
const router = useRouter();
const toast = useToast();

// ID da Atribuição vindo da URL (ex: /teacher/classes/5/gradebook)
const assignmentId = route.params.id;

// --- ESTADOS ---
const assignment = ref(null); // Dados da turma/matéria atual
const students = ref([]);     // Lista de alunos da turma
const loading = ref(true);

// --- DIALOG DE NOTA ---
const gradeDialog = ref(false);
const currentStudent = ref({}); // Aluno selecionado para dar nota
const gradeForm = ref({
    name: '',
    value: null,
    weight: 1.0 // Padrão é 1
});

// --- CARREGAR DADOS ---
const loadClassData = async () => {
    loading.value = true;
    try {
        // 1. Busca detalhes da Atribuição (para saber qual é a turma e a matéria)
        const resAssign = await api.get(`assignments/${assignmentId}/`);
        assignment.value = resAssign.data;

        // 2. Busca os alunos matriculados nesta turma
        // Filtramos enrollments pela turma da atribuição
        const resEnroll = await api.get(`enrollments/?classroom=${assignment.value.classroom}&page_size=100`);
        
        // 3. Busca as notas já lançadas para esta turma e matéria
        const resGrades = await api.get(`grades/?enrollment__classroom=${assignment.value.classroom}&subject=${assignment.value.subject}&page_size=1000`);
        const allGrades = resGrades.data.results;

        // 4. Mágica: Cruzar Alunos com suas Notas para exibir na tela
        students.value = resEnroll.data.results.map(enrollment => {
            // Filtra notas apenas deste aluno
            const studentGrades = allGrades.filter(g => g.enrollment === enrollment.id);

            // --- CÁLCULO DE MÉDIA PONDERADA ---
            let weightedSum = 0; // Soma das (Nota * Peso)
            let totalWeight = 0; // Soma dos Pesos

            studentGrades.forEach(g => {
                const val = parseFloat(g.value);
                const w = parseFloat(g.weight || 1); // Garante peso 1 se vier nulo
                
                weightedSum += (val * w);
                totalWeight += w;
            });

            // Evita divisão por zero
            const avg = totalWeight > 0 ? (weightedSum / totalWeight).toFixed(1) : '-';

            return {
                ...enrollment, 
                grades: studentGrades, 
                average: avg
            };
        });

    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar diário.', life: 3000 });
        console.error(error);
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES ---
const openGradeDialog = (studentWrapper) => {
    currentStudent.value = studentWrapper;
    gradeForm.value = { name: '', value: null, weight: 1.0 }; // Reseta com peso 1
    gradeDialog.value = true;
};

const saveGrade = async () => {
    if (!gradeForm.value.name || gradeForm.value.value === null) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha nome e nota.', life: 3000 });
        return;
    }

    try {
        const payload = {
            enrollment: currentStudent.value.id,
            subject: assignment.value.subject,
            name: gradeForm.value.name,
            value: gradeForm.value.value,
            weight: gradeForm.value.weight // <--- Envia o peso
        };

        await api.post('grades/', payload);
        
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Nota lançada!', life: 3000 });
        gradeDialog.value = false;
        loadClassData(); // Recarrega tudo para atualizar a média e lista
        
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar nota.', life: 3000 });
    }
};

const goBack = () => {
    router.push({ name: 'my-classes' });
};

onMounted(() => {
    loadClassData();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />

            <div class="flex justify-content-between align-items-center mb-4" v-if="assignment">
                <div>
                    <Button icon="pi pi-arrow-left" class="p-button-text mr-2" @click="goBack" />
                    <span class="text-xl font-bold align-middle">{{ assignment.subject_name }} - {{ assignment.classroom_name }}</span>
                </div>
                <div>
                    <Tag :value="students.length + ' Alunos'" severity="info" />
                </div>
            </div>

            <DataTable :value="students" :loading="loading" responsiveLayout="scroll">
                <template #empty>Nenhum aluno nesta turma.</template>

                <Column field="student_name" header="Aluno" sortable></Column>
                
                <Column header="Avaliações">
                    <template #body="slotProps">
                        <div class="flex gap-2">
                            <span v-for="grade in slotProps.data.grades" :key="grade.id">
                                <Tag 
                                    :value="grade.value" 
                                    :severity="grade.value >= 6 ? 'success' : 'danger'" 
                                    v-tooltip.top="`${grade.name} (Peso: ${grade.weight})`" 
                                />
                            </span>
                            <span v-if="slotProps.data.grades.length === 0" class="text-500 text-sm italic">Sem notas</span>
                        </div>
                    </template>
                </Column>

                <Column field="average" header="Média Atual" style="width: 10%">
                    <template #body="slotProps">
                        <strong :class="{'text-red-500': slotProps.data.average < 6 && slotProps.data.average !== '-'}">
                            {{ slotProps.data.average }}
                        </strong>
                    </template>
                </Column>

                <Column header="Ação" style="width: 10%">
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
                        <small class="text-500">Padrão: 1.0</small>
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