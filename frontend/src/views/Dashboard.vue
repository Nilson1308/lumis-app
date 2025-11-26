<script setup>
import { onMounted, ref } from 'vue';
import api from '@/service/api';

// Estados
const dashboardData = ref({
    cards: { students: 0, classes: 0, teachers: 0, risk: 0 },
    charts: { segment_distribution: [], subject_performance: [] }
});

// Configuração dos Gráficos (Chart.js)
const pieData = ref(null);
const barData = ref(null);
const chartOptions = ref({
    responsive: true,
    maintainAspectRatio: false
});

const loadDashboard = async () => {
    try {
        const res = await api.get('dashboard/data/'); // Ajuste a URL conforme seu urls.py
        const data = res.data;
        dashboardData.value = data;

        // Configura Gráfico de Pizza (Segmentos)
        const segments = data.charts.segment_distribution.map(i => i.enrollment__classroom__segment__name || 'Sem Turma');
        const totals = data.charts.segment_distribution.map(i => i.total);

        pieData.value = {
            labels: segments,
            datasets: [{
                data: totals,
                backgroundColor: ['#42A5F5', '#66BB6A', '#FFA726', '#AB47BC'],
                hoverBackgroundColor: ['#64B5F6', '#81C784', '#FFB74D', '#BA68C8']
            }]
        };

        // Configura Gráfico de Barras (Matérias)
        const subjects = data.charts.subject_performance.map(i => i.subject__name);
        const averages = data.charts.subject_performance.map(i => i.avg);

        barData.value = {
            labels: subjects,
            datasets: [{
                label: 'Média Geral da Escola',
                backgroundColor: '#2f4860',
                data: averages
            }]
        };

    } catch (e) {
        console.error("Erro ao carregar dashboard", e);
    }
};

onMounted(() => {
    loadDashboard();
});
</script>

<template>
    <div class="grid">
        <div class="col-12 lg:col-6 xl:col-3">
            <div class="card mb-0">
                <div class="flex justify-content-between mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-3">Total Alunos</span>
                        <div class="text-900 font-medium text-xl">{{ dashboardData.cards.students }}</div>
                    </div>
                    <div class="flex align-items-center justify-content-center bg-blue-100 border-round" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-users text-blue-500 text-xl"></i>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-12 lg:col-6 xl:col-3">
            <div class="card mb-0">
                <div class="flex justify-content-between mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-3">Turmas Ativas</span>
                        <div class="text-900 font-medium text-xl">{{ dashboardData.cards.classes }}</div>
                    </div>
                    <div class="flex align-items-center justify-content-center bg-orange-100 border-round" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-map-marker text-orange-500 text-xl"></i>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-12 lg:col-6 xl:col-3">
            <div class="card mb-0">
                <div class="flex justify-content-between mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-3">Professores</span>
                        <div class="text-900 font-medium text-xl">{{ dashboardData.cards.teachers }}</div>
                    </div>
                    <div class="flex align-items-center justify-content-center bg-cyan-100 border-round" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-id-card text-cyan-500 text-xl"></i>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-12 lg:col-6 xl:col-3">
            <div class="card mb-0">
                <div class="flex justify-content-between mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-3">Alunos em Risco</span>
                        <div class="text-900 font-medium text-xl">{{ dashboardData.cards.risk }}</div>
                    </div>
                    <div class="flex align-items-center justify-content-center bg-red-100 border-round" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-exclamation-circle text-red-500 text-xl"></i>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-12 xl:col-6">
            <div class="card">
                <h5>Distribuição por Segmento</h5>
                <Chart type="pie" :data="pieData" :options="chartOptions" class="w-full md:w-30rem" v-if="pieData" />
            </div>
        </div>
        <div class="col-12 xl:col-6">
            <div class="card">
                <h5>Desempenho por Matéria (Top 5)</h5>
                <Chart type="bar" :data="barData" :options="chartOptions" v-if="barData" />
            </div>
        </div>
    </div>
</template>