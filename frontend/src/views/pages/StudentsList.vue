<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { FilterMatchMode } from '@primevue/core/api'; 
import PhotoCropperDialog from '@/components/PhotoCropperDialog.vue';
import api from '@/service/api';

const toast = useToast();
const students = ref([]);
const guardians = ref([]);
const extraActivities = ref([]); 
const student = ref({});
const studentDialog = ref(false);
const deleteStudentDialog = ref(false);
const loading = ref(true);
const submitted = ref(false);
const showCropper = ref(false);
const tempImageSrc = ref(null);
const photoFile = ref(null);

// --- VARIÁVEIS PARA PAGINAÇÃO SERVER-SIDE ---
const totalRecords = ref(0);
const lazyParams = ref({
    page: 1,
    rows: 10
});

// Filtro Local
const filters = ref({
    global: { value: '', matchMode: FilterMatchMode.CONTAINS }
});

// Opções para Selects
const periodOptions = ref([
    { label: 'Manhã', value: 'MORNING' },
    { label: 'Tarde', value: 'AFTERNOON' }
]);

const mealOptions = ref([
    { label: 'Não Optante', value: 'NONE' },
    { label: 'Almoço', value: 'LUNCH' },
    { label: 'Lanche', value: 'SNACK' },
    { label: 'Almoço + Lanche', value: 'BOTH' }
]);

// --- CARREGAR DADOS ---
const loadData = async () => {
    loading.value = true;
    try {
        const page = lazyParams.value.page;
        const rows = lazyParams.value.rows;
        
        let query = `students/?page=${page}&page_size=${rows}`;
        
        const searchValue = filters.value.global.value;
        if (searchValue && searchValue.trim() !== '') {
            query += `&search=${searchValue}`;
        }

        const resStudents = await api.get(query);
        students.value = resStudents.data.results; 
        totalRecords.value = resStudents.data.count;

        // Carrega auxiliares (Guardians e Activities) apenas uma vez
        if (guardians.value.length === 0) {
            const resGuardians = await api.get('guardians/?page_size=1000');
            const listaBruta = resGuardians.data.results || resGuardians.data;
            guardians.value = listaBruta.map(g => ({
                ...g,
                label: g.name ? `${g.name} ${g.cpf ? '(' + g.cpf + ')' : ''}` : `ID: ${g.id}`
            }));
        }

        if (extraActivities.value.length === 0) {
            const resActivities = await api.get('extra-activities/'); 
            extraActivities.value = resActivities.data.results || resActivities.data;
        }

    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados' });
    } finally {
        loading.value = false;
    }
};

const onPage = (event) => {
    lazyParams.value.page = event.page + 1;
    lazyParams.value.rows = event.rows;
    loadData();
};

const onSearch = () => {
    lazyParams.value.page = 1;
    loadData();
}

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
    student.value = { 
        nationality: 'Brasileira', 
        city: 'Mogi das Cruzes', 
        state: 'SP', 
        guardians: [],
        period: 'AFTERNOON',
        is_full_time: false,
        meals: 'NONE',
        extra_activities: []
    };
    submitted.value = false;
    studentDialog.value = true;
};

const onFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
        // Cria uma URL local para mostrar no Cropper
        tempImageSrc.value = URL.createObjectURL(file);
        showCropper.value = true;
        // Reseta o input para permitir selecionar a mesma foto se errar
        event.target.value = ''; 
    }
};

const onCropSave = (blob) => {
    // Guardamos o blob para enviar ao backend depois
    photoFile.value = blob;

    // (Opcional) Mostra preview na tela
    const previewUrl = URL.createObjectURL(blob);
    student.value.photo_preview = previewUrl; 
};

const editStudent = (prod) => {
    student.value = { ...prod };
    
    if (student.value.birth_date) {
        const parts = student.value.birth_date.split('-');
        student.value.birth_date = new Date(parts[0], parts[1] - 1, parts[2]);
    }

    if (student.value.guardians && Array.isArray(student.value.guardians)) {
        if (student.value.guardians.length > 0 && typeof student.value.guardians[0] === 'object') {
            student.value.guardians = student.value.guardians.map(g => g.id);
        }
    } else {
        student.value.guardians = [];
    }

    if (student.value.extra_activities_details) {
        student.value.extra_activities = student.value.extra_activities_details.map(a => a.id);
    } else if (!student.value.extra_activities) {
        student.value.extra_activities = [];
    }
    
    studentDialog.value = true;
};

