<script setup>
import { ref, watch, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';
import PhotoCropperDialog from '@/components/PhotoCropperDialog.vue';
import StudentHistoryManager from '@/components/StudentHistoryManager.vue';

const props = defineProps({
    visible: Boolean,
    studentId: Number, // Se vier ID, é Edição. Se null, é Criação.
});

const emit = defineEmits(['update:visible', 'saved']);
const toast = useToast();

// --- ESTADO ---
const localVisible = ref(false);
const submitted = ref(false);
const showCropper = ref(false);
const tempImageSrc = ref(null);
const photoFile = ref(null);

// Objeto Aluno (Modelo vazio inicial)
const student = ref({
    name: '', registration_number: '', ra: '', birth_date: null, gender: null,
    cpf: '', rg: '', nationality: 'Brasileira',
    zip_code: '', street: '', number: '', complement: '', neighborhood: '', city: 'Mogi das Cruzes', state: 'SP',
    period: 'AFTERNOON', is_full_time: false, meals: 'NONE',
    allergies: '', medications: '', emergency_contact: '',
    image_authorization: null, exit_authorization: '', close_contacts: '',
    guardians: [],
    photo_preview: null // Apenas visual
});

// --- OPÇÕES (Dropdowns) ---
const periodOptions = [{ label: 'Manhã', value: 'MORNING' }, { label: 'Tarde', value: 'AFTERNOON' }];
const mealOptions = [
    { label: 'Não optante', value: 'NONE' },
    { label: 'Almoço', value: 'LUNCH' },
    { label: 'Lanche', value: 'SNACK' },
    { label: 'Almoço + Lanche', value: 'BOTH' }
];
const guardians = ref([]);

// --- WATCHERS ---
watch(() => props.visible, async (val) => {
    localVisible.value = val;
    if (val) {
        submitted.value = false;
        photoFile.value = null;
        if (props.studentId) {
            await loadStudent(props.studentId);
        } else {
            resetForm();
        }
        // Carrega auxiliares apenas se necessário
        if (guardians.value.length === 0) loadAuxiliaryData();
    }
});

watch(localVisible, (val) => {
    emit('update:visible', val);
});

// --- CARREGAMENTO DE DADOS ---
const loadAuxiliaryData = async () => {
    try {
        const gRes = await api.get('guardians/?page_size=1000');
        guardians.value = (gRes.data.results || gRes.data).map(g => ({ id: g.id, label: `${g.name} (CPF: ${g.cpf})` }));
    } catch (e) {
        console.error("Erro ao carregar auxiliares", e);
    }
};

const resetForm = () => {
    student.value = {
        name: '', registration_number: '', ra: '', nationality: 'Brasileira', city: 'Mogi das Cruzes', state: 'SP',
        period: 'AFTERNOON', is_full_time: false, meals: 'NONE',
        image_authorization: null, exit_authorization: '', close_contacts: '',
        guardians: [], photo_preview: null
    };
};

const loadStudent = async (id) => {
    try {
        const res = await api.get(`students/${id}/`);
        const data = res.data;
        // Tratamento de Data
        if (data.birth_date) data.birth_date = new Date(data.birth_date);
        student.value = data;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar aluno.', life: 3000 });
        localVisible.value = false;
    }
};

// --- AÇÕES DE MÍDIA (FOTO/ARQUIVOS) ---
const onFileSelect = (event, fieldName) => {
    const file = event.files ? event.files[0] : event.target.files[0];
    if (!file) return;

    if (fieldName === 'photo') {
        tempImageSrc.value = URL.createObjectURL(file);
        showCropper.value = true;
        event.target.value = ''; // Reset input
    } else {
        // Laudos e Receitas
        student.value[fieldName] = file;
    }
};

const onCropSave = (blob) => {
    photoFile.value = blob;
    student.value.photo_preview = URL.createObjectURL(blob);
};

// --- CEP ---
const searchCep = async () => {
    const cep = student.value.zip_code?.replace(/\D/g, '');
    if (cep?.length === 8) {
        try {
            const res = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
            const data = await res.json();
            if (!data.erro) {
                student.value.street = data.logradouro;
                student.value.neighborhood = data.bairro;
                student.value.city = data.localidade;
                student.value.state = data.uf;
                document.getElementById('number')?.focus();
            }
        } catch (e) { /* Silencioso */ }
    }
};

// --- SALVAR ---
const saveStudent = async () => {
    submitted.value = true;

    if (!student.value.name || !student.value.registration_number) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha Nome e Matrícula.', life: 3000 });
        return;
    }

    const formData = new FormData();
    // Campos Simples
    const fields = [
        'name', 'registration_number', 'ra', 'birth_date', 'gender', 'cpf', 'rg', 'nationality',
        'zip_code', 'street', 'number', 'complement', 'neighborhood', 'city', 'state',
        'period', 'meals', 'is_full_time', 'allergies', 'medications', 'emergency_contact',
        'image_authorization', 'exit_authorization', 'close_contacts'
    ];

    fields.forEach(f => {
        let val = student.value[f];
        if (f === 'birth_date' && val instanceof Date) val = val.toISOString().split('T')[0];
        if (f === 'is_full_time') val = val ? 'true' : 'false';
        if (f === 'image_authorization') {
            if (val === true) formData.append(f, 'true');
            else if (val === false) formData.append(f, 'false');
            return;
        }
        if (val !== null && val !== undefined) formData.append(f, val);
    });

    // Arrays
    if (student.value.guardians) student.value.guardians.forEach(id => formData.append('guardians', id));
    // Arquivos
    if (student.value.medical_report instanceof File) formData.append('medical_report', student.value.medical_report);
    if (student.value.prescription instanceof File) formData.append('prescription', student.value.prescription);
    if (photoFile.value) formData.append('photo', photoFile.value, 'photo.jpg');

    try {
        const config = { headers: { 'Content-Type': 'multipart/form-data' } };
        if (student.value.id) {
            await api.patch(`students/${student.value.id}/`, formData, config);
            toast.add({ severity: 'success', summary: 'Atualizado', detail: 'Prontuário salvo.', life: 3000 });
        } else {
            await api.post('students/', formData, config);
            toast.add({ severity: 'success', summary: 'Criado', detail: 'Aluno matriculado.', life: 3000 });
        }
        emit('saved'); // Avisa o pai para recarregar a lista
        localVisible.value = false;
    } catch (e) {
        console.error(e);
        const msg = e.response?.data?.registration_number ? 'Matrícula já existe.' : 'Erro ao salvar.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 3000 });
    }
};
</script>

