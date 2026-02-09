<script setup>
import { onMounted, ref, watch } from 'vue';
import { useLayout } from '@/layout/composables/layout';
import api from '@/service/api';

const { getPrimary, getSurface, isDarkTheme } = useLayout();

// Estado dos Dados
const role = ref(null); // 'coordinator' ou 'teacher'
const cards = ref({ students: 0, classes: 0, teachers: 0, risk: 0, subjects: 0 });

// Configuração dos Gráficos
const barPerformanceData = ref(null);
const barPerformanceOptions = ref(null);

const donutSegmentData = ref(null);
const donutSegmentOptions = ref(null);

const barClassData = ref(null);
const barClassOptions = ref(null);

const loading = ref(true);

onMounted(() => {
    loadDashboard();
});

// Recarrega cores quando o tema muda (Dark/Light)
watch([getPrimary, getSurface, isDarkTheme], () => {
    if (!loading.value) updateChartColors();
});

const loadDashboard = async () => {
    try {
        const res = await api.get('dashboard/data/');
        const data = res.data;
        
        role.value = data.role;
        cards.value = data.cards;

        // Prepara dados brutos para os gráficos
        prepareCharts(data.charts);
        
        // Aplica estilos
        updateChartColors();

    } catch (e) {
        console.error("Erro ao carregar dashboard", e);
    } finally {
        loading.value = false;
    }
};

// Variáveis temporárias para armazenar dados antes de aplicar cores
let rawPerformance = [];
let rawSegments = [];
let rawClasses = [];

const prepareCharts = (chartsData) => {
    // 1. Performance (Usado por ambos)
    if (chartsData.subject_performance) {
        rawPerformance = {
            labels: chartsData.subject_performance.map(i => i.subject__name),
            data: chartsData.subject_performance.map(i => i.avg)
        };
    }

    // 2. Segmentos (Só Coordenação)
    if (chartsData.segment_distribution) {
        rawSegments = {
            labels: chartsData.segment_distribution.map(i => i.enrollment__classroom__segment__name || 'N/A'),
            data: chartsData.segment_distribution.map(i => i.total)
        };
    }

    // 3. Alunos por Turma (Usado por ambos)
    if (chartsData.students_per_class) {
        rawClasses = {
            labels: chartsData.students_per_class.map(i => i.name),
            data: chartsData.students_per_class.map(i => i.total)
        };
    }
};

const updateChartColors = () => {
    const documentStyle = getComputedStyle(document.documentElement);
    const textColor = documentStyle.getPropertyValue('--text-color');
    const textColorSecondary = documentStyle.getPropertyValue('--text-color-secondary');
    const surfaceBorder = documentStyle.getPropertyValue('--surface-border');
    const primaryColor = documentStyle.getPropertyValue('--p-primary-500');
    const primaryLight = documentStyle.getPropertyValue('--p-primary-200');

    // --- GRÁFICO 1: Desempenho por Matéria (Barra Vertical) ---
    if (rawPerformance.labels) {
        barPerformanceData.value = {
            labels: rawPerformance.labels,
            datasets: [
                {
                    label: 'Média de Notas',
                    backgroundColor: primaryColor,
                    borderColor: primaryColor,
                    data: rawPerformance.data,
                    barThickness: 30,
                    borderRadius: 4
                }
            ]
        };
        barPerformanceOptions.value = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: textColor } } },
            scales: {
                x: { ticks: { color: textColorSecondary }, grid: { display: false } },
                y: { ticks: { color: textColorSecondary }, grid: { color: surfaceBorder } }
            }
        };
    }

    // --- GRÁFICO 2: Segmentos (Donut) ---
    if (rawSegments.labels) {
        donutSegmentData.value = {
            labels: rawSegments.labels,
            datasets: [
                {
                    data: rawSegments.data,
                    backgroundColor: [
                        documentStyle.getPropertyValue('--p-indigo-500'),
                        documentStyle.getPropertyValue('--p-purple-500'),
                        documentStyle.getPropertyValue('--p-teal-500'),
                        documentStyle.getPropertyValue('--p-orange-500')
                    ],
                    hoverBackgroundColor: [
                        documentStyle.getPropertyValue('--p-indigo-400'),
                        documentStyle.getPropertyValue('--p-purple-400'),
                        documentStyle.getPropertyValue('--p-teal-400'),
                        documentStyle.getPropertyValue('--p-orange-400')
                    ]
                }
            ]
        };
        donutSegmentOptions.value = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { usePointStyle: true, color: textColor } } }
        };
    }

    // --- GRÁFICO 3: Alunos por Turma (Barra Horizontal para variar) ---
    if (rawClasses.labels) {
        barClassData.value = {
            labels: rawClasses.labels,
            datasets: [
                {
                    label: 'Qtd. Alunos',
                    backgroundColor: primaryLight,
                    borderColor: primaryLight,
                    data: rawClasses.data,
                    borderRadius: 4,
                    barThickness: 20
                }
            ]
        };
        barClassOptions.value = {
            indexAxis: 'y', // Barra Horizontal
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: textColorSecondary }, grid: { color: surfaceBorder } },
                y: { ticks: { color: textColorSecondary }, grid: { display: false } }
            }
        };
    }
};
</script>

