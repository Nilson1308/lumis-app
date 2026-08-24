<script setup>
import { ref, onMounted, computed } from 'vue';
import api from '@/service/api';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const loading = ref(false);
const report = ref(null);
const futureTransactions = ref([]);

const formatCurrency = (value) => {
    const num = Number(value);
    if (Number.isNaN(num)) return 'R$ 0,00';
    return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};

const todayIso = () => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const normalForecast = computed(() => {
    return futureTransactions.value
        .filter((row) => !Number(row.taxa_antecipacao))
        .reduce((sum, row) => sum + Number(row.valor_liquido || 0), 0);
});

const anticipationForecast = computed(() => {
    return futureTransactions.value
        .filter((row) => Number(row.taxa_antecipacao) > 0)
        .reduce((sum, row) => sum + Number(row.valor_liquido || 0), 0);
});

const anticipationFees = computed(() => {
    return futureTransactions.value
        .filter((row) => Number(row.taxa_antecipacao) > 0)
        .reduce((sum, row) => sum + Number(row.taxa_antecipacao || 0), 0);
});

const loadCashFlow = async () => {
    loading.value = true;
    try {
        const [reportRes, isaacRes] = await Promise.all([
            api.get('finance-reports/cash-flow/'),
            api.get('isaac-transactions/', {
                params: {
                    settlement_from: todayIso(),
                    page_size: 500,
                    ordering: 'settlement_date',
                },
            }),
        ]);
        report.value = reportRes.data;
        futureTransactions.value = isaacRes.data?.results || isaacRes.data || [];
    } catch {
        toast.add({
            severity: 'error',
            summary: 'Erro',
            detail: 'Não foi possível carregar o fluxo de caixa.',
            life: 4000,
        });
    } finally {
        loading.value = false;
    }
};

onMounted(loadCashFlow);
</script>

