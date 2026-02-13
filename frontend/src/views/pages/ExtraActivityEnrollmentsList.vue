<script setup>
import { ref, onMounted, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import { FilterMatchMode } from '@primevue/core/api';
import api from '@/service/api';

const toast = useToast();
const enrollments = ref([]);
const students = ref([]);
const activities = ref([]);
const loading = ref(false);
const enrollmentDialog = ref(false);
const attendanceDialog = ref(false);
const deleteDialog = ref(false);
const enrollment = ref({});
const selectedEnrollment = ref(null);
const enrollmentToDelete = ref(null);
const filters = ref({ global: { value: null, matchMode: FilterMatchMode.CONTAINS } });

const filterStudent = ref(null);
const filterActivity = ref(null);

const attendanceDate = ref(null);
const attendancePresent = ref(true);
const attendances = ref([]);

const loadEnrollments = async () => {
    loading.value = true;
    try {
        let url = 'extra-activity-enrollments/?page_size=500';
        if (filterStudent.value) url += `&student=${filterStudent.value}`;
        if (filterActivity.value) url += `&activity=${filterActivity.value}`;
        const res = await api.get(url);
        enrollments.value = res.data.results || res.data;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar matrículas.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

const loadDependencies = async () => {
    try {
        const [sRes, aRes] = await Promise.all([
            api.get('students/?page_size=1000'),
            api.get('extra-activities/?page_size=500')
        ]);
        students.value = sRes.data.results || sRes.data;
        activities.value = aRes.data.results || aRes.data;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados.', life: 3000 });
    }
};

watch([filterStudent, filterActivity], loadEnrollments);

const openNew = () => {
    const today = new Date();
    enrollment.value = {
        student: null,
        activity: null,
        start_date: today,
        end_date: null,
        active: true
    };
    enrollmentDialog.value = true;
};

const editEnrollment = (item) => {
    const start = item.start_date ? new Date(item.start_date + 'T00:00:00') : new Date();
    const end = item.end_date ? new Date(item.end_date + 'T00:00:00') : null;
    enrollment.value = {
        ...item,
        start_date: start,
        end_date: end,
        active: item.active !== false
    };
    enrollmentDialog.value = true;
};

const saveEnrollment = async () => {
    if (!enrollment.value.student || !enrollment.value.activity || !enrollment.value.start_date) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha aluno, atividade e data de início.', life: 3000 });
        return;
    }
    try {
        const startStr = enrollment.value.start_date instanceof Date
            ? enrollment.value.start_date.toISOString().split('T')[0]
            : enrollment.value.start_date;
        const endStr = enrollment.value.end_date
            ? (enrollment.value.end_date instanceof Date ? enrollment.value.end_date.toISOString().split('T')[0] : enrollment.value.end_date)
            : null;
        const payload = {
            student: enrollment.value.student,
            activity: enrollment.value.activity,
            start_date: startStr,
            end_date: endStr,
            active: enrollment.value.active !== false
        };
        if (enrollment.value.id) {
            await api.put(`extra-activity-enrollments/${enrollment.value.id}/`, payload);
            toast.add({ severity: 'success', summary: 'Atualizado', detail: 'Matrícula atualizada.', life: 3000 });
        } else {
            await api.post('extra-activity-enrollments/', payload);
            toast.add({ severity: 'success', summary: 'Criado', detail: 'Matrícula criada.', life: 3000 });
        }
        enrollmentDialog.value = false;
        loadEnrollments();
    } catch (e) {
        const msg = e.response?.data?.activity?.[0] || e.response?.data?.detail || 'Erro ao salvar.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 3000 });
    }
};

const openAttendance = (item) => {
    selectedEnrollment.value = item;
    attendanceDate.value = new Date();
    attendancePresent.value = true;
    loadAttendances();
    attendanceDialog.value = true;
};

const loadAttendances = async () => {
    if (!selectedEnrollment.value?.id) return;
    try {
        const res = await api.get(`extra-activity-attendances/?enrollment=${selectedEnrollment.value.id}&page_size=100`);
        attendances.value = res.data.results || res.data;
    } catch (e) {
        attendances.value = [];
    }
};

const saveAttendance = async () => {
    if (!selectedEnrollment.value?.id || !attendanceDate.value) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Informe a data.', life: 3000 });
        return;
    }
    try {
        // Converte a data para o formato YYYY-MM-DD
        let dateStr;
        if (attendanceDate.value instanceof Date) {
            const year = attendanceDate.value.getFullYear();
            const month = String(attendanceDate.value.getMonth() + 1).padStart(2, '0');
            const day = String(attendanceDate.value.getDate()).padStart(2, '0');
            dateStr = `${year}-${month}-${day}`;
        } else if (typeof attendanceDate.value === 'string') {
            // Se já estiver no formato YYYY-MM-DD, usa direto
            if (attendanceDate.value.match(/^\d{4}-\d{2}-\d{2}$/)) {
                dateStr = attendanceDate.value;
            } else if (attendanceDate.value.includes('/')) {
                // Se vier no formato brasileiro (DD/MM/YYYY), converte
                const [day, month, year] = attendanceDate.value.split('/');
                dateStr = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
            } else {
                // Tenta usar ISO string
                dateStr = new Date(attendanceDate.value).toISOString().split('T')[0];
            }
        } else {
            dateStr = new Date(attendanceDate.value).toISOString().split('T')[0];
        }
        
        await api.post('extra-activity-attendances/', {
            enrollment: selectedEnrollment.value.id,
            date: dateStr,
            present: attendancePresent.value
        });
        toast.add({ severity: 'success', summary: 'Salvo', detail: 'Presença registrada.', life: 3000 });
        loadAttendances();
        // Limpa os campos após salvar
        attendanceDate.value = new Date();
        attendancePresent.value = true;
    } catch (e) {
        const msg = e.response?.data?.date?.[0] || e.response?.data?.detail || e.response?.data?.non_field_errors?.[0] || 'Erro ao salvar.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 3000 });
    }
};

const deleteAttendance = async (attendanceId) => {
    try {
        await api.delete(`extra-activity-attendances/${attendanceId}/`);
        toast.add({ severity: 'success', summary: 'Removido', detail: 'Lançamento excluído.', life: 3000 });
        loadAttendances();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir lançamento.', life: 3000 });
    }
};

const confirmDelete = (item) => {
    enrollmentToDelete.value = item;
    deleteDialog.value = true;
};

const deleteEnrollment = async () => {
    try {
        await api.delete(`extra-activity-enrollments/${enrollmentToDelete.value.id}/`);
        deleteDialog.value = false;
        toast.add({ severity: 'success', summary: 'Removido', detail: 'Matrícula excluída.', life: 3000 });
        loadEnrollments();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir.', life: 3000 });
    }
};

const formatDate = (d) => d ? new Date(d + 'T00:00:00').toLocaleDateString('pt-BR') : '—';

onMounted(() => {
    loadDependencies();
    loadEnrollments();
});
</script>

<template>
    <div class="card">
        <Toast />
        <h2 class="text-2xl font-bold mb-4 text-primary">Matrículas em Atividades Extras</h2>

        <div class="grid grid-cols-12 gap-4 mb-4">
            <div class="col-span-12 md:col-span-4">
                <label class="block font-bold mb-2">Filtrar por Aluno</label>
                <Dropdown
                    v-model="filterStudent"
                    :options="students"
                    optionLabel="name"
                    optionValue="id"
                    placeholder="Todos"
                    showClear
                    filter
                    class="w-full"
                />
            </div>
            <div class="col-span-12 md:col-span-4">
                <label class="block font-bold mb-2">Filtrar por Atividade</label>
                <Dropdown
                    v-model="filterActivity"
                    :options="activities"
                    optionLabel="name"
                    optionValue="id"
                    placeholder="Todas"
                    showClear
                    filter
                    class="w-full"
                />
            </div>
        </div>

        <DataTable
            :value="enrollments"
            :loading="loading"
            :paginator="true"
            :rows="10"
            dataKey="id"
            filterDisplay="row"
            v-model:filters="filters"
            stripedRows
            responsiveLayout="scroll"
        >
            <template #header>
                <div class="flex justify-between items-center">
                    <span class="text-xl font-semibold">Lista de Matrículas</span>
                    <Button label="Nova Matrícula" icon="pi pi-plus" @click="openNew" />
                </div>
            </template>
            <Column field="student_name" header="Aluno" sortable>
                <template #body="{ data }">{{ data.student_name }}</template>
            </Column>
            <Column field="activity_name" header="Atividade" sortable>
                <template #body="{ data }">
                    <Tag :severity="data.activity_type === 'INCLUDED' ? 'success' : 'info'" :value="data.activity_name" />
                </template>
            </Column>
            <Column header="Início">
                <template #body="{ data }">{{ formatDate(data.start_date) }}</template>
            </Column>
            <Column header="Fim">
                <template #body="{ data }">{{ formatDate(data.end_date) }}</template>
            </Column>
            <Column field="active" header="Ativo">
                <template #body="{ data }">
                    <i :class="data.active ? 'pi pi-check text-green-600' : 'pi pi-times text-red-600'" />
                </template>
            </Column>
            <Column header="Ações" :exportable="false" style="min-width: 10rem">
                <template #body="slotProps">
                    <Button icon="pi pi-calendar" class="p-button-rounded mr-2" @click="openAttendance(slotProps.data)" v-tooltip.top="'Presença'" />
                    <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editEnrollment(slotProps.data)" v-tooltip.top="'Editar'" />
                    <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDelete(slotProps.data)" v-tooltip.top="'Excluir'" />
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="enrollmentDialog" :header="enrollment.id ? 'Editar Matrícula' : 'Nova Matrícula'" :modal="true" :style="{ width: '500px' }" class="p-fluid">
            <div class="mb-2">
                <label class="block font-bold mb-2">Aluno *</label>
                <Dropdown v-model="enrollment.student" :options="students" optionLabel="name" optionValue="id" placeholder="Selecione" filter fluid />
            </div>
            <div class="mb-2">
                <label class="block font-bold mb-2">Atividade *</label>
                <Dropdown v-model="enrollment.activity" :options="activities" optionLabel="name" optionValue="id" placeholder="Selecione" filter fluid />
            </div>
            <div class="grid grid-cols-12 gap-4 mb-3">
                <div class="col-span-6">
                    <label class="block font-bold mb-2">Data de Início *</label>
                    <Calendar v-model="enrollment.start_date" dateFormat="dd/mm/yy" showIcon fluid />
                </div>
                <div class="col-span-6">
                    <label class="block mb-2">Data de Término</label>
                    <Calendar v-model="enrollment.end_date" dateFormat="dd/mm/yy" showIcon fluid />
                </div>
            </div>
            <div class="flex items-center gap-2">
                <Checkbox v-model="enrollment.active" inputId="active" :binary="true" />
                <label for="active">Matrícula ativa</label>
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="enrollmentDialog = false" />
                <Button label="Salvar" icon="pi pi-check" @click="saveEnrollment" />
            </template>
        </Dialog>

        <Dialog v-model:visible="attendanceDialog" :header="`Presença - ${selectedEnrollment?.student_name || ''} - ${selectedEnrollment?.activity_name || ''}`" :modal="true" :style="{ width: '600px' }" class="p-fluid">
            <div class="grid grid-cols-12 gap-4 mb-4">
                <div class="col-span-12 md:col-span-5">
                    <label class="block font-bold mb-2">Data</label>
                    <Calendar 
                        v-model="attendanceDate" 
                        dateFormat="dd/mm/yy" 
                        showIcon 
                        fluid
                        :showOnFocus="false"
                        inputId="attendance-date"
                    />
                </div>
                <div class="col-span-12 md:col-span-4 flex items-end">
                    <div class="flex flex-col w-full">
                        <label class="block font-bold mb-2">Status</label>
                        <ToggleButton 
                            v-model="attendancePresent" 
                            onLabel="Presente" 
                            offLabel="Ausente"
                            onIcon="pi pi-check" 
                            offIcon="pi pi-times"
                            class="w-full"
                        />
                    </div>
                </div>
                <div class="col-span-12 md:col-span-3 flex items-end">
                    <Button label="Registrar" icon="pi pi-check" class="w-full" @click="saveAttendance" />
                </div>
            </div>
            <DataTable :value="attendances" :paginator="true" :rows="5" dataKey="id" size="small" stripedRows>
                <Column header="Data" style="width: 40%">
                    <template #body="{ data }">{{ formatDate(data.date) }}</template>
                </Column>
                <Column header="Status" style="width: 40%">
                    <template #body="{ data }">
                        <Tag :severity="data.present ? 'success' : 'danger'" :value="data.present ? 'Presente' : 'Ausente'" />
                    </template>
                </Column>
                <Column header="Ações" style="width: 20%">
                    <template #body="{ data }">
                        <Button 
                            icon="pi pi-trash" 
                            class="p-button-rounded p-button-text p-button-danger" 
                            v-tooltip.top="'Excluir'"
                            @click="deleteAttendance(data.id)" 
                        />
                    </template>
                </Column>
            </DataTable>
        </Dialog>

        <Dialog v-model:visible="deleteDialog" header="Confirmar" :modal="true" :style="{ width: '350px' }">
            <div class="flex items-center gap-3">
                <i class="pi pi-exclamation-triangle" style="font-size: 2rem" />
                <span>Excluir esta matrícula?</span>
            </div>
            <template #footer>
                <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                <Button label="Sim" icon="pi pi-check" class="p-button-danger" @click="deleteEnrollment" />
            </template>
        </Dialog>
    </div>
</template>
