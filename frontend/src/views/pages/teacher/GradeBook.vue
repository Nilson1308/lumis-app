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
const periods = ref([]);
const selectedPeriod = ref(null);
const loading = ref(true);

// --- DIALOG DE NOTA (Criação e Edição) ---
const gradeDialog = ref(false);
const currentStudent = ref({}); // Aluno sendo editado/lançado
const currentGradeId = ref(null); // Se tiver ID, é edição. Se null, é criação.
const gradeForm = ref({
    name: '',
    value: null,
    weight: 1.0
});

// --- DIALOG DE DETALHES (Lista de Notas) ---
const detailsDialog = ref(false);
const selectedStudentGrades = ref([]); // Lista de notas para exibir no dialog de detalhes

// --- CARREGAR DEPENDÊNCIAS ---
const loadPeriods = async () => {
    try {
        const res = await api.get('periods/');
        periods.value = res.data.results || res.data;
        const active = periods.value.find(p => p.is_active);
        
        if (active) {
            selectedPeriod.value = active.id;
        } else if (periods.value.length > 0) {
            selectedPeriod.value = periods.value[periods.value.length - 1].id;
        }
        
        if (selectedPeriod.value) {
            loadClassData();
        }
    } catch (e) {
        console.error("Erro ao carregar períodos");
    }
};

const loadClassData = async () => {
    if (!selectedPeriod.value) return;

    loading.value = true;
    try {
        // 1. Carrega dados da Atribuição (Matéria/Turma)
        if (!assignment.value) {
            const resAssign = await api.get(`assignments/${assignmentId}/`);
            assignment.value = resAssign.data;
        }

        // 2. Carrega Alunos
        const resEnroll = await api.get(`enrollments/?classroom=${assignment.value.classroom}&page_size=100`);
        
        // 3. Carrega Notas do Período
        const resGrades = await api.get(`grades/?enrollment__classroom=${assignment.value.classroom}&subject=${assignment.value.subject}&period=${selectedPeriod.value}&page_size=1000`);
        
        const allGrades = resGrades.data.results;

        // 4. Cruza os dados
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

        // Se o dialog de detalhes estiver aberto, atualiza a lista dele também
        if (detailsDialog.value && currentStudent.value.id) {
            const updatedStudent = students.value.find(s => s.id === currentStudent.value.id);
            if (updatedStudent) {
                selectedStudentGrades.value = updatedStudent.grades;
            }
        }

    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar diário.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

watch(selectedPeriod, () => {
    loadClassData();
});

// --- AÇÕES PRINCIPAIS ---

// 1. Abrir Dialog para NOVA Nota
const openNewGradeDialog = (studentWrapper) => {
    currentStudent.value = studentWrapper;
    currentGradeId.value = null; // Modo Criação
    gradeForm.value = { name: '', value: null, weight: 1.0 };
    gradeDialog.value = true;
};

// 2. Abrir Dialog de DETALHES (Ver todas as notas)
const openDetailsDialog = (studentWrapper) => {
    currentStudent.value = studentWrapper;
    selectedStudentGrades.value = studentWrapper.grades;
    detailsDialog.value = true;
};

// 3. Abrir Dialog de EDIÇÃO (Vindo de dentro dos detalhes)
const openEditGradeDialog = (grade) => {
    currentGradeId.value = grade.id; // Modo Edição
    gradeForm.value = { 
        name: grade.name, 
        value: parseFloat(grade.value), 
        weight: parseFloat(grade.weight) 
    };
    gradeDialog.value = true; // Reusa o mesmo dialog de formulário
};

// 4. Salvar (Create ou Update)
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
            period: selectedPeriod.value
        };

        if (currentGradeId.value) {
            // EDIÇÃO (PATCH)
            await api.patch(`grades/${currentGradeId.value}/`, payload);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Nota atualizada!', life: 3000 });
        } else {
            // CRIAÇÃO (POST)
            await api.post('grades/', payload);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Nota lançada!', life: 3000 });
        }
        
        gradeDialog.value = false;
        loadClassData(); // Recarrega tudo para atualizar médias e listas
        
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar nota.', life: 3000 });
    }
};

// 5. Excluir Nota
const deleteGrade = async (gradeId) => {
    if(!confirm("Tem certeza que deseja excluir esta nota?")) return;

    try {
        await api.delete(`grades/${gradeId}/`);
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Nota removida.', life: 3000 });
        loadClassData();
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir.', life: 3000 });
    }
};

const goBack = () => {
    router.push({ name: 'my-classes' });
};

