<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();

// --- ESTADOS ---
const enrollments = ref([]);
const allClassrooms = ref([]); // Todas as turmas do banco
const availableYears = ref([]); // Anos extraídos das turmas (ex: [2024, 2025])
const students = ref([]);
const loading = ref(false);
const printDialog = ref(false);
const printOptions = ref([]);
const selectedPrintPeriod = ref(null);
const studentToPrint = ref(null);

// --- FILTROS SELECIONADOS ---
const selectedYear = ref(null);
const selectedClassroom = ref(null);

// --- DIALOGS ---
const enrollment = ref({});
const enrollmentDialog = ref(false);
const deleteDialog = ref(false);

// --- FILTROS DA TABELA (Busca Local) ---
const filters = ref({
    global: { value: null, matchMode: 'contains' } // <--- Use a string direta 'contains'
});

// --- COMPUTED: Filtrar turmas pelo ano selecionado ---
const filteredClassrooms = computed(() => {
    if (!selectedYear.value) return [];
    return allClassrooms.value.filter(c => c.year === selectedYear.value);
});

// Carrega os períodos e adiciona a opção "Final"
const loadPrintOptions = async () => {
    try {
        const res = await api.get('periods/');
        const periods = res.data.results || res.data;
        
        // Monta as opções do Dropdown
        printOptions.value = [
            { name: 'Boletim Final (Todos os Períodos)', id: null }, // ID null = Final
            ...periods // Espalha os bimestres (1º Bim, 2º Bim...)
        ];
    } catch (e) { console.error(e); }
};

// Abre o modal
const openPrintDialog = (enrollmentId) => {
    studentToPrint.value = enrollmentId;
    selectedPrintPeriod.value = null; // Padrão: Final
    if (printOptions.value.length === 0) loadPrintOptions(); // Carrega se não tiver
    printDialog.value = true;
};

// --- API: CARREGAR DADOS INICIAIS ---
const loadDependencies = async () => {
    try {
        // Carrega TODAS as turmas para montar a lógica de anos no front
        const resClasses = await api.get('classrooms/?page_size=1000');
        allClassrooms.value = resClasses.data.results;

        // Extrai anos únicos e ordena (2025, 2024...)
        const years = [...new Set(allClassrooms.value.map(c => c.year))];
        availableYears.value = years.sort((a, b) => b - a);
        
        // Seleciona o ano mais recente automaticamente
        if (availableYears.value.length > 0) {
            selectedYear.value = availableYears.value[0];
        }
    } catch (e) {
        console.error("Erro ao carregar turmas");
    }
};

