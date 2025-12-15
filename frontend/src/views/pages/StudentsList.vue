<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();

const FilterMatchMode = {
    STARTS_WITH: 'startsWith',
    CONTAINS: 'contains',
    NOT_CONTAINS: 'notContains',
    ENDS_WITH: 'endsWith',
    EQUALS: 'equals',
    NOT_EQUALS: 'notEquals',
    IN: 'in',
    LESS_THAN: 'lt',
    LESS_THAN_OR_EQUAL_TO: 'lte',
    GREATER_THAN: 'gt',
    GREATER_THAN_OR_EQUAL_TO: 'gte',
    BETWEEN: 'between',
    DATE_IS: 'dateIs',
    DATE_IS_NOT: 'dateIsNot',
    DATE_BEFORE: 'dateBefore',
    DATE_AFTER: 'dateAfter'
};

const students = ref([]);
const guardians = ref([]); // Lista de opções para o Dropdown
const student = ref({});
const studentDialog = ref(false);
const deleteStudentDialog = ref(false);
const loading = ref(true);
const submitted = ref(false);

const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
});

// --- CARREGAR DADOS ---
const loadData = async () => {
    loading.value = true;
    try {
        // Busca Alunos
        const resStudents = await api.get('students/?page_size=100');
        students.value = resStudents.data.results;

        // Busca Responsáveis
        const resGuardians = await api.get('guardians/?page_size=1000');
        const listaBruta = resGuardians.data.results || resGuardians.data;
        
        // Mapeamento: Cria o campo 'label' para a LISTA DE OPÇÕES
        guardians.value = listaBruta.map(g => ({
            ...g, // Mantém id, cpf, email, etc
            label: g.name ? `${g.name} ${g.cpf ? '(' + g.cpf + ')' : ''}` : `Sem Nome (ID: ${g.id})`
        }));

    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados' });
    } finally {
        loading.value = false;
    }
};

// --- BUSCA DE CEP (VIACEP) ---
const searchCep = async () => {
    const cep = student.value.zip_code ? student.value.zip_code.replace(/\D/g, '') : '';

    if (cep.length !== 8) return;

    try {
        const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
        const data = await response.json();

        if (data.erro) {
            toast.add({ severity: 'warn', summary: 'Atenção', detail: 'CEP não encontrado.', life: 3000 });
            return;
        }

        student.value.street = data.logradouro;
        student.value.neighborhood = data.bairro;
        student.value.city = data.localidade;
        student.value.state = data.uf;
        
        toast.add({ severity: 'info', summary: 'Endereço', detail: 'Endereço carregado!', life: 3000 });
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao buscar CEP.', life: 3000 });
    }
};

// --- AÇÕES ---
const openNew = () => {
    student.value = {
        nationality: 'Brasileira',
        city: 'Mogi das Cruzes',
        state: 'SP',
        guardians: [] // Array vazio obrigatório
    };
    submitted.value = false;
    studentDialog.value = true;
};

const editStudent = (prod) => {
    student.value = { ...prod };
    
    // Ajuste de Data
    if (student.value.birth_date) {
        const parts = student.value.birth_date.split('-');
        student.value.birth_date = new Date(parts[0], parts[1] - 1, parts[2]);
    }

    // --- A CORREÇÃO SIMPLIFICADA ---
    // Transforma a lista de objetos [{id:1, name: '...'}, {id:2...}] 
    // em uma lista simples de IDs: [1, 2]
    if (student.value.guardians && Array.isArray(student.value.guardians)) {
        student.value.guardians = student.value.guardians.map(g => g.id);
    } else {
        student.value.guardians = [];
    }
    
    studentDialog.value = true;
};

const confirmDeleteStudent = (prod) => {
    student.value = prod;
    deleteStudentDialog.value = true;
};

