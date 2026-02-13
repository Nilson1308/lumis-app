<script setup>
import { ref, computed, watch } from 'vue';
import api from '@/service/api';

const props = defineProps({
    visible: {
        type: Boolean,
        default: false
    },
    enrollmentId: {
        type: Number,
        required: true
    },
    studentName: {
        type: String,
        required: true
    },
    subjectId: {
        type: Number,
        default: null
    },
    isContraturno: {
        type: Boolean,
        default: false
    }
});

const emit = defineEmits(['update:visible']);

const loading = ref(false);
const stats = ref({
    periods: [],
    total: {
        absences: 0,
        presences: 0,
        total: 0
    }
});

const loadStats = async () => {
    if (!props.enrollmentId) return;
    
    loading.value = true;
    try {
        let endpoint = '';
        if (props.isContraturno) {
            endpoint = `contraturno-attendances/stats/?enrollment=${props.enrollmentId}`;
        } else {
            endpoint = `attendance/stats/?enrollment=${props.enrollmentId}&subject=${props.subjectId}`;
        }
        
        const res = await api.get(endpoint);
        stats.value = res.data;
    } catch (error) {
        console.error('Erro ao carregar estatísticas', error);
    } finally {
        loading.value = false;
    }
};

const absenceRate = computed(() => {
    if (stats.value.total.total === 0) return 0;
    return parseFloat(((stats.value.total.absences / stats.value.total.total) * 100).toFixed(1));
});

// Carrega estatísticas quando o dialog é aberto
watch(() => props.visible, (newVal) => {
    if (newVal) {
        loadStats();
    }
});
</script>

<template>
    <Dialog 
        :visible="props.visible"
        @update:visible="(value) => emit('update:visible', value)"
        :style="{ width: '600px' }" 
        :header="`Frequência - ${props.studentName}`"
        :modal="true"
        class="attendance-stats-dialog"
    >
        <div v-if="loading" class="text-center p-4">
            <i class="pi pi-spin pi-spinner text-2xl"></i>
            <p class="mt-2">Carregando estatísticas...</p>
        </div>

        <div v-else>
            <!-- Resumo Total - Cards -->
            <div class="grid mb-4">
                <div class="col-12 md:col-3">
                    <div class="card bg-green-50 dark:bg-green-900/20 border-round p-3 text-center">
                        <div class="text-3xl font-bold text-green-600 dark:text-green-400 mb-1">
                            {{ stats.total.presences }}
                        </div>
                        <div class="text-sm text-600 dark:text-400 font-medium">Presentes</div>
                    </div>
                </div>
                <div class="col-12 md:col-3">
                    <div class="card bg-red-50 dark:bg-red-900/20 border-round p-3 text-center">
                        <div class="text-3xl font-bold text-red-600 dark:text-red-400 mb-1">
                            {{ stats.total.absences }}
                        </div>
                        <div class="text-sm text-600 dark:text-400 font-medium">Faltas</div>
                    </div>
                </div>
                <div class="col-12 md:col-3">
                    <div class="card bg-blue-50 dark:bg-blue-900/20 border-round p-3 text-center">
                        <div class="text-3xl font-bold text-blue-600 dark:text-blue-400 mb-1">
                            {{ stats.total.total }}
                        </div>
                        <div class="text-sm text-600 dark:text-400 font-medium">Total</div>
                    </div>
                </div>
                <div class="col-12 md:col-3">
                    <div class="card border-round p-3 text-center" 
                         :class="absenceRate > 25 ? 'bg-red-50 dark:bg-red-900/20' : absenceRate > 15 ? 'bg-orange-50 dark:bg-orange-900/20' : 'bg-green-50 dark:bg-green-900/20'">
                        <div class="text-3xl font-bold mb-1"
                             :class="absenceRate > 25 ? 'text-red-600 dark:text-red-400' : absenceRate > 15 ? 'text-orange-600 dark:text-orange-400' : 'text-green-600 dark:text-green-400'">
                            {{ (100 - parseFloat(absenceRate)).toFixed(1) }}%
                        </div>
                        <div class="text-sm text-600 dark:text-400 font-medium">Frequência</div>
                    </div>
                </div>
            </div>

            <!-- Por Período -->
            <div v-if="stats.periods && stats.periods.length > 0" class="mt-4">
                <h4 class="mt-0 mb-3 text-900">Detalhamento por Período</h4>
                <DataTable :value="stats.periods" size="small" stripedRows class="p-datatable-sm">
                    <Column field="period_name" header="Período" style="min-width: 150px">
                        <template #body="slotProps">
                            <span class="font-semibold">{{ slotProps.data.period_name }}</span>
                        </template>
                    </Column>
                    <Column field="presences" header="Presentes" style="width: 100px">
                        <template #body="slotProps">
                            <span class="text-green-600 dark:text-green-400 font-semibold">{{ slotProps.data.presences }}</span>
                        </template>
                    </Column>
                    <Column field="absences" header="Faltas" style="width: 100px">
                        <template #body="slotProps">
                            <span class="text-red-600 dark:text-red-400 font-semibold">{{ slotProps.data.absences }}</span>
                        </template>
                    </Column>
                    <Column field="total" header="Total" style="width: 100px">
                        <template #body="slotProps">
                            <span class="font-semibold text-900">{{ slotProps.data.total }}</span>
                        </template>
                    </Column>
                    <Column header="Taxa" style="width: 100px">
                        <template #body="slotProps">
                            <span 
                                class="font-semibold"
                                :class="slotProps.data.total > 0 && (slotProps.data.absences / slotProps.data.total * 100) > 25 ? 'text-red-600' : 
                                        slotProps.data.total > 0 && (slotProps.data.absences / slotProps.data.total * 100) > 15 ? 'text-orange-600' : 'text-green-600'"
                            >
                                {{ slotProps.data.total > 0 ? (100 - (slotProps.data.absences / slotProps.data.total * 100)).toFixed(1) : 0 }}%
                            </span>
                        </template>
                    </Column>
                </DataTable>
            </div>

            <div v-else class="text-center p-4 text-600">
                Nenhum registro de frequência encontrado.
            </div>
        </div>

        <template #footer>
            <Button label="Fechar" icon="pi pi-times" @click="emit('update:visible', false)" class="p-button-text" />
        </template>
    </Dialog>
</template>