onMounted(() => {
    loadPeriods();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />

            <div class="flex flex-col md:flex-row justify-between items-center mb-4" v-if="assignment">
                <div class="flex mb-3 md:mb-0">
                    <Button icon="pi pi-arrow-left" class="p-button-text mr-2" @click="goBack" />
                    <div>
                        <span class="block text-xl font-bold">{{ assignment.subject_name }}</span>
                        <span class="text-600">{{ assignment.classroom_name }}</span>
                    </div>
                </div>
                
                <div class="flex items-center gap-3">
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
                
                <Column header="Avaliações (Resumo)">
                    <template #body="slotProps">
                        <div class="flex gap-2 flex-wrap items-center">
                            <span v-for="grade in slotProps.data.grades.slice(0, 3)" :key="grade.id">
                                <Tag 
                                    :value="grade.value" 
                                    :severity="grade.value >= 6 ? 'success' : 'danger'" 
                                    v-tooltip.top="`${grade.name} (Peso: ${grade.weight})`" 
                                />
                            </span>
                            
                            <span v-if="slotProps.data.grades.length > 3" class="text-xs text-500 font-bold">
                                +{{ slotProps.data.grades.length - 3 }}
                            </span>

                            <span v-if="slotProps.data.grades.length === 0" class="text-500 text-sm italic">
                                -
                            </span>
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

                <Column header="Ações" style="width: 120px; text-align: right">
                    <template #body="slotProps">
                        <Button icon="pi pi-list" class="p-button-rounded p-button-secondary p-button-text mr-1" v-tooltip.top="'Ver Detalhes / Editar'" @click="openDetailsDialog(slotProps.data)" />
                        <Button icon="pi pi-plus" class="p-button-rounded p-button-sm" v-tooltip.top="'Lançar Nova Nota'" @click="openNewGradeDialog(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="gradeDialog" :header="currentGradeId ? 'Editar Nota' : 'Lançar Nota'" :modal="true" :style="{ width: '400px' }">
                <div class="grid grid-cols-12 gap-6">
                    <div class="col-span-12">
                        <label class="font-bold block mb-2">Nome da Avaliação</label>
                        <InputText v-model="gradeForm.name" placeholder="Ex: Trabalho, Prova..." autofocus fluid />
                    </div>
                    
                    <div class="col-span-6">
                        <label class="font-bold block mb-2">Nota (0-10)</label>
                        <InputNumber v-model="gradeForm.value" mode="decimal" :min="0" :max="10" :minFractionDigits="1" :maxFractionDigits="2" showButtons fluid />
                    </div>

                    <div class="col-span-6">
                        <label class="font-bold block mb-2">Peso</label>
                        <InputNumber v-model="gradeForm.weight" mode="decimal" :min="0.1" :max="10" :step="0.5" showButtons suffix="x" fluid />
                    </div>
                </div>
                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="gradeDialog = false" />
                    <Button label="Salvar" icon="pi pi-check" @click="saveGrade" />
                </template>
            </Dialog>

            <Dialog v-model:visible="detailsDialog" :header="`Notas de: ${currentStudent.student_name}`" :modal="true" :style="{ width: '600px' }">
                <DataTable :value="selectedStudentGrades" stripedRows responsiveLayout="scroll">
                    <template #empty>Nenhuma nota lançada neste bimestre.</template>
                    
                    <Column field="name" header="Avaliação"></Column>
                    <Column field="value" header="Nota" style="width: 100px">
                        <template #body="slotProps">
                            <Tag :value="slotProps.data.value" :severity="slotProps.data.value >= 6 ? 'success' : 'danger'" />
                        </template>
                    </Column>
                    <Column field="weight" header="Peso" style="width: 80px"></Column>
                    <Column field="date" header="Data" style="width: 100px">
                        <template #body="slotProps">
                           {{ new Date(slotProps.data.date).toLocaleDateString('pt-BR') }}
                        </template>
                    </Column>
                    <Column header="Ações" style="width: 100px">
                        <template #body="slotProps">
                            <Button icon="pi pi-pencil" class="p-button-rounded p-button-text p-button-warning mr-1" @click="openEditGradeDialog(slotProps.data)" v-tooltip="'Editar'" />
                            <Button icon="pi pi-trash" class="p-button-rounded p-button-text p-button-danger" @click="deleteGrade(slotProps.data.id)" v-tooltip="'Excluir'" />
                        </template>
                    </Column>
                </DataTable>
                <div class="mt-4 text-right">
                    <span class="text-lg mr-2">Média Parcial:</span>
                    <strong class="text-xl">{{ currentStudent.average }}</strong>
                </div>
            </Dialog>

        </div>
    </div>
</template>