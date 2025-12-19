<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const route = useRoute();
const router = useRouter();

// Estados de Dados
const summary = ref([]);
const history = ref([]);
const loading = ref(true);
const studentName = ref('');
const studentClass = ref('');
const studentId = ref(null);

// Estados do Modal de Justificativa
const justificationDialog = ref(false);
const selectedAttendance = ref(null);
const justificationForm = ref({
    reason: '',
    file: null
});
const sending = ref(false);

const openFile = (url) => {
    if (url) window.open(url, '_blank');
};

// --- CARREGAMENTO DE DADOS ---
const loadData = async () => {
    try {
        loading.value = true;
        
        // Busca em paralelo
        const [attendanceResponse, childrenResponse] = await Promise.all([
            api.get(`students/${studentId.value}/attendance-report/`),
            api.get(`students/my-children/`)
        ]);

        // 1. Processa Faltas
        summary.value = attendanceResponse.data.summary;
        history.value = attendanceResponse.data.history;

        // 2. Processa Dados do Aluno
        const currentStudent = childrenResponse.data.find(child => child.id === studentId.value);
        if (currentStudent) {
            studentName.value = currentStudent.name;
            studentClass.value = currentStudent.classroom_name || 'Sem Turma';
        }

    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar frequência', life: 3000 });
    } finally {
        loading.value = false;
    }
};

onMounted(() => {
    studentId.value = parseInt(route.params.id);
    loadData();
});

const goBack = () => router.push({ name: 'parent-dashboard' });

// --- LÓGICA DE JUSTIFICATIVA ---

const openJustification = (att) => {
    selectedAttendance.value = att;
    // Limpa o formulário
    justificationForm.value = { reason: '', file: null };
    justificationDialog.value = true;
};

// Captura o arquivo do componente FileUpload
const onFileSelect = (event) => {
    // O evento do PrimeVue retorna "files" que é um array
    justificationForm.value.file = event.files[0];
};

const sendJustification = async () => {
    if (!justificationForm.value.reason) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Por favor, descreva o motivo da falta.' });
        return;
    }

    try {
        sending.value = true;
        const formData = new FormData();
        
        if (!selectedAttendance.value.id) {
             throw new Error("ID da falta não encontrado.");
        }

        formData.append('attendance', selectedAttendance.value.id);
        formData.append('reason', justificationForm.value.reason);
        
        if (justificationForm.value.file) {
            formData.append('file', justificationForm.value.file);
        }

        await api.post('justifications/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        toast.add({ severity: 'success', summary: 'Enviado', detail: 'Justificativa enviada para análise.' });
        justificationDialog.value = false;
        
        // --- CORREÇÃO AQUI ---
        // Atualiza a lista localmente e NÃO chama o servidor de novo agora.
        const index = history.value.findIndex(item => item.id === selectedAttendance.value.id);
        
        if (index !== -1) {
            // Truque do Vue 3: Criar um novo objeto força a reatividade da Tabela a notar a mudança
            history.value[index] = { 
                ...history.value[index], 
                justification_status: 'PENDING' 
            };
        }

        // REMOVA ou COMENTE esta linha para evitar sobrescrever a mudança visual
        // await loadData(); 

    } catch (e) {
        console.error(e);
        let msg = 'Falha ao enviar justificativa.';
        if (e.response && e.response.data && e.response.data[0]) {
            msg = e.response.data[0];
        }
        toast.add({ severity: 'error', summary: 'Erro', detail: msg });
    } finally {
        sending.value = false;
    }
};
</script>

