<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();

// --- ESTADOS ---
const observations = ref([]);
const assignments = ref([]); // Lista de Aulas (Professor + Turma) para selecionar
const observation = ref({});
const loading = ref(true);
const observationDialog = ref(false);
const deleteDialog = ref(false);
const submitted = ref(false);

// --- CARREGAR DADOS ---
const loadDependencies = async () => {
    try {
        // Carrega as Aulas (Atribuições) para o dropdown
        // Ex: "Prof. João - Matemática - 6º A"
        const resAssign = await api.get('assignments/?page_size=1000');
        assignments.value = resAssign.data.results.map(a => ({
            id: a.id,
            label: `${a.teacher_name} - ${a.subject_name} (${a.classroom_name})`
        }));
        
        fetchObservations();
    } catch (e) {
        console.error("Erro ao carregar dependências");
    }
};

const fetchObservations = async () => {
    loading.value = true;
    try {
        const response = await api.get('class-observations/');
        observations.value = response.data.results;
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar observações', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES ---
const openNew = () => {
    observation.value = {
        date: new Date(),
        pontuality: 3,
        class_control: 3,
        planning: 3,
        student_engagement: 3,
        feedback_given: false
    };
    submitted.value = false;
    observationDialog.value = true;
};

const editObservation = (item) => {
    observation.value = { ...item };
    // Ajusta data string para objeto Date
    if (observation.value.date) {
        observation.value.date = new Date(observation.value.date);
    }
    observationDialog.value = true;
};

const confirmDelete = (item) => {
    observation.value = item;
    deleteDialog.value = true;
};

// --- SALVAR ---
const saveObservation = async () => {
    submitted.value = true;

    if (observation.value.assignment && observation.value.date) {
        // Formatar data para YYYY-MM-DD
        const payload = { ...observation.value };
        if (payload.date instanceof Date) {
            const offset = payload.date.getTimezoneOffset();
            payload.date = new Date(payload.date.getTime() - (offset*60*1000)).toISOString().split('T')[0];
        }

        try {
            if (observation.value.id) {
                await api.put(`class-observations/${observation.value.id}/`, payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Observação atualizada', life: 3000 });
            } else {
                await api.post('class-observations/', payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Observação criada', life: 3000 });
            }
            observationDialog.value = false;
            fetchObservations();
        } catch (error) {
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar.', life: 3000 });
        }
    }
};

const deleteObservation = async () => {
    try {
        await api.delete(`class-observations/${observation.value.id}/`);
        deleteDialog.value = false;
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Removido com sucesso', life: 3000 });
        fetchObservations();
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao remover', life: 3000 });
    }
};

onMounted(() => {
    loadDependencies();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            <Toolbar class="mb-4">
                <template v-slot:start>
                    <div class="my-2">
                        <Button label="Nova Observação" icon="pi pi-plus" class="p-button-success mr-2" @click="openNew" />
                    </div>
                </template>
            </Toolbar>

            <DataTable :value="observations" :loading="loading" responsiveLayout="scroll" :paginator="true" :rows="10">
                <template #header>Histórico de Observações</template>
                <template #empty>Nenhuma observação registrada.</template>

                <Column field="date" header="Data" sortable>
                    <template #body="slotProps">
                        {{ new Date(slotProps.data.date).toLocaleDateString('pt-BR') }}
                    </template>
                </Column>
                <Column field="teacher_name" header="Professor" sortable></Column>
                <Column field="classroom_name" header="Turma" sortable></Column>
                <Column field="coordinator_name" header="Observador"></Column>
                
                <Column field="feedback_given" header="Feedback">
                    <template #body="slotProps">
                        <Tag :severity="slotProps.data.feedback_given ? 'success' : 'warning'" :value="slotProps.data.feedback_given ? 'Realizado' : 'Pendente'" />
                    </template>
                </Column>

                <Column header="Ações">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded p-button-success mr-2" @click="editObservation(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded p-button-warning" @click="confirmDelete(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="observationDialog" :style="{ width: '600px' }" header="Ficha de Observação" :modal="true" class="p-fluid">
                
                <div class="field">
                    <label class="font-bold">Aula Observada (Professor / Turma)</label>
                    <Dropdown 
                        v-model="observation.assignment" 
                        :options="assignments" 
                        optionLabel="label" 
                        optionValue="id" 
                        placeholder="Selecione..." 
                        filter
                        autofocus
                        :class="{ 'p-invalid': submitted && !observation.assignment }"
                    />
                    <small class="p-error" v-if="submitted && !observation.assignment">Obrigatório.</small>
                </div>

                <div class="field">
                    <label class="font-bold">Data</label>
                    <Calendar v-model="observation.date" dateFormat="dd/mm/yy" showIcon />
                </div>

                <div class="formgrid grid">
                    <div class="field col-6">
                        <label>Pontualidade</label>
                        <Rating v-model="observation.pontuality" :cancel="false" />
                    </div>
                    <div class="field col-6">
                        <label>Domínio de Classe</label>
                        <Rating v-model="observation.class_control" :cancel="false" />
                    </div>
                    <div class="field col-6">
                        <label>Planejamento</label>
                        <Rating v-model="observation.planning" :cancel="false" />
                    </div>
                    <div class="field col-6">
                        <label>Engajamento dos Alunos</label>
                        <Rating v-model="observation.student_engagement" :cancel="false" />
                    </div>
                </div>

                <div class="field mt-3">
                    <label class="font-bold">Pontos Fortes</label>
                    <Textarea v-model="observation.strong_points" rows="3" autoResize />
                </div>

                <div class="field">
                    <label class="font-bold">Pontos a Melhorar</label>
                    <Textarea v-model="observation.points_to_improve" rows="3" autoResize />
                </div>

                <div class="field-checkbox">
                    <Checkbox id="feedback" v-model="observation.feedback_given" :binary="true" />
                    <label for="feedback">O feedback já foi passado ao professor?</label>
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="observationDialog = false" />
                    <Button label="Salvar Registro" icon="pi pi-check" @click="saveObservation" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-items-center justify-content-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span>Apagar este registo de observação?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteObservation" />
                </template>
            </Dialog>
        </div>
    </div>
</template>