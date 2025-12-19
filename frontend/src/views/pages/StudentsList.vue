<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const students = ref([]);
const guardians = ref([]);
const student = ref({});
const studentDialog = ref(false);
const deleteStudentDialog = ref(false);
const loading = ref(true);
const submitted = ref(false);

// --- VARIÁVEIS PARA PAGINAÇÃO SERVER-SIDE ---
const totalRecords = ref(0);
const lazyParams = ref({
    page: 1,
    rows: 10
});

const filters = ref({
    global: { value: null, matchMode: 'contains' },
});

// --- CARREGAR DADOS (COM PAGINAÇÃO REAL) ---
const loadData = async () => {
    loading.value = true;
    try {
        // 1. Monta a URL com a página correta
        const page = lazyParams.value.page;
        const rows = lazyParams.value.rows;
        
        // Ex: students/?page=1&page_size=10
        const resStudents = await api.get(`students/?page=${page}&page_size=${rows}`);
        
        // 2. Atualiza a tabela e o total de registros (para o paginador saber quantas páginas existem)
        students.value = resStudents.data.results; 
        totalRecords.value = resStudents.data.count; 

        // 3. Busca Responsáveis (apenas na primeira carga ou se estiver vazio)
        if (guardians.value.length === 0) {
            const resGuardians = await api.get('guardians/?page_size=1000');
            const listaBruta = resGuardians.data.results || resGuardians.data;
            guardians.value = listaBruta.map(g => ({
                ...g,
                label: g.name ? `${g.name} ${g.cpf ? '(' + g.cpf + ')' : ''}` : `ID: ${g.id}`
            }));
        }

    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados' });
    } finally {
        loading.value = false;
    }
};

// Evento disparado ao mudar de página na tabela
const onPage = (event) => {
    lazyParams.value.page = event.page + 1; // PrimeVue começa em 0, Django em 1
    lazyParams.value.rows = event.rows;
    loadData();
};

const searchCep = async () => {
    const cep = student.value.zip_code ? student.value.zip_code.replace(/\D/g, '') : '';
    if (cep.length !== 8) return;
    try {
        const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
        const data = await response.json();
        if (!data.erro) {
            student.value.street = data.logradouro;
            student.value.neighborhood = data.bairro;
            student.value.city = data.localidade;
            student.value.state = data.uf;
        }
    } catch (error) { console.error(error); }
};

const openNew = () => {
    student.value = { nationality: 'Brasileira', city: 'Mogi das Cruzes', state: 'SP', guardians: [] };
    submitted.value = false;
    studentDialog.value = true;
};

const editStudent = (prod) => {
    student.value = { ...prod };
    
    // Ajuste Data
    if (student.value.birth_date) {
        const parts = student.value.birth_date.split('-');
        student.value.birth_date = new Date(parts[0], parts[1] - 1, parts[2]);
    }

    // --- CORREÇÃO DO MULTISELECT ---
    // Verifica se os itens SÃO objetos antes de tentar acessar .id
    // Se a API já mandou [1, 5], não fazemos nada.
    if (student.value.guardians && Array.isArray(student.value.guardians)) {
        if (student.value.guardians.length > 0 && typeof student.value.guardians[0] === 'object') {
            student.value.guardians = student.value.guardians.map(g => g.id);
        }
        // Se já forem números, mantém como está.
    } else {
        student.value.guardians = [];
    }
    
    studentDialog.value = true;
};

const confirmDeleteStudent = (prod) => {
    student.value = prod;
    deleteStudentDialog.value = true;
};

const saveStudent = async () => {
    submitted.value = true;
    if (student.value.name && student.value.registration_number) {
        const payload = { ...student.value };
        
        if (payload.birth_date instanceof Date) {
            payload.birth_date = payload.birth_date.toISOString().split('T')[0];
        }

        // Garante envio apenas de IDs
        if (payload.guardians && payload.guardians.length > 0) {
            payload.guardians = payload.guardians.map(g => (g.id ? g.id : g));
        }

        try {
            if (student.value.id) {
                await api.put(`students/${student.value.id}/`, payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Atualizado!' });
            } else {
                await api.post('students/', payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Criado!' });
            }
            studentDialog.value = false;
            loadData(); // Recarrega a página atual
        } catch (error) {
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao salvar.' });
        }
    }
};

const deleteStudent = async () => {
    try {
        await api.delete(`students/${student.value.id}/`);
        deleteStudentDialog.value = false;
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Removido!' });
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao remover.' });
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

            <DataTable 
                :value="students" 
                :loading="loading" 
                responsiveLayout="scroll" 
                
                :paginator="true" 
                :rows="10"
                :totalRecords="totalRecords"
                :lazy="true"
                @page="onPage"
                
                :filters="filters"
            >
                <template #header>
                    <div class="flex flex-wrap gap-2 items-center justify-between">
                        <h4 class="m-0">Listagem de Alunos</h4>
                        <div class="flex gap-2">
                            <IconField>
                                <InputIcon>
                                    <i class="pi pi-search" />
                                </InputIcon>
                                <InputText v-model="filters['global'].value" placeholder="Buscar..." @input="onSearch" />
                            </IconField>
                            <Button icon="pi pi-refresh" class="p-button-rounded p-button-text" @click="loadData" />
                        </div>
                    </div>
                </template>
                
                <Column field="registration_number" header="Matrícula"></Column>
                <Column field="name" header="Nome"></Column>
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

            <Dialog v-model:visible="studentDialog" :style="{ width: '800px' }" header="Prontuário do Aluno" :modal="true" class="p-fluid" maximizable>
                
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
                                <DatePicker v-model="student.birth_date" dateFormat="dd/mm/yy" :showIcon="true" fluid />
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
                            <Editor v-model="student.allergies" rows="3" autoResize placeholder="Lista de alergias..." fluid editorStyle="height: 320px" />
                        </div>
                        <div class="mb-2">
                            <label class="block font-bold mb-3">Medicamentos Contínuos</label>
                            <Editor v-model="student.medications" rows="3" autoResize fluid editorStyle="height: 320px" />
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
                                optionValue="id"
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