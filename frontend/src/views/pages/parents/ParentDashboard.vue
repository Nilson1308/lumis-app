<script setup>
import { useRouter, useRoute } from 'vue-router';
import { ref, onMounted, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const router = useRouter();
const route = useRoute(); // Para capturar ?action=profile
const toast = useToast();

const children = ref([]);
const guardianProfile = ref({ name: '' });
const loading = ref(true);

// --- ESTADOS DOS DIALOGS ---
const showProfileDialog = ref(false);
const showStudentDialog = ref(false);
const editingStudent = ref({});
const medicalReportFile = ref(null);
const prescriptionFile = ref(null);
const savingStudent = ref(false);

// --- CARREGAMENTO ---
const loadDashboard = async () => {
    try {
        loading.value = true;
        
        // 1. Busca Filhos
        const resChildren = await api.get('students/my-children/');
        children.value = resChildren.data;

        // 2. Busca Perfil do Pai (Para o Header e Edição)
        const resProfile = await api.get('guardians/me/');
        guardianProfile.value = {
            ...resProfile.data,
            secondary_phone: resProfile.data.secondary_phone || ''
        };

    } catch (e) {
        console.error("Erro ao carregar dados", e);
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES DE NAVEGAÇÃO ---
const openReportCard = (studentId) => router.push({ name: 'parent-report-card', params: { id: studentId } });
const openAttendance = (studentId) => router.push({ name: 'parent-attendance', params: { id: studentId } });
const openClassDiary = (studentId) => router.push({ name: 'parent-class-diary', params: { id: studentId } });
const openSchoolCalendar = () => router.push({ name: 'parent-calendar' });
const openClassSchedule = (studentId) => router.push({ name: 'parent-class-schedule', params: { id: studentId } });
const openWeeklySummary = (studentId) => router.push({ name: 'parent-student-summary', params: { id: studentId } });

// --- LÓGICA DE EDIÇÃO: PERFIL ---
const openProfileEdit = () => {
    showProfileDialog.value = true;
};

const saveProfile = async () => {
    try {
        await api.patch(`guardians/${guardianProfile.value.id}/`, guardianProfile.value);
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Seus dados foram atualizados!', life: 3000 });
        showProfileDialog.value = false;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao atualizar perfil.' });
    }
};

const searchCep = async () => {
    const cep = editingStudent.value.zip_code ? editingStudent.value.zip_code.replace(/\D/g, '') : '';
    if (cep.length !== 8) return;
    try {
        const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
        const data = await response.json();
        if (!data.erro) {
            editingStudent.value.street = data.logradouro;
            editingStudent.value.neighborhood = data.bairro;
            editingStudent.value.city = data.localidade;
            editingStudent.value.state = data.uf;
        }
    } catch (error) { console.error(error); }
};

// --- LÓGICA DE EDIÇÃO: ALUNO ---
const openStudentEdit = (child) => {
    editingStudent.value = { ...child }; // Clona para não editar em tempo real
    medicalReportFile.value = null;
    prescriptionFile.value = null;
    showStudentDialog.value = true;
};

const openUploadedFile = (url) => {
    if (!url) return;
    if (String(url).startsWith('http')) window.open(url, '_blank');
    else window.open(`${window.location.origin}${url}`, '_blank');
};

const onMedicalReportSelect = (event) => {
    medicalReportFile.value = event.files?.[0] || null;
};

const onPrescriptionSelect = (event) => {
    prescriptionFile.value = event.files?.[0] || null;
};

const saveStudent = async () => {
    savingStudent.value = true;
    try {
        const id = editingStudent.value.id;
        const hasNewFiles = !!(medicalReportFile.value || prescriptionFile.value);

        if (hasNewFiles) {
            const formData = new FormData();
            const textFields = [
                'emergency_contact',
                'allergies',
                'medications',
                'zip_code',
                'street',
                'number',
                'complement',
                'neighborhood',
                'city',
                'state'
            ];
            textFields.forEach((key) => {
                const v = editingStudent.value[key];
                formData.append(key, v != null && v !== undefined ? String(v) : '');
            });
            if (medicalReportFile.value) formData.append('medical_report', medicalReportFile.value);
            if (prescriptionFile.value) formData.append('prescription', prescriptionFile.value);

            await api.patch(`students/${id}/`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
        } else {
            await api.patch(`students/${id}/`, editingStudent.value);
        }

        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Dados atualizados!', life: 3000 });
        showStudentDialog.value = false;
        medicalReportFile.value = null;
        prescriptionFile.value = null;
        loadDashboard();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao atualizar dados do aluno.' });
    } finally {
        savingStudent.value = false;
    }
};

// Monitora a URL para abrir o modal de perfil vindo do Menu
watch(() => route.query.action, (newAction) => {
    if (newAction === 'profile') {
        openProfileEdit();
        // Limpa a query para não reabrir ao dar refresh
        router.replace({ query: null }); 
    }
});

onMounted(() => {
    loadDashboard();
    // Verifica se já chegou com o comando de abrir perfil
    if (route.query.action === 'profile') {
        openProfileEdit();
        router.replace({ query: null });
    }
});
</script>

<template>
    <div class="grid grid-cols-12 gap-4 mb-2">
        <Toast />

        <div class="col-span-12 xl:col-span-12">
            <div class="card mb-0">
                <div class="flex justify-between items-center mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-1">Bem-vindo(a)</span>
                        <div class="text-900 font-medium text-xl">{{ guardianProfile.name || 'Carregando...' }}</div>
                        <div class="text-500 text-sm">Portal da Família</div>
                    </div>
                    <div class="flex flex-col items-center gap-2">
                        <Button 
                            icon="pi pi-user-edit" 
                            class="p-button-rounded p-button-outlined" 
                            @click="openProfileEdit" 
                            v-tooltip.left="'Editar Meus Dados'"
                        />
                    </div>
                </div>
            </div>
        </div>

        <div class="col-span-12 md:col-span-6 xl:col-span-6" v-for="child in children" :key="child.id">
            <div class="card card-w-title h-full flex flex-col surface-card border-1 surface-border">
                <div class="flex align-items-start justify-content-between gap-3 mb-3">
                    <div class="flex align-items-center">
                        <Avatar :label="child.name.charAt(0)" size="large" shape="circle" class="mr-3 bg-indigo-500 text-white font-bold flex-shrink-0" />
                        <div class="min-w-0">
                            <div class="text-xl font-bold text-900 line-height-3">{{ child.name }}</div>
                            <span class="text-600 text-sm">{{ child.classroom_name || 'Sem Turma' }}</span>
                        </div>
                    </div>
                    <Button
                        icon="pi pi-pencil"
                        class="p-button-rounded p-button-text flex-shrink-0"
                        @click.stop="openStudentEdit(child)"
                        v-tooltip.left="'Dados do aluno, saúde e documentos'"
                    />
                </div>

                <Divider class="my-0" />

                <div class="mt-3">
                    <div class="text-500 text-xs font-semibold uppercase mb-2">Rotina e acompanhamento</div>
                    <div class="grid grid-cols-2 gap-2">
                        <Button
                            label="Resumo da semana"
                            icon="pi pi-chart-line"
                            class="col-span-2 w-full p-button-sm justify-content-center"
                            @click.stop="openWeeklySummary(child.id)"
                        />
                        <Button
                            label="Diário de classe"
                            icon="pi pi-bookmark"
                            class="w-full p-button-outlined p-button-info justify-content-center"
                            @click.stop="openClassDiary(child.id)"
                        />
                        <Button
                            label="Grade horária"
                            icon="pi pi-clock"
                            class="w-full p-button-outlined p-button-success justify-content-center"
                            @click.stop="openClassSchedule(child.id)"
                            v-tooltip.bottom="'Horários da turma do seu educando'"
                        />
                        <Button
                            label="Frequência"
                            icon="pi pi-calendar-times"
                            class="w-full p-button-outlined p-button-warning justify-content-center"
                            @click.stop="openAttendance(child.id)"
                        />
                        <Button
                            label="Boletim"
                            icon="pi pi-file-pdf"
                            class="w-full p-button-outlined justify-content-center"
                            @click.stop="openReportCard(child.id)"
                        />
                        <Button
                            label="Relatórios"
                            icon="pi pi-file-edit"
                            class="w-full p-button-outlined justify-content-center"
                            @click.stop="router.push({ name: 'parent-reports', params: { id: child.id } })"
                        />
                    </div>
                    <Button
                        label="Calendário da escola"
                        icon="pi pi-calendar"
                        class="w-full mt-2 p-button-outlined p-button-secondary justify-content-center"
                        @click.stop="openSchoolCalendar()"
                        v-tooltip.bottom="'Provas, eventos e avisos no calendário (em evolução por turma)'"
                    />
                </div>
            </div>
        </div>
        
        <div v-if="!loading && children.length === 0" class="col-12">
            <div class="card">
                <p>Nenhum aluno vinculado ao seu CPF.</p>
            </div>
        </div>

        <Dialog v-model:visible="showProfileDialog" header="Meus Dados de Contato" :modal="true" :style="{ width: '480px' }" class="p-fluid">
            <div class="mb-4">
                <label class="font-bold mb-2 block">E-mail</label>
                <InputText v-model="guardianProfile.email" type="email" placeholder="exemplo@email.com" fluid />
            </div>
            <div class="mb-4">
                <label class="font-bold mb-2 block">Celular / WhatsApp</label>
                <InputMask v-model="guardianProfile.phone" mask="(99) 99999-9999" fluid />
            </div>
            <div class="mb-4">
                <label class="font-bold mb-2 block">Telefone secundário / recado</label>
                <InputMask v-model="guardianProfile.secondary_phone" mask="(99) 99999-9999" fluid />
                <small class="text-600">Opcional — outro número para contato da escola.</small>
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="showProfileDialog = false" />
                <Button label="Salvar" icon="pi pi-check" @click="saveProfile" />
            </template>
        </Dialog>

        <Dialog v-model:visible="showStudentDialog" :header="'Dados de ' + editingStudent.name" :modal="true" :style="{ width: '800px' }" class="p-fluid" maximizable>
            <div class="grid grid-cols-12 gap-4 mb-2">
                <div class="col-span-12 xl:col-span-4">
                    <label class="block font-bold mb-3">CEP <i class="pi pi-search text-primary ml-1" v-tooltip="'Digite o CEP para buscar'"></i></label>
                    <InputMask v-model="editingStudent.zip_code" mask="99999-999" @blur="searchCep" fluid />
                </div>
                <div class="col-span-12 xl:col-span-8">
                    <label class="block font-bold mb-3">Logradouro (Rua/Av)</label>
                    <InputText v-model="editingStudent.street" fluid />
                </div>
                <div class="col-span-12 xl:col-span-4">
                    <label class="block font-bold mb-3">Número</label>
                    <InputText id="number" v-model="editingStudent.number" fluid />
                </div>
                <div class="col-span-12 xl:col-span-8">
                    <label class="block font-bold mb-3">Complemento</label>
                    <InputText v-model="editingStudent.complement" fluid />
                </div>
                <div class="col-span-12 xl:col-span-5">
                    <label class="block font-bold mb-3">Bairro</label>
                    <InputText v-model="editingStudent.neighborhood" fluid />
                </div>
                <div class="col-span-12 xl:col-span-5">
                    <label class="block font-bold mb-3">Cidade</label>
                    <InputText v-model="editingStudent.city" fluid />
                </div>
                <div class="col-span-12 xl:col-span-2">
                    <label class="block font-bold mb-3">UF</label>
                    <InputText v-model="editingStudent.state" fluid />
                </div>
            </div>
            
            <Divider/>
            
            <div class="field mb-4">
                <label class="font-bold mb-2 block text-red-600">Contato de Emergência</label>
                <InputText v-model="editingStudent.emergency_contact" placeholder="Nome e Telefone" fluid />
            </div>

            <div class="grid grid-cols-2 gap-4">
                <div class="col-span-2 md:col-span-1 mb-3">
                    <label class="font-bold block mb-2">Alergias</label>
                    <Editor v-model="editingStudent.allergies" rows="3" autoResize class="w-full" editorStyle="height: 160px" />
                </div>
                <div class="col-span-2 md:col-span-1 mb-3">
                    <label class="font-bold block mb-2">Medicamentos</label>
                    <Editor v-model="editingStudent.medications" rows="3" autoResize class="w-full" editorStyle="height: 160px" />
                </div>
            </div>

            <Divider />
            <div class="text-900 font-semibold mb-3">Documentos médicos</div>
            <div class="grid grid-cols-12 gap-4">
                <div class="col-span-12 md:col-span-6">
                    <label class="font-bold block mb-2">Laudo médico</label>
                    <div v-if="editingStudent.medical_report" class="mb-2">
                        <Button
                            label="Ver arquivo atual"
                            icon="pi pi-external-link"
                            class="p-button-text p-button-sm p-0"
                            @click="openUploadedFile(editingStudent.medical_report)"
                        />
                    </div>
                    <FileUpload
                        mode="basic"
                        name="medical_report"
                        accept="application/pdf,image/*"
                        :maxFileSize="8000000"
                        chooseLabel="Enviar ou trocar laudo"
                        @select="onMedicalReportSelect"
                        class="w-full"
                    />
                    <small class="text-600">PDF ou imagem, até 8 MB.</small>
                </div>
                <div class="col-span-12 md:col-span-6">
                    <label class="font-bold block mb-2">Receita médica</label>
                    <div v-if="editingStudent.prescription" class="mb-2">
                        <Button
                            label="Ver arquivo atual"
                            icon="pi pi-external-link"
                            class="p-button-text p-button-sm p-0"
                            @click="openUploadedFile(editingStudent.prescription)"
                        />
                    </div>
                    <FileUpload
                        mode="basic"
                        name="prescription"
                        accept="application/pdf,image/*"
                        :maxFileSize="8000000"
                        chooseLabel="Enviar ou trocar receita"
                        @select="onPrescriptionSelect"
                        class="w-full"
                    />
                    <small class="text-600">PDF ou imagem, até 8 MB.</small>
                </div>
            </div>

            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="showStudentDialog = false" />
                <Button label="Salvar" icon="pi pi-check" @click="saveStudent" :loading="savingStudent" />
            </template>
        </Dialog>
    </div>
</template>