<template>
    <Dialog 
        v-model:visible="localVisible" 
        :style="{ width: '900px' }" 
        :header="student.id ? 'Editar Prontuário' : 'Novo Aluno'" 
        :modal="true" 
        class="p-fluid" 
        maximizable
    >
        <Tabs value="0">
            <TabList>
                <Tab value="0">Dados Pessoais</Tab>
                <Tab value="1">Escolar & Rotina</Tab>
                <Tab value="2">Endereço</Tab>
                <Tab value="3">Saúde & Arquivos</Tab>
                <Tab value="4">Responsáveis</Tab>
                <Tab value="5">Histórico</Tab>
            </TabList>
            
            <TabPanels>
                <TabPanel value="0">
                    <div class="grid grid-cols-12 gap-4 mb-2">
                        <div class="col-span-12 xl:col-span-3">
                            <div class="flex flex-col items-center mb-4">
                                <div class="relative">
                                    <Avatar 
                                        :image="student.photo_preview || student.photo || '/default-avatar.png'" 
                                        size="xlarge" shape="circle" style="width: 150px; height: 150px; object-fit: cover"
                                        class="surface-200"
                                    />
                                    <div class="absolute bottom-0 right-0">
                                        <Button icon="pi pi-camera" class="p-button-rounded" @click="$refs.fileInput.click()" size="small" />
                                    </div>
                                </div>
                                <input type="file" ref="fileInput" accept="image/*" style="display: none" @change="(e) => onFileSelect(e, 'photo')" />
                                <span class="text-sm text-center mt-2">Clique na câmera</span>
                            </div>
                        </div>

                        <div class="col-span-12 xl:col-span-9">
                            <label for="name" class="block font-bold mb-3">Nome Completo</label>
                            <InputText id="name" v-model.trim="student.name" required="true" autofocus :class="{ 'p-invalid': submitted && !student.name }" fluid />
                            <small class="p-error" v-if="submitted && !student.name">Obrigatório.</small>
                            
                            <div class="grid grid-cols-12 gap-4 mt-3">
                                <div class="col-span-12 xl:col-span-4">
                                    <label class="block font-bold mb-3">Matrícula</label>
                                    <InputText v-model.trim="student.registration_number" :class="{ 'p-invalid': submitted && !student.registration_number }" fluid />
                                </div>
                                <div class="col-span-12 xl:col-span-4">
                                    <label class="block font-bold mb-3">RA (Registro do Aluno)</label>
                                    <InputText v-model.trim="student.ra" placeholder="Opcional" fluid />
                                </div>
                                <div class="col-span-12 xl:col-span-4">
                                    <label class="block font-bold mb-3">Data de Nascimento</label>
                                    <DatePicker v-model="student.birth_date" dateFormat="dd/mm/yy" showIcon fluid />
                                </div>
                            </div>
                        </div>
                    </div>

                    <Divider />

                    <div class="grid grid-cols-12 gap-4">
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
                    </div>
                </TabPanel>

                <TabPanel value="1">
                    <div class="grid grid-cols-12 gap-4">
                        <div class="col-span-12 md:col-span-6">
                            <label class="block font-bold mb-3">Período</label>
                            <SelectButton v-model="student.period" :options="periodOptions" optionLabel="label" optionValue="value" />
                        </div>
                        <div class="col-span-12 md:col-span-6 flex items-center pt-8">
                            <ToggleSwitch v-model="student.is_full_time" inputId="fulltime" />
                            <label for="fulltime" class="font-bold cursor-pointer ml-2">Aluno Integral?</label>
                        </div>
                        <div class="col-span-12">
                            <label class="block font-bold mb-3">Refeições</label>
                            <Dropdown v-model="student.meals" :options="mealOptions" optionLabel="label" optionValue="value" fluid />
                        </div>
                        <div class="col-span-12">
                            <small class="text-color-secondary">Matrículas em atividades extracurriculares são gerenciadas no módulo <strong>Atividades Extras</strong>.</small>
                        </div>
                    </div>
                </TabPanel>

                <TabPanel value="2">
                    <div class="grid grid-cols-12 gap-4">
                        <div class="col-span-4">
                            <label class="block font-bold mb-3">CEP</label>
                            <InputMask v-model="student.zip_code" mask="99999-999" @blur="searchCep" fluid />
                        </div>
                        <div class="col-span-8">
                            <label class="block font-bold mb-3">Logradouro</label>
                            <InputText v-model="student.street" fluid />
                        </div>
                        <div class="col-span-4">
                            <label class="block font-bold mb-3">Número</label>
                            <InputText id="number" v-model="student.number" fluid />
                        </div>
                        <div class="col-span-8">
                            <label class="block font-bold mb-3">Bairro</label>
                            <InputText v-model="student.neighborhood" fluid />
                        </div>
                         <div class="col-span-6">
                            <label class="block font-bold mb-3">Cidade</label>
                            <InputText v-model="student.city" fluid />
                        </div>
                         <div class="col-span-6">
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
                    <div class="mb-4">
                        <label class="block font-bold mb-3">Autorização de Imagem</label>
                        <Dropdown 
                            v-model="student.image_authorization" 
                            :options="[
                                { label: 'Sim', value: true },
                                { label: 'Não', value: false },
                                { label: 'Não informado', value: null }
                            ]" 
                            optionLabel="label" 
                            optionValue="value" 
                            placeholder="Selecione" 
                            fluid 
                        />
                        <small class="text-gray-500">Autoriza o uso de imagem do aluno em fotos, vídeos e redes sociais.</small>
                    </div>
                    
                    <Divider />
                    
                    <div class="grid grid-cols-12 gap-4">
                        <div class="col-span-12 md:col-span-6">
                            <label class="block font-bold mb-3">Laudo Médico (PDF/IMG)</label>
                            <FileUpload 
                                mode="basic" 
                                name="medical_report" 
                                accept="image/*,.pdf"
                                :maxFileSize="5000000" 
                                @select="(e) => onFileSelect(e, 'medical_report')" 
                                chooseLabel="Escolher Arquivo" 
                                :auto="false" 
                                class="w-full"
                            />
                            
                            <div v-if="student.medical_report && typeof student.medical_report === 'string'" 
                                 class="mt-3 p-3 surface-100 border-round flex items-center gap-3">
                                <i class="pi pi-file-pdf text-red-500 text-2xl"></i>
                                <div class="flex flex-col">
                                    <span class="text-xs text-500 font-bold uppercase mb-1">Arquivo Atual</span>
                                    <a :href="student.medical_report" target="_blank" class="text-primary font-bold hover:underline flex items-center gap-1">
                                        Visualizar Laudo <i class="pi pi-external-link text-xs"></i>
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
                                :maxFileSize="5000000" 
                                @select="(e) => onFileSelect(e, 'prescription')" 
                                chooseLabel="Escolher Arquivo" 
                                :auto="false" 
                                class="w-full"
                            />

                            <div v-if="student.prescription && typeof student.prescription === 'string'" 
                                 class="mt-3 p-3 surface-100 border-round flex items-center gap-3">
                                <i class="pi pi-file text-blue-500 text-2xl"></i>
                                <div class="flex flex-col">
                                    <span class="text-xs text-500 font-bold uppercase mb-1">Arquivo Atual</span>
                                    <a :href="student.prescription" target="_blank" class="text-primary font-bold hover:underline flex items-center gap-1">
                                        Visualizar Receita <i class="pi pi-external-link text-xs"></i>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </TabPanel>

                <TabPanel value="4">
                    <div class="mb-4">
                        <label class="block font-bold mb-3">Vincular Responsáveis</label>
                        <MultiSelect v-model="student.guardians" :options="guardians" optionLabel="label" optionValue="id" placeholder="Busque..." display="chip" filter fluid />
                        <small class="block mt-2 text-gray-500">
                             Não encontrou? Cadastre na tela de Responsáveis primeiro.
                        </small>
                    </div>
                    <div class="mb-4">
                        <label class="block font-bold mb-3">Autorização de Saída</label>
                        <Textarea v-model="student.exit_authorization" rows="3" autoResize fluid placeholder="Quem está autorizado a retirar o aluno da escola (ex.: Pai, Mãe, Avó Maria)" />
                    </div>
                    <div class="mb-2">
                        <label class="block font-bold mb-3">Contatos Próximos</label>
                        <Textarea v-model="student.close_contacts" rows="3" autoResize fluid placeholder="Pessoas de confiança, contatos próximos (texto livre)" />
                    </div>
                </TabPanel>

                <TabPanel value="5">
                    <StudentHistoryManager :studentId="student.id" v-if="student.id" />
                </TabPanel>
            </TabPanels>
        </Tabs>

        <template #footer>
            <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="localVisible = false" />
            <Button label="Salvar Prontuário" icon="pi pi-check" @click="saveStudent" />
        </template>
        
        <PhotoCropperDialog v-model:visible="showCropper" :imageSrc="tempImageSrc" @save="onCropSave" />
    </Dialog>
</template>