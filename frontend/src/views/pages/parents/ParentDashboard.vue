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

// --- CARREGAMENTO ---
const loadDashboard = async () => {
    try {
        loading.value = true;
        
        // 1. Busca Filhos
        const resChildren = await api.get('students/my-children/');
        children.value = resChildren.data;

        // 2. Busca Perfil do Pai (Para o Header e Edição)
        const resProfile = await api.get('guardians/me/');
        guardianProfile.value = resProfile.data;

    } catch (e) {
        console.error("Erro ao carregar dados", e);
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES DE NAVEGAÇÃO ---
const openReportCard = (studentId) => router.push({ name: 'parent-report-card', params: { id: studentId } });
const openAttendance = (studentId) => router.push({ name: 'parent-attendance', params: { id: studentId } });

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
    showStudentDialog.value = true;
};

const saveStudent = async () => {
    try {
        await api.patch(`students/${editingStudent.value.id}/`, editingStudent.value);
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Dados de saúde atualizados!', life: 3000 });
        showStudentDialog.value = false;
        loadDashboard(); // Recarrega para atualizar a tela
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao atualizar dados do aluno.' });
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

        <div class="col-span-12 xl:col-span-4" v-for="child in children" :key="child.id">
            <div class="card card-w-title cursor-pointer hover:surface-100 transition-duration-200 h-full flex flex-col justify-between">
                <div>
                    <div class="flex align-center mb-3">
                        <Avatar :label="child.name.charAt(0)" size="large" shape="circle" class="mr-3 bg-indigo-500 text-white font-bold" />
                        <div>
                            <div class="text-xl font-bold">{{ child.name }}</div>
                            <span class="text-gray-500">{{ child.classroom_name || 'Sem Turma' }}</span>
                        </div>
                    </div>
                    <Divider />
                </div>
                
                <div class="mt-3 flex gap-2 justify-between">
                    <div class="flex gap-2">
                        <Button label="Boletim" icon="pi pi-file" class="p-button-sm p-button-outlined" @click="openReportCard(child.id)" />
                        <Button label="Faltas" icon="pi pi-calendar" class="p-button-sm p-button-outlined p-button-warning" @click="openAttendance(child.id)" />
                        <Button 
                            icon="pi pi-book" 
                            label="Relatórios" 
                            class="p-button-sm p-button-outlined flex-1" 
                            @click="router.push({ name: 'parent-reports', params: { id: child.id } })" 
                        />
                    </div>
                    <Button 
                        icon="pi pi-pencil" 
                        class="p-button-sm p-button-text" 
                        @click="openStudentEdit(child)" 
                        v-tooltip.top="'Atualizar Dados de Saúde/Emergência'"
                    />
                </div>
            </div>
        </div>
        
        <div v-if="!loading && children.length === 0" class="col-12">
            <div class="card">
                <p>Nenhum aluno vinculado ao seu CPF.</p>
            </div>
        </div>

        <Dialog v-model:visible="showProfileDialog" header="Meus Dados de Contato" :modal="true" :style="{ width: '450px' }" class="p-fluid">
            <div class="mb-4">
                <label class="font-bold mb-2 block">Email</label>
                <InputText v-model="guardianProfile.email" fluid />
            </div>
            <div class="mb-4">
                <label class="font-bold mb-2 block">Celular / WhatsApp</label>
                <InputMask v-model="guardianProfile.phone" mask="(99) 99999-9999" fluid />
            </div>
            <div class="mb-4">
                <label class="font-bold mb-2 block">Email</label>
                <InputText v-model="guardianProfile.email" placeholder="exemplo@email.com" fluid />
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

            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="showStudentDialog = false" />
                <Button label="Salvar" icon="pi pi-check" @click="saveStudent" />
            </template>
        </Dialog>
    </div>
</template>