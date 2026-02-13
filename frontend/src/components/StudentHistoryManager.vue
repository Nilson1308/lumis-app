<script setup>
import { ref, onMounted, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const props = defineProps({
    studentId: { type: Number, required: true },
    readonly: { type: Boolean, default: false } // Nova Prop
});

const toast = useToast();
const historyList = ref([]);
const loading = ref(false);

// Estado do Formulário
const dialogVisible = ref(false);
const record = ref({});
const submitted = ref(false);

// --- CARREGAR DADOS ---
const loadHistory = async () => {
    loading.value = true;
    try {
        // Busca o histórico mesclado (Passado + Presente)
        const res = await api.get(`academic-history/?student=${props.studentId}`);
        historyList.value = res.data.results || res.data;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar histórico.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES CRUD ---
const openNew = () => {
    record.value = {
        student: props.studentId,
        year: new Date().getFullYear() - 1, // Sugere ano anterior
        school_name: '', // Deixa vazio para preencher
        status: 'APPROVED'
    };
    submitted.value = false;
    dialogVisible.value = true;
};

const editRecord = (item) => {
    if (item.is_virtual) {
        toast.add({ severity: 'info', summary: 'Atual', detail: 'Este registro é automático da matrícula atual.', life: 3000 });
        return;
    }
    record.value = { ...item };
    dialogVisible.value = true;
};

const saveRecord = async () => {
    submitted.value = true;

    if (!record.value.year || !record.value.classroom_name) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha Ano e Turma.', life: 3000 });
        return;
    }

    try {
        if (record.value.id) {
            await api.patch(`academic-history/${record.value.id}/`, record.value);
            toast.add({ severity: 'success', summary: 'Atualizado', detail: 'Histórico salvo.', life: 3000 });
        } else {
            await api.post('academic-history/', record.value);
            toast.add({ severity: 'success', summary: 'Criado', detail: 'Registro adicionado.', life: 3000 });
        }
        dialogVisible.value = false;
        loadHistory();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao salvar.', life: 3000 });
    }
};

const deleteRecord = async (id) => {
    if (confirm('Remover este registro histórico?')) {
        try {
            await api.delete(`academic-history/${id}/`);
            toast.add({ severity: 'success', summary: 'Removido', detail: 'Registro apagado.', life: 3000 });
            loadHistory();
        } catch (e) {
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao remover.', life: 3000 });
        }
    }
};

// Recarrega sempre que mudar o aluno (se o componente ficar aberto)
watch(() => props.studentId, () => {
    loadHistory();
});

onMounted(() => {
    loadHistory();
});
</script>

<template>
    <div>
        <div class="flex justify-between items-center mb-4">
            <h4 class="text-xl font-bold m-0 text-700">Linha do Tempo Escolar</h4>
            <Button 
                v-if="!readonly" 
                label="Adicionar Registro Antigo" 
                icon="pi pi-plus" 
                size="small" 
                @click="openNew" 
            />
        </div>

        <Timeline :value="historyList" align="left" class="customized-timeline">
            <template #marker="slotProps">
                <span class="flex w-[2rem] h-[2rem] items-center justify-center rounded-full text-white shadow-1"
                    :class="{
                        'bg-green-500': slotProps.item.status === 'APPROVED',
                        'bg-red-500': slotProps.item.status === 'RETAINED',
                        'bg-blue-500': slotProps.item.status === 'IN_PROGRESS',
                        'bg-orange-500': slotProps.item.status === 'TRANSFERRED'
                    }">
                    <i :class="{
                        'pi pi-check': slotProps.item.status === 'APPROVED',
                        'pi pi-times': slotProps.item.status === 'RETAINED',
                        'pi pi-book': slotProps.item.status === 'IN_PROGRESS',
                        'pi pi-arrow-right-arrow-left': slotProps.item.status === 'TRANSFERRED'
                    }"></i>
                </span>
            </template>
            
            <template #content="slotProps">
                <Card class="mb-3 shadow-none border-1 surface-border">
                    <template #title>
                        <div class="flex justify-between">
                            <span class="text-base font-bold">{{ slotProps.item.year }} - {{ slotProps.item.classroom_name }}</span>
                            
                            <div v-if="!readonly && !slotProps.item.is_virtual">
                                <Button icon="pi pi-pencil" class="p-button-text p-button-sm p-0 w-2rem h-2rem" @click="editRecord(slotProps.item)" />
                                <Button icon="pi pi-trash" class="p-button-text p-button-danger p-button-sm p-0 w-2rem h-2rem ml-1" @click="deleteRecord(slotProps.item.id)" />
                            </div>
                            
                            <Tag v-else-if="slotProps.item.is_virtual" value="Atual" severity="info" />
                        </div>
                    </template>
                    <template #subtitle>
                        {{ slotProps.item.school_name || 'Escola Externa' }}
                    </template>
                    <template #content>
                        <div class="flex flex-col gap-1 text-sm">
                            <span><b>Situação:</b> {{ slotProps.item.status_display || slotProps.item.status }}</span>
                            <span v-if="slotProps.item.final_grade"><b>Média Final:</b> {{ slotProps.item.final_grade }}</span>
                            <p v-if="slotProps.item.observation" class="m-0 text-500 italic mt-1">"{{ slotProps.item.observation }}"</p>
                        </div>
                    </template>
                </Card>
            </template>
        </Timeline>

        <Dialog v-model:visible="dialogVisible" header="Registro Histórico Manual" :modal="true" :style="{ width: '450px' }" class="p-fluid">
            <div class="field mb-3">
                <label class="block font-bold">Ano Letivo</label>
                <InputNumber v-model="record.year" :useGrouping="false" :min="1900" :max="2100" fluid />
            </div>
            
            <div class="mb-3">
                <label class="block font-bold">Nome da Turma / Série</label>
                <InputText v-model="record.classroom_name" placeholder="Ex: 5º Ano B" fluid />
            </div>

            <div class="mb-3">
                <label class="block font-bold">Nome da Escola</label>
                <InputText v-model="record.school_name" placeholder="Ex: Colégio Saint Thomas" fluid />
                <small>Deixe em branco se foi nesta mesma escola.</small>
            </div>

            <div class="grid grid-cols-12 gap-4 mb-3">
                <div class="col-span-12 md:col-span-6">
                    <label class="block font-bold">Situação Final</label>
                    <Dropdown v-model="record.status" :options="[
                        {label: 'Aprovado', value: 'APPROVED'},
                        {label: 'Reprovado', value: 'RETAINED'},
                        {label: 'Transferido', value: 'TRANSFERRED'},
                        {label: 'Evadido', value: 'DROPOUT'}
                    ]" optionLabel="label" optionValue="value" fluid />
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="block font-bold">Média Final</label>
                    <InputText v-model="record.final_grade" placeholder="Ex: 8.5" fluid />
                </div>
            </div>

            <div>
                <label class="block font-bold">Observações</label>
                <Textarea v-model="record.observation" rows="2" autoResize fluid />
            </div>

            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="dialogVisible = false" />
                <Button label="Salvar Registro" icon="pi pi-check" @click="saveRecord" />
            </template>
        </Dialog>
    </div>
</template>

<style>
/* Remove a linha vertical final para ficar mais limpo */
.p-timeline-event:last-child .p-timeline-event-connector {
    display: none;
}
</style>