const confirmDeleteStudent = (prod) => {
    student.value = prod;
    deleteStudentDialog.value = true;
};

const saveStudent = async () => {
    submitted.value = true;

    // Verifica campos obrigatórios
    if (student.value.name && student.value.registration_number) {
        
        const formData = new FormData();
        
        // 1. Campos Simples
        const simpleFields = [
            'name', 'registration_number', 'birth_date', 'gender', 'cpf', 'rg', 'nationality',
            'zip_code', 'street', 'number', 'complement', 'neighborhood', 'city', 'state',
            'allergies', 'medications', 'emergency_contact',
            'period', 'meals', 'is_full_time'
        ];

        simpleFields.forEach(field => {
            let val = student.value[field];
            
            // Tratamento de Data
            if (field === 'birth_date' && val instanceof Date) {
                val = val.toISOString().split('T')[0];
            }
            // Tratamento de Booleano
            if (field === 'is_full_time') {
                val = val ? 'true' : 'false';
            }
            // Apenas adiciona se tiver valor
            if (val !== undefined && val !== null) {
                formData.append(field, val);
            }
        });

        // 2. Relacionamentos (Arrays)
        if (student.value.guardians) {
            student.value.guardians.forEach(id => formData.append('guardians', id));
        }
        if (student.value.extra_activities) {
            student.value.extra_activities.forEach(id => formData.append('extra_activities', id));
        }

        // 3. Arquivos Documentais (Laudos/Receitas)
        if (student.value.medical_report instanceof File) {
            formData.append('medical_report', student.value.medical_report);
        }
        if (student.value.prescription instanceof File) {
            formData.append('prescription', student.value.prescription);
        }

        // 4. NOVA LÓGICA DA FOTO (Aqui está a mágica)
        // Se photoFile (ref criado no setup) tiver valor, anexa como arquivo
        if (photoFile.value) {
            formData.append('photo', photoFile.value, 'photo.jpg');
        }

        try {
            const config = { headers: { 'Content-Type': 'multipart/form-data' } };
            
            if (student.value.id) {
                await api.patch(`students/${student.value.id}/`, formData, config);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Atualizado com sucesso!', life: 3000 });
            } else {
                await api.post('students/', formData, config);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Criado com sucesso!', life: 3000 });
            }
            
            studentDialog.value = false;
            photoFile.value = null; // Limpa a foto temporária da memória
            loadData();
        } catch (error) {
            console.error(error);
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao salvar. Verifique os dados.', life: 3000 });
        }
    } else {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha Nome e Matrícula.', life: 3000 });
    }
};

