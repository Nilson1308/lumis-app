<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const reports = ref([]);
const studentOptions = ref([]); // Renomeado para deixar claro que são opções personalizadas
const loading = ref(true);
const reportDialog = ref(false);
const report = ref({});
const submitted = ref(false);

// Variável temporária para armazenar o objeto selecionado no Dropdown
const selectedStudentContext = ref(null);

// --- CARREGAR DADOS ---
const loadData = async () => {
    loading.value = true;
    try {
        const [repRes, optRes] = await Promise.all([
            api.get('student-reports/'),
            // CHAMA A NOVA ROTA ESPECÍFICA
            api.get('assignments/my_students_options/') 
        ]);
        reports.value = repRes.data.results || repRes.data;
        studentOptions.value = optRes.data;
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES ---
const openNew = () => {
    report.value = { date: new Date(), content: '' };
    selectedStudentContext.value = null; // Limpa seleção visual
    submitted.value = false;
    reportDialog.value = true;
};

const editReport = (item) => {
    if (item.status === 'APPROVED') {
        toast.add({ severity: 'warn', summary: 'Bloqueado', detail: 'Relatório aprovado não pode ser editado.', life: 3000 });
        return;
    }
    
    report.value = { ...item, date: new Date(item.date) };
    
    // Tenta reconstruir o contexto visual (opcional, pois o ID já está salvo)
    // Se quiser que o dropdown mostre o valor correto na edição, precisa encontrar na lista:
    const found = studentOptions.value.find(opt => opt.student_id === item.student);
    if (found) {
        selectedStudentContext.value = found;
    }

    reportDialog.value = true;
};

// Quando seleciona um aluno no Dropdown
const onStudentChange = () => {
    if (selectedStudentContext.value) {
        // 1. Define o ID do aluno para enviar ao backend
        report.value.student = selectedStudentContext.value.student_id;
        
        // 2. Preenche automaticamente o Assunto com a Matéria (Teacher UX!)
        // O professor pode alterar depois se quiser (ex: "Matemática - Comportamento")
        if (!report.value.subject) {
            report.value.subject = selectedStudentContext.value.subject_name;
        }
    }
};

const saveReport = async () => {
    submitted.value = true;
    
    // Validação básica
    if (!report.value.student || !report.value.subject || !report.value.content) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Preencha todos os campos obrigatórios.', life: 3000 });
        return;
    }

    const payload = { ...report.value };
    if (payload.date instanceof Date) {
        payload.date = payload.date.toISOString().split('T')[0];
    }

    try {
        if (report.value.id) {
            await api.put(`student-reports/${report.value.id}/`, payload);
            toast.add({ severity: 'success', summary: 'Atualizado', detail: 'Relatório salvo.', life: 3000 });
        } else {
            await api.post('student-reports/', payload);
            toast.add({ severity: 'success', summary: 'Criado', detail: 'Relatório enviado.', life: 3000 });
        }
        reportDialog.value = false;
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao salvar.', life: 3000 });
    }
};

onMounted(() => {
    loadData();
});

// ... funções auxiliares de status (getStatusLabel, getStatusSeverity) ...
const getStatusLabel = (status) => {
    const map = { 'PENDING': 'Em Análise', 'APPROVED': 'Aprovado', 'REJECTED': 'Ajuste Solicitado' };
    return map[status] || status;
};

const getStatusSeverity = (status) => {
    const map = { 'PENDING': 'warning', 'APPROVED': 'success', 'REJECTED': 'danger' };
    return map[status] || 'info';
};
</script>

<template>
    <div class="card">
        <Toast />
        <Toolbar class="mb-4">
            <template #start>
                <Button label="Novo Relatório Individual" icon="pi pi-plus" class="p-button-success" @click="openNew" />
            </template>
        </Toolbar>

        <DataTable :value="reports" :loading="loading" :paginator="true" :rows="10">
            <template #header>Meus Relatórios</template>
            <template #empty>Nenhum registro.</template>

            <Column field="date" header="Data">
                <template #body="slotProps">{{ new Date(slotProps.data.date).toLocaleDateString('pt-BR') }}</template>
            </Column>
            <Column field="student_name" header="Aluno"></Column>
            <Column field="subject" header="Assunto"></Column>
            <Column field="status" header="Status" style="min-width: 180px">
                <template #body="slotProps">
                    <div class="flex items-center gap-2">
                        <Tag :value="getStatusLabel(slotProps.data.status)" :severity="getStatusSeverity(slotProps.data.status)" />
                        
                        <i v-if="slotProps.data.status === 'REJECTED'" 
                           class="pi pi-exclamation-circle text-red-500 text-xl cursor-pointer" 
                           v-tooltip.top="'Atenção: ' + (slotProps.data.coordinator_comment || 'Verifique o conteúdo.')"
                        ></i>

                        <i v-if="slotProps.data.status === 'APPROVED'" 
                           class="pi pi-check-circle text-green-500 text-xl" 
                           v-tooltip.top="'Relatório Aprovado e Publicado'"
                        ></i>
                    </div>
                </template>
            </Column>
            <Column header="Ações">
                <template #body="slotProps">
                    <Button icon="pi pi-pencil" class="p-button-rounded p-button-text" @click="editReport(slotProps.data)" :disabled="slotProps.data.status === 'APPROVED'" />
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="reportDialog" :style="{ width: '800px' }" header="Relatório de Aluno" :modal="true" class="p-fluid" maximizable>
            
            <div class="mb-2">
                <label class="block font-bold mb-2">Selecione o Aluno</label>
                <Dropdown 
                    v-model="selectedStudentContext" 
                    :options="studentOptions" 
                    optionLabel="label" 
                    placeholder="Busque por nome ou turma..." 
                    filter 
                    :disabled="!!report.id" 
                    @change="onStudentChange"
                    class="w-full"
                >
                    <template #option="slotProps">
                        <div class="flex flex-col">
                            <span class="font-bold">{{ slotProps.option.student_name }}</span>
                            <span class="text-sm text-gray-500">{{ slotProps.option.classroom_name }} - {{ slotProps.option.subject_name }}</span>
                        </div>
                    </template>
                </Dropdown>
                <small class="p-error" v-if="submitted && !report.student">Obrigatório.</small>
            </div>
            
            <div class="grid grid-cols-12 gap-4 mb-2">
                <div class="col-span-12 xl:col-span-6">
                    <label class="block font-bold mb-2">Data</label>
                    <DatePicker v-model="report.date" dateFormat="dd/mm/yy" showIcon fluid />
                </div>
                <div class="col-span-12 xl:col-span-6">
                    <label class="block font-bold mb-2">Assunto / Matéria</label>
                    <InputText v-model="report.subject" placeholder="Ex: Matemática - Dificuldade em Frações" fluid />
                    <small class="text-gray-500">Preenchido automaticamente ao selecionar o aluno.</small>
                </div>
            </div>

            <div>
                <label class="block font-bold mb-2">Conteúdo do Relatório</label>
                <Editor v-model="report.content" editorStyle="height: 320px" />
                <small class="p-error" v-if="submitted && !report.content">O conteúdo é obrigatório.</small>
            </div>

            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="reportDialog = false" />
                <Button label="Salvar e Enviar" icon="pi pi-check" @click="saveReport" />
            </template>
        </Dialog>
    </div>
</template>