<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const assignments = ref([]);
const assignmentDialog = ref(false);
const deleteAssignmentDialog = ref(false);
const assignment = ref({});
const submitted = ref(false);

// Listas para os Dropdowns
const teachers = ref([]);
const classrooms = ref([]);
const subjects = ref([]);

// --- CARREGAR DADOS ---
const loadData = async () => {
    try {
        // Carrega Atribuições
        const resAssign = await api.get('assignments/?page_size=1000');
        assignments.value = resAssign.data.results;

        // Carrega Dependências (Turmas, Matérias, Professores)
        // Dica: Para professores, idealmente teriamos um endpoint /api/users/?group=Professores
        // Por enquanto, vamos carregar todos users e filtrar no front ou backend se tiver endpoint especifico
        // Se não tiver endpoint de users, use o endpoint que tiver. Vou assumir '/users/'
        const [resClass, resSubj, resUsers] = await Promise.all([
            api.get('classrooms/?page_size=1000'),
            api.get('subjects/?page_size=1000'),
            api.get('users/?group=Professores&page_size=1000')
        ]);

        classrooms.value = resClass.data.results;
        subjects.value = resSubj.data.results;
        
        // Filtra visualmente quem é professor (se a API trouxer groups, melhor ainda)
        // Aqui assumo que o endpoint users traz tudo. 
        // Se sua API de users for diferente, me avise.
        teachers.value = resUsers.data.results.filter(u => 
            u.groups && u.groups.some(g => g.name === 'Professores') || 
            u.is_staff // Fallback
        );

    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados.' });
    }
};

// --- AÇÕES CRUD ---
const openNew = () => {
    assignment.value = {};
    submitted.value = false;
    assignmentDialog.value = true;
};

const editAssignment = (item) => {
    assignment.value = { ...item };
    assignmentDialog.value = true;
};

const confirmDeleteAssignment = (item) => {
    assignment.value = item;
    deleteAssignmentDialog.value = true;
};

const saveAssignment = async () => {
    submitted.value = true;
    if (!assignment.value.teacher || !assignment.value.classroom || !assignment.value.subject) return;

    try {
        if (assignment.value.id) {
            await api.put(`assignments/${assignment.value.id}/`, assignment.value);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Atribuição atualizada' });
        } else {
            await api.post('assignments/', assignment.value);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Atribuição criada' });
        }
        assignmentDialog.value = false;
        assignment.value = {};
        loadData(); // Recarrega a tabela
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao salvar. Verifique se já existe essa combinação.' });
    }
};

const deleteAssignment = async () => {
    try {
        await api.delete(`assignments/${assignment.value.id}/`);
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Removido com sucesso' });
        deleteAssignmentDialog.value = false;
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir' });
    }
};

// Helper para exibir nome no dropdown
const getUserName = (user) => `${user.first_name} ${user.last_name}` || user.username;

onMounted(() => {
    loadData();
});
</script>

<template>
    <div class="card">
        <Toast />
        <Toolbar class="mb-4">
            <template #start>
                <div class="my-2">
                    <Button label="Nova Atribuição" icon="pi pi-plus" class="p-button mr-2" @click="openNew" />
                </div>
            </template>
        </Toolbar>

        <DataTable :value="assignments" responsiveLayout="scroll" :paginator="true" :rows="10">
            <template #header>
                <h5 class="m-0">Atribuição de Aulas</h5>
            </template>

            <Column field="classroom_name" header="Turma" sortable></Column>
            <Column field="subject_name" header="Matéria" sortable></Column>
            <Column field="teacher_name" header="Professor" sortable>
                <template #body="slotProps">
                    <span class="font-bold">{{ slotProps.data.teacher_name }}</span>
                </template>
            </Column>
            
            <Column header="Ações">
                <template #body="slotProps">
                    <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editAssignment(slotProps.data)" />
                    <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDeleteAssignment(slotProps.data)" />
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="assignmentDialog" :style="{ width: '700px' }" header="Detalhes da Atribuição" :modal="true" class="p-fluid">
            
            <div class="mb-2">
                <label class="block font-bold mb-1">Turma</label>
                <Dropdown v-model="assignment.classroom" :options="classrooms" optionLabel="name" optionValue="id" placeholder="Selecione a Turma" filter fluid />
                <small class="p-invalid" v-if="submitted && !assignment.classroom">Turma é obrigatória.</small>
            </div>

            <div class="mb-2">
                <label class="block font-bold mb-1">Matéria</label>
                <Dropdown v-model="assignment.subject" :options="subjects" optionLabel="name" optionValue="id" placeholder="Selecione a Matéria" filter fluid />
                <small class="p-invalid" v-if="submitted && !assignment.subject">Matéria é obrigatória.</small>
            </div>

            <div class="mb-2">
                <label class="block font-bold mb-1">Professor</label>
                <Dropdown v-model="assignment.teacher" :options="teachers" :optionLabel="getUserName" optionValue="id" placeholder="Selecione o Professor" filter fluid />
                <small class="p-invalid" v-if="submitted && !assignment.teacher">Professor é obrigatório.</small>
            </div>

            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="assignmentDialog = false" />
                <Button label="Salvar" icon="pi pi-check" class="p-button-text" @click="saveAssignment" />
            </template>
        </Dialog>

        <Dialog v-model:visible="deleteAssignmentDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
            <div class="flex items-center justify-center">
                <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                <span>Tem certeza que deseja remover esta atribuição?</span>
            </div>
            <template #footer>
                <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteAssignmentDialog = false" />
                <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteAssignment" />
            </template>
        </Dialog>
    </div>
</template>