<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast'; // Adicionado Toast
import api from '@/service/api';

const route = useRoute();
const router = useRouter();
const toast = useToast();

const grades = ref([]);
const loading = ref(true);
const studentName = ref('');
const studentClass = ref('');
const studentId = ref(null);

// --- VARIÁVEIS PARA IMPRESSÃO (PDF) ---
const printDialog = ref(false);
const printOptions = ref([]);
const selectedPrintPeriod = ref(null);
const loadingPDF = ref(false);

onMounted(async () => {
    try {
        studentId.value = parseInt(route.params.id);
        loading.value = true;

        const [gradesResponse, childrenResponse] = await Promise.all([
            api.get(`students/${studentId.value}/report-card/`),
            api.get(`students/my-children/`)
        ]);

        // Dados do Aluno
        const currentStudent = childrenResponse.data.find(child => child.id === studentId.value);
        if (currentStudent) {
            studentName.value = currentStudent.name;
            studentClass.value = currentStudent.classroom_name || 'Sem Turma';
        }

        // Processamento das Notas
        grades.value = gradesResponse.data.map(row => {
            const n1 = parseGrade(row['1']);
            const n2 = parseGrade(row['2']);
            const n3 = parseGrade(row['3']);
            const n4 = parseGrade(row['4']);

            if (n1 !== null && n2 !== null && n3 !== null && n4 !== null) {
                const avg = (n1 + n2 + n3 + n4) / 4;
                row.final = avg.toFixed(1);
            } else {
                row.final = '-';
            }
            return row;
        });

    } catch (e) {
        console.error("Erro ao carregar boletim:", e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Não foi possível carregar os dados.' });
    } finally {
        loading.value = false;
    }
});

const parseGrade = (value) => {
    if (!value || value === '-') return null;
    if (typeof value === 'number') return value;
    return parseFloat(value.toString().replace(',', '.'));
};

const goBack = () => router.push({ name: 'parent-dashboard' });

// --- LÓGICA DE IMPRESSÃO (IGUAL AO ENROLLMENT LIST) ---

const openPrintDialog = async () => {
    // Carrega as opções de período apenas se ainda não carregou
    if (printOptions.value.length === 0) {
        try {
            const res = await api.get('periods/');
            const periods = res.data.results || res.data;
            printOptions.value = [
                { name: 'Boletim Completo (Final)', id: null }, 
                ...periods
            ];
        } catch (e) {
            console.error(e);
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar opções de impressão.' });
        }
    }
    
    selectedPrintPeriod.value = null; // Reset para "Completo"
    printDialog.value = true;
};

const generatePDF = () => {
    if (!studentId.value) return;

    let url = `reports/student_card/${studentId.value}/`;
    
    // Se escolheu um período específico, adiciona na URL
    if (selectedPrintPeriod.value) {
        url += `?period=${selectedPrintPeriod.value}`;
    }

    loadingPDF.value = true;

    api.get(url, { responseType: 'blob' })
        .then(response => {
            const fileURL = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
            const fileLink = document.createElement('a');
            fileLink.href = fileURL;
            fileLink.setAttribute('target', '_blank'); // Abre em nova aba
            document.body.appendChild(fileLink);
            fileLink.click();
            printDialog.value = false; // Fecha modal
        })
        .catch(() => {
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao gerar o PDF.' });
        })
        .finally(() => {
            loadingPDF.value = false;
        });
};
</script>

<template>
    <div class="card">
        <Toast />

        <div class="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
            <div class="flex items-center gap-2 self-start md:self-auto">
                <Button icon="pi pi-arrow-left" class="p-button-rounded p-button-text" @click="goBack" />
                <div>
                    <span class="block text-xl font-bold">Boletim Escolar</span>
                    <span class="text-sm text-gray-500 hidden md:inline">Acompanhamento acadêmico</span>
                </div>
            </div>
            
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div class="text-right flex-grow-1 md:flex-grow-0">
                    <div class="text-900 font-bold text-lg">{{ studentName }}</div>
                    <div class="text-600">{{ studentClass }}</div>
                </div>
                
                <Button 
                    label="Imprimir" 
                    icon="pi pi-print" 
                    class="p-button-outlined" 
                    @click="openPrintDialog" 
                />
            </div>
        </div>

        <DataTable :value="grades" :loading="loading" responsiveLayout="scroll" stripedRows showGridlines>
            <Column field="subject" header="Disciplina" sortable class="font-bold text-900"></Column>
            
            <Column field="1" header="1º Bim" class="text-center" style="width: 8.8%">
                <template #body="slotProps">
                    <span :class="{'text-red-500 font-bold': parseGrade(slotProps.data['1']) < 6}">
                        {{ slotProps.data['1'] }}
                    </span>
                </template>
            </Column>
            
            <Column field="2" header="2º Bim" class="text-center" style="width: 8.8%">
                <template #body="slotProps">
                    <span :class="{'text-red-500 font-bold': parseGrade(slotProps.data['2']) < 6}">
                        {{ slotProps.data['2'] }}
                    </span>
                </template>
            </Column>
            
            <Column field="3" header="3º Bim" class="text-center" style="width: 8.8%">
                <template #body="slotProps">
                    <span :class="{'text-red-500 font-bold': parseGrade(slotProps.data['3']) < 6}">
                        {{ slotProps.data['3'] }}
                    </span>
                </template>
            </Column>
            
            <Column field="4" header="4º Bim" class="text-center" style="width: 8.8%">
                <template #body="slotProps">
                    <span :class="{'text-red-500 font-bold': parseGrade(slotProps.data['4']) < 6}">
                        {{ slotProps.data['4'] }}
                    </span>
                </template>
            </Column>
            
            <Column field="final" header="Média" class="text-center font-bold bg-gray-50" style="width: 8.8%">
                <template #body="slotProps">
                    <span v-if="slotProps.data.final !== '-'" 
                          class="px-2 py-1 border-round"
                          :class="slotProps.data.final < 6 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'">
                        {{ slotProps.data.final }}
                    </span>
                    <span v-else>-</span>
                </template>
            </Column>
        </DataTable>
        
        <div class="mt-4 text-xs text-gray-500 flex gap-4 justify-end">
            <div class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-green-500 block"></span> Aprovado (>= 6.0)</div>
            <div class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-red-500 block"></span> Abaixo da Média</div>
        </div>

        <Dialog v-model:visible="printDialog" header="Gerar Boletim (PDF)" :modal="true" :style="{ width: '350px' }">
            <div class="field">
                <label class="mb-3 block font-bold">Selecione o Período</label>
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
                <Button label="Baixar PDF" icon="pi pi-download" @click="generatePDF" :loading="loadingPDF" />
            </template>
        </Dialog>

    </div>
</template>