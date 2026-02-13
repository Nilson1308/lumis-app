<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const contraturnos = ref([]);
const contraturnoDialog = ref(false);
const deleteContraturnoDialog = ref(false);
const contraturno = ref({});
const submitted = ref(false);
const loading = ref(false);

// Listas para os Dropdowns
const classrooms = ref([]);
const teachers = ref([]);

const PERIOD_CHOICES = [
    { label: 'Manhã', value: 'MORNING' },
    { label: 'Tarde', value: 'AFTERNOON' }
];

// --- CARREGAR DEPENDÊNCIAS ---
const loadDependencies = async () => {
    try {
        const [resClass, resUsers] = await Promise.all([
            api.get('classrooms/?page_size=1000'),
            api.get('users/?role=teacher&page_size=1000')
        ]);

        classrooms.value = resClass.data.results;
        teachers.value = resUsers.data.results.map(u => ({
            id: u.id,
            label: u.full_name || u.first_name || u.username || u.username
        }));
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar listas.', life: 3000 });
    }
};

// --- BUSCAR CONTRATURNOS ---
const fetchContraturnos = async () => {
    loading.value = true;
    try {
        const res = await api.get('contraturno-classrooms/?page_size=1000');
        contraturnos.value = res.data.results || res.data;
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar contraturnos.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- ABRIR DIALOG ---
const openNew = () => {
    contraturno.value = {
        classroom: [],
        contraturno_period: 'MORNING',
        teacher: null,
        active: true
    };
    submitted.value = false;
    contraturnoDialog.value = true;
};

const editContraturno = (ct) => {
    contraturno.value = { 
        ...ct,
        classroom: ct.classroom ? [ct.classroom] : [] // Converte para array para compatibilidade com MultiSelect
    };
    contraturnoDialog.value = true;
};

const confirmDelete = (ct) => {
    contraturno.value = ct;
    deleteContraturnoDialog.value = true;
};

// --- SALVAR ---
const saveContraturno = async () => {
    submitted.value = true;

    const classrooms = Array.isArray(contraturno.value.classroom) 
        ? contraturno.value.classroom 
        : (contraturno.value.classroom ? [contraturno.value.classroom] : []);

    if (classrooms.length === 0 || !contraturno.value.teacher || !contraturno.value.contraturno_period) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha todos os campos obrigatórios.', life: 3000 });
        return;
    }

    try {
        if (contraturno.value.id) {
            // Edição: salva apenas uma turma (a primeira do array se houver múltiplas)
            const dataToSave = {
                ...contraturno.value,
                classroom: classrooms[0]
            };
            await api.put(`contraturno-classrooms/${contraturno.value.id}/`, dataToSave);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Contraturno atualizado', life: 3000 });
        } else {
            // Criação: cria um contraturno para cada turma selecionada
            const promises = classrooms.map(classroomId => 
                api.post('contraturno-classrooms/', {
                    classroom: classroomId,
                    contraturno_period: contraturno.value.contraturno_period,
                    teacher: contraturno.value.teacher,
                    active: contraturno.value.active
                })
            );
            
            await Promise.all(promises);
            toast.add({ 
                severity: 'success', 
                summary: 'Sucesso', 
                detail: `${classrooms.length} contraturno(s) criado(s) com sucesso!`, 
                life: 3000 
            });
        }
        contraturnoDialog.value = false;
        contraturno.value = {};
        await fetchContraturnos();
    } catch (error) {
        console.error(error);
        const msg = error.response?.data?.error || error.response?.data?.detail || 'Erro ao salvar.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 3000 });
    }
};

// --- DELETAR ---
const deleteContraturno = async () => {
    try {
        await api.delete(`contraturno-classrooms/${contraturno.value.id}/`);
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Contraturno removido', life: 3000 });
        deleteContraturnoDialog.value = false;
        contraturno.value = {};
        await fetchContraturnos();
    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao remover.', life: 3000 });
    }
};

// --- HELPERS ---
const getPeriodLabel = (value) => {
    return PERIOD_CHOICES.find(p => p.value === value)?.label || value;
};

onMounted(async () => {
    await loadDependencies();
    await fetchContraturnos();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            
            <div class="flex justify-between items-center mb-4">
                <h3>Gestão de Contraturnos</h3>
                <Button label="Novo Contraturno" icon="pi pi-plus" @click="openNew" />
            </div>

            <DataTable :value="contraturnos" :loading="loading" responsiveLayout="scroll" stripedRows>
                <template #empty>Nenhum contraturno cadastrado.</template>

                <Column field="classroom_name" header="Turma" sortable></Column>
                <Column field="contraturno_period_display" header="Período" sortable></Column>
                <Column field="teacher_name" header="Professor Responsável" sortable></Column>
                <Column field="active" header="Ativo" style="width: 10%">
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.active ? 'Sim' : 'Não'" 
                             :severity="slotProps.data.active ? 'success' : 'danger'" />
                    </template>
                </Column>
                <Column header="Ações" style="width: 15%">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2"
                                @click="editContraturno(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded" 
                                @click="confirmDelete(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <!-- Dialog de Edição/Criação -->
            <Dialog v-model:visible="contraturnoDialog" :style="{ width: '450px' }" header="Contraturno" :modal="true" class="p-fluid">
                <div class="field mb-4">
                    <label for="classroom">Turma(s) *</label>
                    <MultiSelect 
                        id="classroom"
                        v-model="contraturno.classroom" 
                        :options="classrooms" 
                        optionLabel="name" 
                        optionValue="id"
                        placeholder="Selecione uma ou mais turmas"
                        :maxSelectedLabels="3"
                        selectedItemsLabel="{0} turmas selecionadas"
                        class="w-full"
                        display="chip"
                    />
                </div>

                <div class="field mb-4">
                    <label for="contraturno_period">Período do Contraturno *</label>
                    <Dropdown 
                        id="contraturno_period"
                        v-model="contraturno.contraturno_period" 
                        :options="PERIOD_CHOICES" 
                        optionLabel="label" 
                        optionValue="value"
                        placeholder="Selecione o período"
                        class="w-full"
                    />
                </div>

                <div class="field mb-4">
                    <label for="teacher">Professor Responsável *</label>
                    <Dropdown 
                        id="teacher"
                        v-model="contraturno.teacher" 
                        :options="teachers" 
                        optionLabel="label" 
                        optionValue="id"
                        placeholder="Selecione o professor"
                        class="w-full"
                    />
                </div>

                <div class="field mb-4">
                    <label class="mb-3 block" for="active">Ativo</label>
                    <InputSwitch id="active" v-model="contraturno.active" />
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="contraturnoDialog = false" />
                    <Button label="Salvar" icon="pi pi-check" @click="saveContraturno" />
                </template>
            </Dialog>

            <!-- Dialog de Confirmação de Exclusão -->
            <Dialog v-model:visible="deleteContraturnoDialog" :style="{ width: '450px' }" header="Confirmar Exclusão" :modal="true">
                <div class="confirmation-content">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span v-if="contraturno">Tem certeza que deseja excluir o contraturno de <b>{{ contraturno.classroom_name }}</b>?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteContraturnoDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-danger" @click="deleteContraturno" />
                </template>
            </Dialog>
        </div>
    </div>
</template>