// --- API: LISTAR MATRÍCULAS ---
const fetchEnrollments = async () => {
    if (!selectedClassroom.value) return;

    loading.value = true;
    try {
        const response = await api.get(`enrollments/?classroom=${selectedClassroom.value}&page_size=100`);
        enrollments.value = response.data.results;
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar lista.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// Se mudar o Ano, limpa a Turma
watch(selectedYear, () => {
    selectedClassroom.value = null;
    enrollments.value = [];
});

// Se mudar a Turma, carrega a lista
watch(selectedClassroom, () => {
    if (selectedClassroom.value) {
        fetchEnrollments();
    } else {
        enrollments.value = [];
    }
});

// --- API: BUSCAR ALUNOS (Para o cadastro) ---
const fetchStudents = async () => {
    if (students.value.length > 0) return;
    const res = await api.get('students/?page_size=1000'); // Limite alto para busca local no dropdown
    students.value = res.data.results;
};

// --- AÇÕES ---
const openNew = async () => {
    if (!selectedClassroom.value) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Selecione uma turma primeiro!', life: 3000 });
        return;
    }
    await fetchStudents();
    enrollment.value = { classroom: selectedClassroom.value };
    enrollmentDialog.value = true;
};

const confirmDelete = (item) => {
    enrollment.value = item;
    deleteDialog.value = true;
};

// --- SALVAR (Com Tratamento de Erro Inteligente) ---
const saveEnrollment = async () => {
    if (enrollment.value.student && enrollment.value.classroom) {
        try {
            await api.post('enrollments/', enrollment.value);
            
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aluno matriculado!', life: 3000 });
            enrollmentDialog.value = false;
            fetchEnrollments(); // Atualiza a lista
            
        } catch (error) {
            // AQUI ESTÁ A MELHORIA DO TOAST
            // O backend retorna arrays de erro. Pegamos a mensagem específica do serializer.
            let msg = 'Erro ao processar requisição.';
            
            if (error.response && error.response.data) {
                // Se o erro vier do validator (ex: "Aluno já matriculado...") ele vem em um array 'non_field_errors' ou direto
                const data = error.response.data;
                if (Array.isArray(data)) msg = data[0];
                else if (data.non_field_errors) msg = data.non_field_errors[0];
                else if (data.detail) msg = data.detail;
            }
            
            toast.add({ severity: 'error', summary: 'Conflito de Matrícula', detail: msg, life: 5000 });
        }
    }
};

const deleteEnrollment = async () => {
    try {
        await api.delete(`enrollments/${enrollment.value.id}/`);
        deleteDialog.value = false;
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Matrícula removida', life: 3000 });
        fetchEnrollments();
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao remover', life: 3000 });
    }
};

// Gera o PDF
const generatePDF = () => {
    let url = `reports/student_card/${studentToPrint.value}/`;
    
    // Se escolheu um período específico, adiciona na URL
    if (selectedPrintPeriod.value) {
        url += `?period=${selectedPrintPeriod.value}`;
    }

    loading.value = true;
    api.get(url, { responseType: 'blob' })
        .then(response => {
            const fileURL = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
            const fileLink = document.createElement('a');
            fileLink.href = fileURL;
            fileLink.setAttribute('target', '_blank');
            document.body.appendChild(fileLink);
            fileLink.click();
            printDialog.value = false; // Fecha modal
        })
        .catch(() => toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao gerar PDF' }))
        .finally(() => loading.value = false);
};

onMounted(() => {
    loadDependencies();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />

            <div class="flex flex-col md:flex-row gap-4 mb-4 align-end p-fluid">
                <div class="col-12 md:col-2">
                    <label class="block font-bold mb-2">Ano Letivo</label>
                    <Dropdown 
                        v-model="selectedYear" 
                        :options="availableYears" 
                        placeholder="Ano" 
                        fluid
                    />
                </div>

                <div class="col-12 md:col-6">
                    <label class="block font-bold mb-2">Turma</label>
                    <Dropdown 
                        v-model="selectedClassroom" 
                        :options="filteredClassrooms" 
                        optionLabel="name" 
                        optionValue="id" 
                        placeholder="Selecione a Turma..." 
                        :disabled="!selectedYear"
                        emptyMessage="Nenhuma turma neste ano"
                        fluid
                    />
                </div>

                <div class="col-12 md:col-4">
                    <label class="block font-bold mb-2">&nbsp;</label> <Button 
                        label="Nova Matrícula" 
                        icon="pi pi-plus" 
                        class="p-button-primary w-full" 
                        :disabled="!selectedClassroom"
                        @click="openNew" 
                    />
                </div>
            </div>

            <DataTable 
                v-if="selectedClassroom" 
                :value="enrollments" 
                :loading="loading" 
                responsiveLayout="scroll"
                :paginator="true"
                :rows="10"
                v-model:filters="filters"
                filterDisplay="row"
                :globalFilterFields="['student_name']"
            >
                <template #header>
                    <div class="flex flex-wrap gap-2 items-center justify-between">
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText v-model="filters['global'].value" placeholder="Buscar aluno nesta turma..." />
                        </IconField>
                    </div>
                </template>

                <template #empty>Nenhum aluno matriculado nesta turma.</template>
                
                <Column field="student_name" header="Aluno" sortable></Column>
                
                <Column field="date_enrolled" header="Data Matrícula">
                        <template #body="slotProps">
                        {{ new Date(slotProps.data.date_enrolled).toLocaleDateString('pt-BR') }}
                    </template>
                </Column>
                
                <Column header="Ações" style="width: 15%">
                    <template #body="slotProps">
                        <Button 
                            icon="pi pi-print" 
                            class="p-button-rounded mr-2" 
                            v-tooltip.top="'Imprimir Boletim'"
                            @click="openPrintDialog(slotProps.data.id)" 
                        />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDelete(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="enrollmentDialog" header="Matricular Aluno" :modal="true" :style="{ width: '450px' }">
                <div class="field">
                    <label class="mb-3 block font-bold">Selecione o Aluno</label>
                    <Dropdown 
                        v-model="enrollment.student" 
                        :options="students" 
                        optionLabel="name" 
                        optionValue="id" 
                        placeholder="Busque o aluno pelo nome..." 
                        filter 
                        class="w-full"
                    />
                </div>
                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="enrollmentDialog = false" />
                    <Button label="Matricular" icon="pi pi-check" @click="saveEnrollment" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" header="Remover Matrícula" :modal="true" :style="{ width: '450px' }">
                <div class="flex align-items-center justify-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span>Tem certeza que deseja remover este aluno desta turma?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteEnrollment" />
                </template>
            </Dialog>

            <Dialog v-model:visible="printDialog" header="Gerar Boletim" :modal="true" :style="{ width: '350px' }">
                <div class="field">
                    <label class="mb-3 block font-bold">Selecione o Tipo</label>
                    <Dropdown 
                        v-model="selectedPrintPeriod" 
                        :options="printOptions" 
                        optionLabel="name" 
                        optionValue="id" 
                        placeholder="Selecione..." 
                        class="w-full"
                    />
                </div>
                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="printDialog = false" />
                    <Button label="Gerar PDF" icon="pi pi-file-pdf" @click="generatePDF" :loading="loading" />
                </template>
            </Dialog>

        </div>
    </div>
</template>