// --- SALVAR ---
const saveStudent = async () => {
    submitted.value = true;

    if (student.value.name && student.value.registration_number) {
        // Clona para não afetar a tela visualmente enquanto salva
        const payload = { ...student.value };
        
        // 1. Formata Data (YYYY-MM-DD)
        if (payload.birth_date instanceof Date) {
            payload.birth_date = payload.birth_date.toISOString().split('T')[0];
        }

        // 2. Extrai apenas os IDs dos Responsáveis para enviar ao Backend
        // O componente usa Objetos inteiros, mas a API espera [1, 2, 5]
        if (payload.guardians && payload.guardians.length > 0) {
            payload.guardians = payload.guardians.map(g => (g.id ? g.id : g));
        }

        try {
            if (student.value.id) {
                await api.put(`students/${student.value.id}/`, payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aluno atualizado', life: 3000 });
            } else {
                await api.post('students/', payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aluno criado', life: 3000 });
            }
            studentDialog.value = false;
            loadData();
        } catch (error) {
            console.error(error);
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar aluno.', life: 3000 });
        }
    }
};

const deleteStudent = async () => {
    try {
        await api.delete(`students/${student.value.id}/`);
        deleteStudentDialog.value = false;
        student.value = {};
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aluno removido', life: 3000 });
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao remover', life: 3000 });
    }
};

onMounted(() => {
    loadData();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            <Toolbar class="mb-4">
                <template v-slot:start>
                    <div class="my-2">
                        <Button label="Novo Aluno" icon="pi pi-plus" class="mr-2" @click="openNew" />
                    </div>
                </template>
            </Toolbar>

            <DataTable :value="students" :filters="filters" :loading="loading" responsiveLayout="scroll" :paginator="true" :rows="10">
                <template #header>
                    <div class="flex flex-wrap gap-2 items-center justify-between">
                        <h4 class="m-0">Listagem de Alunos</h4>
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText v-model="filters['global'].value" placeholder="Buscar..." />
                        </IconField>
                    </div>
                </template>
                
                <Column field="registration_number" header="Matrícula" sortable></Column>
                <Column field="name" header="Nome" sortable></Column>
                <Column field="birth_date" header="Nascimento">
                    <template #body="slotProps">
                        <span v-if="slotProps.data.birth_date">
                            {{ new Date(slotProps.data.birth_date + 'T00:00:00').toLocaleDateString('pt-BR') }}
                        </span>
                    </template>
                </Column>
                <Column field="emergency_contact" header="Contato Emergência"></Column>
                
                <Column header="Ações">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editStudent(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDeleteStudent(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="studentDialog" :style="{ width: '800px' }" header="Prontuário do Aluno" :modal="true" class="p-fluid">
                
                <TabView>
                    
                    <TabPanel header="Dados Pessoais">
                        <div class="mb-2">
                            <label for="name" class="block font-bold mb-3">Nome Completo</label>
                            <InputText id="name" v-model.trim="student.name" required="true" autofocus :class="{ 'p-invalid': submitted && !student.name }" fluid />
                            <small class="p-error" v-if="submitted && !student.name">O nome é obrigatório.</small>
                        </div>

                        <div class="grid grid-cols-12 gap-4 mb-2">
                            <div class="col-span-12 xl:col-span-6">
                                <label class="block font-bold mb-3">Matrícula</label>
                                <InputText v-model.trim="student.registration_number" required="true" :class="{ 'p-invalid': submitted && !student.registration_number }" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-6">
                                <label class="block font-bold mb-3">Data de Nascimento</label>
                                <Calendar v-model="student.birth_date" dateFormat="dd/mm/yy" :showIcon="true" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-4">
                                <label class="block font-bold mb-3">Gênero</label>
                                <Dropdown v-model="student.gender" :options="[{label:'Masculino', value:'M'}, {label:'Feminino', value:'F'}]" optionLabel="label" optionValue="value" placeholder="Selecione" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-4">
                                <label class="block font-bold mb-3">CPF</label>
                                <InputMask v-model="student.cpf" mask="999.999.999-99" placeholder="000.000.000-00" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-4">
                                <label class="block font-bold mb-3">RG</label>
                                <InputText v-model="student.rg" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-12">
                                <label class="block font-bold mb-3">Nacionalidade</label>
                                <InputText v-model="student.nationality" fluid />
                            </div>
                        </div>
                    </TabPanel>

                    <TabPanel header="Endereço">
                        <div class="grid grid-cols-12 gap-4 mb-2">
                            <div class="col-span-12 xl:col-span-4">
                                <label class="block font-bold mb-3">CEP <i class="pi pi-search text-primary ml-1" v-tooltip="'Digite o CEP para buscar'"></i></label>
                                <InputMask v-model="student.zip_code" mask="99999-999" @blur="searchCep" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-8">
                                <label class="block font-bold mb-3">Logradouro (Rua/Av)</label>
                                <InputText v-model="student.street" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-4">
                                <label class="block font-bold mb-3">Número</label>
                                <InputText id="number" v-model="student.number" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-8">
                                <label class="block font-bold mb-3">Complemento</label>
                                <InputText v-model="student.complement" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-5">
                                <label class="block font-bold mb-3">Bairro</label>
                                <InputText v-model="student.neighborhood" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-5">
                                <label class="block font-bold mb-3">Cidade</label>
                                <InputText v-model="student.city" fluid />
                            </div>
                            <div class="col-span-12 xl:col-span-2">
                                <label class="block font-bold mb-3">UF</label>
                                <InputText v-model="student.state" fluid />
                            </div>
                        </div>
                    </TabPanel>

                    <TabPanel header="Saúde & Emergência">
                        <div class="mb-2">
                            <label class="block font-bold mb-3 text-red-500">Alergias</label>
                            <Textarea v-model="student.allergies" rows="3" autoResize placeholder="Lista de alergias..." fluid />
                        </div>
                        <div class="mb-2">
                            <label class="block font-bold mb-3">Medicamentos Contínuos</label>
                            <Textarea v-model="student.medications" rows="3" autoResize fluid />
                        </div>
                        <div class="mb-2">
                            <label class="block font-bold mb-3">Contato de Emergência (Nome e Telefone)</label>
                            <InputText v-model="student.emergency_contact" placeholder="Ex: Avó Maria - (11) 99999-9999" fluid />
                        </div>
                    </TabPanel>

                    <TabPanel header="Responsáveis (Pais)">
                        <div class="mb-2">
                            <label class="block font-bold mb-3">Vincular Responsáveis Cadastrados</label>
                            
                            <MultiSelect 
                                id="guardians"
                                v-model="student.guardians" 
                                :options="guardians" 
                                optionLabel="label" 
                                dataKey="id"
                                placeholder="Busque pelo nome ou CPF..." 
                                display="chip" 
                                filter
                                fluid
                            />
                            
                            <small class="block mt-2">
                                Não encontrou? <router-link to="/academic/guardians">Cadastre o Responsável aqui</router-link> antes de vincular.
                            </small>
                        </div>
                    </TabPanel>

                </TabView>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="studentDialog = false" />
                    <Button label="Salvar Prontuário" icon="pi pi-check" @click="saveStudent" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteStudentDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-items-center justify-content-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span>Deseja remover este aluno?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteStudentDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteStudent" />
                </template>
            </Dialog>
        </div>
    </div>
</template>