<template>
    <div class="flex flex-col gap-5">
        <Toast />

        <div>
            <h4 class="m-0 mb-1">Fluxo de Caixa</h4>
            <p class="m-0 text-muted-color text-sm">
                Consolidação bancária, previsões Isaac e contas a pagar
                <span v-if="report?.reference_date"> — referência {{ report.reference_date.split('-').reverse().join('/') }}</span>
            </p>
        </div>

        <div v-if="loading" class="flex justify-center py-10">
            <ProgressSpinner />
        </div>

        <template v-else-if="report">
            <div class="grid grid-cols-12 gap-4">
                <div class="col-span-12 md:col-span-6 xl:col-span-3">
                    <Card class="finance-card finance-card--primary h-full">
                        <template #title>
                            <div class="flex items-center gap-2">
                                <i class="pi pi-building-columns text-primary" />
                                <span>Saldo bancário</span>
                            </div>
                        </template>
                        <template #content>
                            <p class="finance-card__value">{{ formatCurrency(report.saldo_bancario) }}</p>
                            <p class="finance-card__hint">Entradas registradas no banco</p>
                        </template>
                    </Card>
                </div>

                <div class="col-span-12 md:col-span-6 xl:col-span-3">
                    <Card class="finance-card h-full">
                        <template #title>
                            <div class="flex items-center gap-2">
                                <i class="pi pi-calendar text-secondary" />
                                <span>Previsões Isaac</span>
                            </div>
                        </template>
                        <template #content>
                            <p class="finance-card__value">{{ formatCurrency(report.previsoes_isaac_liquidas) }}</p>
                            <p class="finance-card__hint">Repasses pendentes de liquidação</p>
                        </template>
                    </Card>
                </div>

                <div class="col-span-12 md:col-span-6 xl:col-span-3">
                    <Card class="finance-card h-full">
                        <template #title>
                            <div class="flex items-center gap-2">
                                <i class="pi pi-wallet text-secondary" />
                                <span>Contas a pagar</span>
                            </div>
                        </template>
                        <template #content>
                            <p class="finance-card__value text-red-500">{{ formatCurrency(report.contas_a_pagar) }}</p>
                            <p class="finance-card__hint">Obrigações em aberto</p>
                        </template>
                    </Card>
                </div>

                <div class="col-span-12 md:col-span-6 xl:col-span-3">
                    <Card class="finance-card finance-card--highlight h-full">
                        <template #title>
                            <div class="flex items-center gap-2">
                                <i class="pi pi-chart-line text-primary" />
                                <span>Saldo consolidado</span>
                            </div>
                        </template>
                        <template #content>
                            <p class="finance-card__value text-primary">{{ formatCurrency(report.saldo_consolidado) }}</p>
                            <p class="finance-card__hint">Banco + previsões − contas a pagar</p>
                        </template>
                    </Card>
                </div>
            </div>

            <div class="grid grid-cols-12 gap-4">
                <div class="col-span-12 lg:col-span-6">
                    <Card class="finance-card finance-card--normal h-full">
                        <template #title>
                            <div class="flex items-center justify-between gap-2 flex-wrap">
                                <div class="flex items-center gap-2">
                                    <i class="pi pi-arrow-down-left text-primary" />
                                    <span>Recebimentos normais</span>
                                </div>
                                <Tag severity="info" value="Operacional" />
                            </div>
                        </template>
                        <template #content>
                            <p class="finance-card__value">{{ formatCurrency(normalForecast) }}</p>
                            <p class="finance-card__hint mb-3">
                                Repasses futuros sem antecipação — base recorrente do caixa projetado.
                            </p>
                            <div class="finance-card__detail">
                                <span>Previsões Isaac (API)</span>
                                <strong>{{ formatCurrency(report.previsoes_isaac_liquidas) }}</strong>
                            </div>
                            <div class="finance-card__detail">
                                <span>Antecipações isoladas (mês)</span>
                                <strong>{{ formatCurrency(report.antecipacoes_isoladas) }}</strong>
                            </div>
                        </template>
                    </Card>
                </div>

                <div class="col-span-12 lg:col-span-6">
                    <Card class="finance-card finance-card--anticipation h-full">
                        <template #title>
                            <div class="flex items-center justify-between gap-2 flex-wrap">
                                <div class="flex items-center gap-2">
                                    <i class="pi pi-bolt text-orange-500" />
                                    <span>Antecipações</span>
                                </div>
                                <Tag severity="warn" value="Isolado" />
                            </div>
                        </template>
                        <template #content>
                            <p class="finance-card__value text-orange-600 dark:text-orange-400">
                                {{ formatCurrency(anticipationForecast || report.antecipacoes_isoladas) }}
                            </p>
                            <p class="finance-card__hint mb-3">
                                Entradas antecipadas separadas dos recebimentos normais para evitar distorção do saldo.
                            </p>
                            <div class="finance-card__detail">
                                <span>Taxas de antecipação</span>
                                <strong>{{ formatCurrency(anticipationFees || report.taxas_antecipacao) }}</strong>
                            </div>
                            <div class="finance-card__detail">
                                <span>Caixa antecipado (mês corrente)</span>
                                <strong>{{ formatCurrency(report.antecipacoes_isoladas) }}</strong>
                            </div>
                        </template>
                    </Card>
                </div>
            </div>
        </template>
    </div>
</template>

<style scoped>
.finance-card :deep(.p-card) {
    border: 1px solid var(--surface-border);
    background: var(--surface-card);
    box-shadow: none;
}

.finance-card :deep(.p-card-title) {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-color);
}

.finance-card :deep(.p-card-body) {
    padding-top: 0.5rem;
}

.finance-card--primary :deep(.p-card) {
    border-color: color-mix(in srgb, var(--primary-color) 35%, var(--surface-border));
    background: color-mix(in srgb, var(--primary-color) 6%, var(--surface-card));
}

.finance-card--highlight :deep(.p-card) {
    border-color: color-mix(in srgb, var(--primary-color) 45%, var(--surface-border));
    background: color-mix(in srgb, var(--primary-color) 10%, var(--surface-card));
}

.finance-card--normal :deep(.p-card) {
    border-left: 4px solid var(--primary-color);
}

.finance-card--anticipation :deep(.p-card) {
    border-left: 4px solid var(--secondary-color);
    background: color-mix(in srgb, var(--secondary-color) 6%, var(--surface-card));
}

.finance-card__value {
    margin: 0;
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.2;
    color: var(--text-color);
}

.finance-card__hint {
    margin: 0.35rem 0 0;
    font-size: 0.875rem;
    color: var(--text-color-secondary);
}

.finance-card__detail {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 0;
    border-top: 1px solid var(--surface-border);
    font-size: 0.875rem;
    color: var(--text-color-secondary);
}

.finance-card__detail strong {
    color: var(--text-color);
}

.text-secondary {
    color: var(--secondary-color);
}
</style>