<template>
    <div class="grid grid-cols-12 gap-4 mb-2">
        <Toast />
        
        <div class="col-span-12 xl:col-span-12">
            <div class="card">
                <div class="flex flex-col md:flex-row justify-between items-center gap-4">
                    <div class="flex items-center gap-2 self-start md:self-auto">
                        <Button icon="pi pi-arrow-left" class="p-button-rounded p-button-text" @click="goBack" />
                        <div>
                            <span class="block text-xl font-bold">Frequência e Faltas</span>
                            <span class="text-sm text-gray-500 hidden md:inline">Acompanhamento acadêmico</span>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-3 w-full md:w-auto">
                        <div class="text-right flex-grow-1 md:flex-grow-0">
                            <div class="text-900 font-bold text-lg">{{ studentName }}</div>
                            <div class="text-600">{{ studentClass }}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-span-12 xl:col-span-3" v-for="item in summary" :key="item.subject">
            <div class="card h-full flex flex-col justify-center items-center text-center">
                <div class="text-900 font-medium mb-2">{{ item.subject }}</div>
                
                <div class="text-2xl font-bold" :class="{'text-red-500': item.effective > 5, 'text-gray-700': item.effective <= 5}">
                    {{ item.count }} Faltas
                </div>
                
                <div v-if="item.justified > 0" class="text-sm text-green-600 font-bold mt-1">
                    ({{ item.justified }} Abonadas/Justificadas)
                </div>
                <div v-else class="text-xs text-gray-400 mt-1">
                    Nenhuma justificada
                </div>
            </div>
        </div>

        <div class="col-span-12 xl:col-span-12">
            <div class="card">
                <h5>Histórico de Ausências</h5>
                <DataTable :value="history" :loading="loading" :paginator="true" :rows="10" responsiveLayout="scroll">
                    <Column field="date" header="Data" sortable>
                        <template #body="slotProps">
                            {{ new Date(slotProps.data.date).toLocaleDateString('pt-BR') }}
                        </template>
                    </Column>
                    <Column field="subject" header="Matéria/Aula"></Column>
                    
                    <Column header="Situação / Ação" style="min-width: 250px;">
                        <template #body="slotProps">
                            
                            <div v-if="slotProps.data.justified" class="flex items-center gap-2">
                                <Tag severity="success" value="Abonada" icon="pi pi-check" />
                                <Button v-if="slotProps.data.file_url" 
                                        icon="pi pi-paperclip" 
                                        class="p-button-rounded p-button-text p-button-sm" 
                                        @click="openFile(slotProps.data.file_url)" 
                                        v-tooltip="'Ver Atestado Arquivado'" />
                            </div>
                            
                            <div v-else-if="slotProps.data.justification_status === 'PENDING'" class="flex items-center gap-2">
                                <Tag severity="warning" value="Em Análise" icon="pi pi-clock" />
                                <Button v-if="slotProps.data.file_url" 
                                        icon="pi pi-eye" 
                                        class="p-button-rounded p-button-text p-button-secondary p-button-sm" 
                                        @click="openFile(slotProps.data.file_url)" 
                                        v-tooltip="'Ver o que eu enviei'" />
                            </div>
                            
                            <div v-else-if="slotProps.data.justification_status === 'REJECTED'" class="flex items-center gap-2">
                                <Tag severity="danger" value="Recusada" />
                                
                                <i class="pi pi-info-circle text-red-500 cursor-pointer" 
                                   v-tooltip.top="'Motivo: ' + slotProps.data.rejection_reason"></i>
                                
                                <Button label="Reenviar" 
                                        class="p-button-outlined p-button-danger p-button-sm ml-2" 
                                        @click="openJustification(slotProps.data)" />
                            </div>

                            <Button v-else 
                                    label="Justificar" 
                                    icon="pi pi-upload" 
                                    class="p-button-sm p-button-outlined" 
                                    @click="openJustification(slotProps.data)" />
                            
                        </template>
                    </Column>
                </DataTable>
            </div>
        </div>

        <Dialog v-model:visible="justificationDialog" header="Enviar Justificativa" :modal="true" :style="{ width: '500px' }" class="p-fluid">
            <p class="mb-4 text-gray-600 text-sm">
                Envie um atestado médico ou documento que comprove a ausência. A coordenação irá analisar o pedido.
            </p>

            <div class="field mb-4">
                <label class="font-bold mb-2 block">Motivo da Ausência</label>
                <Textarea v-model="justificationForm.reason" rows="3" class="w-full" placeholder="Ex: Consulta médica, virose, problemas familiares..." />
            </div>
            
            <div class="field mb-4">
                <label class="font-bold mb-2 block">Anexar Documento (Foto ou PDF)</label>
                <FileUpload 
                    mode="basic" 
                    name="file" 
                    accept="image/*,application/pdf" 
                    :maxFileSize="5000000" 
                    @select="onFileSelect"
                    chooseLabel="Selecionar Arquivo" 
                    class="w-full"
                />
            </div>

            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="justificationDialog = false" />
                <Button label="Enviar para Análise" icon="pi pi-send" @click="sendJustification" :loading="sending" />
            </template>
        </Dialog>

    </div>
</template>