const deleteStudent = async () => {
    try {
        await api.delete(`students/${student.value.id}/`);
        deleteStudentDialog.value = false;
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Removido!', life: 3000 });
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao remover.', life: 3000 });
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
                                <InputText 
                                    v-model="filters.global.value" 
                                    placeholder="Buscar por Nome, Matrícula ou CPF..." 
                                    @keydown.enter="onSearch"
                                    style="width: 300px" 
                                />
                            </IconField>
                            <Button icon="pi pi-search" class="p-button-rounded p-button-text ml-2" @click="onSearch" v-tooltip="'Pesquisar'" />
                            <Button icon="pi pi-refresh" class="p-button-rounded p-button-text" @click="loadData" v-tooltip="'Recarregar Tabela'" />
                        </div>
                    </div>
                </template>
                
                <Column field="registration_number" header="Matrícula"></Column>
                <Column field="name" header="Nome"></Column>
                
                <Column field="period" header="Período">
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.period === 'MORNING' ? 'Manhã' : 'Tarde'" 
                             :severity="slotProps.data.period === 'MORNING' ? 'info' : 'warning'" />
                    </template>
                </Column>
                <Column field="is_full_time" header="Integral">
                    <template #body="slotProps">
                        <i class="pi" :class="{'pi-check-circle text-green-500': slotProps.data.is_full_time, 'pi-times-circle text-gray-400': !slotProps.data.is_full_time}"></i>
                    </template>
                </Column>

                <Column field="birth_date" header="Nascimento">
                    <template #body="slotProps">
                        <span v-if="slotProps.data.birth_date">
                            {{ new Date(slotProps.data.birth_date + 'T00:00:00').toLocaleDateString('pt-BR') }}
                        </span>
                    </template>
                </Column>
                
                <Column header="Ações">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editStudent(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDeleteStudent(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="studentDialog" :style="{ width: '900px' }" header="Prontuário do Aluno" :modal="true" class="p-fluid" maximizable>
                
                <Tabs value="0">
                    <TabList>
                        <Tab value="0">Dados Pessoais</Tab>
                        <Tab value="1">Escolar & Rotina</Tab>
                        <Tab value="2">Endereço</Tab>
                        <Tab value="3">Saúde & Arquivos</Tab>
                        <Tab value="4">Responsáveis</Tab>
                    </TabList>
                    
                    <TabPanels>
                        <TabPanel value="0">
                            <div class="grid grid-cols-12 gap-4 mb-2">
                                <div class="col-span-12 xl:col-span-3">
                                    <div class="flex flex-col items-center mb-4">
                                        <div class="relative">
                                            <Avatar 
                                                :image="student.photo_preview || student.photo || '/public/default-avatar.png'" 
                                                size="xlarge" 
                                                shape="circle"
                                                style="object-fit: cover"
                                            />

                                            <div class="absolute bottom-0 right-0">
                                                <Button icon="pi pi-camera" class="p-button-rounded" @click="$refs.fileInput.click()" size="small" />
                                            </div>
                                        </div>

                                        <input 
                                            type="file" 
                                            ref="fileInput" 
                                            accept="image/*" 
                                            style="display: none" 
                                            @change="onFileSelect" 
                                        />
                                        <span class="text-sm text-center">Clique na câmera para alterar</span>
                                    </div>
                                </div>
                                <div class="col-span-12 xl:col-span-9">
                                    <label for="name" class="block font-bold mb-3">Nome Completo</label>
                                    <InputText id="name" v-model.trim="student.name" required="true" autofocus :class="{ 'p-invalid': submitted && !student.name }" fluid />
                                    <small class="p-error" v-if="submitted && !student.name">O nome é obrigatório.</small>
                                    <div class="grid grid-cols-12 gap-4 mb-2 mt-2">
                                        <div class="col-span-12 xl:col-span-6">
                                            <label class="block font-bold mb-3">Matrícula</label>
                                            <InputText v-model.trim="student.registration_number" required="true" :class="{ 'p-invalid': submitted && !student.registration_number }" fluid />
                                        </div>
                                        <div class="col-span-12 xl:col-span-6">
                                            <label class="block font-bold mb-3">Data de Nascimento</label>
                                            <DatePicker v-model="student.birth_date" dateFormat="dd/mm/yy" :showIcon="true" fluid />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <PhotoCropperDialog 
                                v-model:visible="showCropper" 
                                :imageSrc="tempImageSrc" 
                                @save="onCropSave" 
                            />

                            <Divider />

                            <div class="grid grid-cols-12 gap-4 mb-2">
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

                        <TabPanel value="1">
                            <div class="grid grid-cols-12 gap-4">
                                <div class="col-span-12 md:col-span-6">
                                    <label class="block font-bold mb-3">Período</label>
                                    <SelectButton v-model="student.period" :options="periodOptions" optionLabel="label" optionValue="value" />
                                </div>
                                
                                <div class="col-span-12 md:col-span-6 flex items-center">
                                    <div class="flex items-center gap-2 mt-6">
                                        <ToggleSwitch v-model="student.is_full_time" inputId="fulltime" />
                                        <label for="fulltime" class="font-bold cursor-pointer">Aluno Integral?</label>
                                    </div>
                                </div>

                                <div class="col-span-12">
                                    <label class="block font-bold mb-3">Plano de Refeições</label>
                                    <Dropdown v-model="student.meals" :options="mealOptions" optionLabel="label" optionValue="value" placeholder="Selecione..." fluid />
                                </div>

                                <div class="col-span-12">
                                    <label class="block font-bold mb-3">Atividades Extras</label>
                                    <MultiSelect 
                                        v-model="student.extra_activities" 
                                        :options="extraActivities" 
                                        optionLabel="name" 
                                        optionValue="id" 
                                        placeholder="Selecione as atividades" 
                                        display="chip" 
                                        filter
                                        fluid 
                                    />
                                </div>
                            </div>
                        </TabPanel>

                        <TabPanel value="2">
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

                        <TabPanel value="3">
                            <div class="mb-4">
                                <label class="block font-bold mb-3 text-red-500">Alergias</label>
                                <Textarea v-model="student.allergies" rows="3" autoResize fluid placeholder="Descreva alergias alimentares ou medicamentosas..." />
                            </div>
                            <div class="mb-4">
                                <label class="block font-bold mb-3">Medicamentos Contínuos</label>
                                <Textarea v-model="student.medications" rows="3" autoResize fluid />
                            </div>
                            <div class="mb-4">
                                <label class="block font-bold mb-3">Contato de Emergência</label>
                                <InputText v-model="student.emergency_contact" placeholder="Nome e Telefone" fluid />
                            </div>
                            
                            <Divider />
                            
                            <div class="grid grid-cols-12 gap-4">
                                <div class="col-span-12 md:col-span-6">
                                    <label class="block font-bold mb-3">Laudo Médico (PDF/IMG)</label>
                                    <FileUpload 
                                        mode="basic" 
                                        name="medical_report" 
                                        accept="image/*,.pdf" 
                                        :maxFileSize="2000000" 
                                        @select="(e) => onFileSelect(e, 'medical_report')" 
                                        :auto="false" 
                                        chooseLabel="Anexar Arquivo" 
                                    />
                                    
                                    <div v-if="student.medical_report && typeof student.medical_report === 'string'" 
                                        class="mt-3 p-2 bg-gray-50 border border-gray-200 rounded flex items-center gap-2">
                                        <i class="pi pi-check-circle text-green-500 text-xl"></i>
                                        <div class="flex flex-col">
                                            <span class="text-xs text-gray-500 font-semibold">ARQUIVO ATUAL</span>
                                            <a :href="student.medical_report" target="_blank" class="text-primary font-bold hover:underline flex items-center">
                                                Visualizar Laudo <i class="pi pi-external-link ml-1 text-xs"></i>
                                            </a>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="col-span-12 md:col-span-6">
                                    <label class="block font-bold mb-3">Receita Médica</label>
                                    <FileUpload 
                                        mode="basic" 
                                        name="prescription" 
                                        accept="image/*,.pdf" 
                                        :maxFileSize="2000000" 
                                        @select="(e) => onFileSelect(e, 'prescription')" 
                                        :auto="false" 
                                        chooseLabel="Anexar Receita" 
                                    />

                                    <div v-if="student.prescription && typeof student.prescription === 'string'" 
                                        class="mt-3 p-2 bg-gray-50 border border-gray-200 rounded flex items-center gap-2">
                                        <i class="pi pi-check-circle text-green-500 text-xl"></i>
                                        <div class="flex flex-col">
                                            <span class="text-xs text-gray-500 font-semibold">ARQUIVO ATUAL</span>
                                            <a :href="student.prescription" target="_blank" class="text-primary font-bold hover:underline flex items-center">
                                                Visualizar Receita <i class="pi pi-external-link ml-1 text-xs"></i>
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </TabPanel>

                        <TabPanel value="4">
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
                                <small class="block mt-2 text-gray-500">
                                    Não encontrou? <router-link to="/academic/guardians" class="text-primary font-bold hover:underline">Cadastre o Responsável aqui</router-link> antes de vincular.
                                </small>
                            </div>
                        </TabPanel>

                    </TabPanels>
                </Tabs>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="studentDialog = false" />
                    <Button label="Salvar Prontuário" icon="pi pi-check" @click="saveStudent" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteStudentDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-items-center justify-content-center">
                    <i class="pi pi-exclamation-triangle mr-3 text-yellow-500" style="font-size: 2rem" />
                    <span>Deseja remover este aluno?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteStudentDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text p-button-danger" @click="deleteStudent" />
                </template>
            </Dialog>
        </div>
    </div>
</template>

<style scoped>
.p-avatar-xl{
    width: 8rem !important;
    height: 8rem !important;
}
</style>