<template>
    <div class="grid grid-cols-12 gap-8">
        
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-3">Total Alunos</span>
                        <div class="text-900 font-medium text-xl">{{ cards.students }}</div>
                    </div>
                    <div class="flex items-center justify-center bg-blue-100 dark:bg-blue-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-users text-blue-500 text-xl"></i>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-3">Turmas Ativas</span>
                        <div class="text-900 font-medium text-xl">{{ cards.classes }}</div>
                    </div>
                    <div class="flex items-center justify-center bg-orange-100 dark:bg-orange-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-map-marker text-orange-500 text-xl"></i>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-3">
                            {{ role === 'coordinator' ? 'Professores' : 'Minhas Matérias' }}
                        </span>
                        <div class="text-900 font-medium text-xl">
                            {{ role === 'coordinator' ? cards.teachers : cards.subjects }}
                        </div>
                    </div>
                    <div class="flex items-center justify-center bg-cyan-100 dark:bg-cyan-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-id-card text-cyan-500 text-xl"></i>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-3">Alunos em Risco (+5 Faltas)</span>
                        <div class="text-900 font-medium text-xl">{{ cards.risk }}</div>
                    </div>
                    <div class="flex items-center justify-center bg-red-100 dark:bg-red-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-exclamation-triangle text-red-500 text-xl"></i>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-span-12 xl:col-span-6">
            <div class="card h-full">
                <div class="font-semibold text-xl mb-4">Top 5 - Médias por Matéria</div>
                <Chart type="bar" :data="barPerformanceData" :options="barPerformanceOptions" class="h-80" />
            </div>
        </div>

        <div class="col-span-12 xl:col-span-6">
            <div class="card h-full flex flex-col items-center justify-center" v-if="role === 'coordinator'">
                <div class="font-semibold text-xl mb-4 self-start">Alunos por Segmento</div>
                <Chart type="doughnut" :data="donutSegmentData" :options="donutSegmentOptions" class="h-80 w-full" />
            </div>

            <div class="card h-full" v-else>
                <div class="font-semibold text-xl mb-4">Alunos por Turma</div>
                <Chart type="bar" :data="barClassData" :options="barClassOptions" class="h-80" />
            </div>
        </div>

        <div class="col-span-12" v-if="role === 'coordinator'">
            <div class="card">
                <div class="font-semibold text-xl mb-4">Lotação das Turmas</div>
                <Chart type="bar" :data="barClassData" :options="barClassOptions" class="h-[25rem]" />
            </div>
        </div>

    </div>
</template>