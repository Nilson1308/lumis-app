<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { FilterMatchMode } from '@primevue/core/api';
import api from '@/service/api';

const toast = useToast();
const activities = ref([]);
const loading = ref(true);
const activityDialog = ref(false);
const deleteDialog = ref(false);
const activity = ref({});
const activityToDelete = ref(null);
const filters = ref({ global: { value: null, matchMode: FilterMatchMode.CONTAINS } });

const activityTypes = [
    { label: 'Incluída no Período Integral', value: 'INCLUDED' },
    { label: 'Atividade Paga', value: 'PAID' }
];

const loadData = async () => {
    loading.value = true;
    try {
        const res = await api.get('extra-activities/?page_size=500');
        activities.value = res.data.results || res.data;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar atividades.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

const openNew = () => {
    activity.value = { name: '', description: '', price: 0, activity_type: 'PAID' };
    activityDialog.value = true;
};

const editActivity = (item) => {
    activity.value = { ...item };
    activityDialog.value = true;
};

const saveActivity = async () => {
    if (!activity.value.name) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Informe o nome da atividade.', life: 3000 });
        return;
    }
    try {
        if (activity.value.id) {
            await api.put(`extra-activities/${activity.value.id}/`, activity.value);
            toast.add({ severity: 'success', summary: 'Atualizado', detail: 'Atividade atualizada.', life: 3000 });
        } else {
            await api.post('extra-activities/', activity.value);
            toast.add({ severity: 'success', summary: 'Criado', detail: 'Atividade criada.', life: 3000 });
        }
        activityDialog.value = false;
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: e.response?.data?.detail || 'Erro ao salvar.', life: 3000 });
    }
};

const confirmDelete = (item) => {
    activityToDelete.value = item;
    deleteDialog.value = true;
};

const deleteActivity = async () => {
    try {
        await api.delete(`extra-activities/${activityToDelete.value.id}/`);
        deleteDialog.value = false;
        toast.add({ severity: 'success', summary: 'Removido', detail: 'Atividade excluída.', life: 3000 });
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir.', life: 3000 });
    }
};

const getActivityTypeLabel = (val) => activityTypes.find(t => t.value === val)?.label || val;

onMounted(loadData);
</script>

<template>
    <div class="card">
        <Toast />
        <h3 class="text-2xl font-bold mb-4 text-primary">Atividades Extracurriculares</h3>

        <DataTable
            :value="activities"
            :loading="loading"
            :paginator="true"
            :rows="10"
            :rowsPerPageOptions="[5, 10, 25, 50]"
            dataKey="id"
            filterDisplay="row"
            v-model:filters="filters"
            stripedRows
            responsiveLayout="scroll"
        >
            <template #header>
                <div class="flex justify-between items-center">
                    <span class="text-xl font-semibold">Cadastro de Atividades</span>
                    <Button label="Nova Atividade" icon="pi pi-plus" @click="openNew" />
                </div>
            </template>
            <Column field="name" header="Nome" sortable filterField="name" :showFilterMenu="false">
                <template #filter>
                    <InputText v-model="filters['global'].value" placeholder="Buscar..." class="p-column-filter" />
                </template>
            </Column>
            <Column field="activity_type" header="Tipo" sortable>
                <template #body="{ data }">
                    <Tag :severity="data.activity_type === 'INCLUDED' ? 'success' : 'info'" :value="getActivityTypeLabel(data.activity_type)" />
                </template>
            </Column>
            <Column field="price" header="Valor Mensal">
                <template #body="{ data }">
                    {{ data.activity_type === 'PAID' ? 'R$ ' + parseFloat(data.price || 0).toFixed(2) : '—' }}
                </template>
            </Column>
            <Column header="Ações" :exportable="false" style="min-width: 8rem">
                <template #body="slotProps">
                    <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editActivity(slotProps.data)" v-tooltip.top="'Editar'" />
                    <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDelete(slotProps.data)" v-tooltip.top="'Excluir'" />
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="activityDialog" :header="activity.id ? 'Editar Atividade' : 'Nova Atividade'" :modal="true" :style="{ width: '500px' }" class="p-fluid">
            <div class="mb-2">
                <label class="block font-bold mb-2">Nome</label>
                <InputText v-model="activity.name" required fluid />
            </div>
            <div class="grid grid-cols-12 gap-4 mb-2">
                <div class="col-span-8">
                    <label class="block font-bold mb-2">Tipo</label>
                    <Dropdown v-model="activity.activity_type" :options="activityTypes" optionLabel="label" optionValue="value" fluid />
                </div>
                <div class="col-span-4" v-if="activity.activity_type === 'PAID'">
                    <label class="block mb-2">Valor Mensal (R$)</label>
                    <InputNumber v-model="activity.price" mode="currency" currency="BRL" locale="pt-BR" :minFractionDigits="2" fluid />
                </div>
            </div>
            <div>
                <label class="block mb-2">Descrição</label>
                <Textarea v-model="activity.description" rows="3" fluid />
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="activityDialog = false" />
                <Button label="Salvar" icon="pi pi-check" @click="saveActivity" />
            </template>
        </Dialog>

        <Dialog v-model:visible="deleteDialog" header="Confirmar" :modal="true" :style="{ width: '350px' }">
            <div class="flex items-center gap-3">
                <i class="pi pi-exclamation-triangle" style="font-size: 2rem" />
                <span>Excluir a atividade "{{ activityToDelete?.name }}"?</span>
            </div>
            <template #footer>
                <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                <Button label="Sim" icon="pi pi-check" class="p-button-danger" @click="deleteActivity" />
            </template>
        </Dialog>
    </div>
</template>
