<script setup>
import { ref, onMounted, computed } from 'vue';
import api from '@/service/api';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const transactions = ref([]);
const loading = ref(false);
const totalRecords = ref(0);
const lazyParams = ref({ page: 1, rows: 15 });

const todayIso = () => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const formatCurrency = (value) => {
    const num = Number(value);
    if (Number.isNaN(num)) return 'R$ 0,00';
    return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};

const formatDate = (value) => {
    if (!value) return '—';
    const [year, month, day] = value.split('-');
    return `${day}/${month}/${year}`;
};

const forecastTotal = computed(() =>
    transactions.value.reduce((sum, row) => sum + Number(row.valor_liquido || 0), 0)
);

const reconciliationSeverity = (status) => {
    if (status === 'RECONCILED') return 'success';
    if (status === 'DIVERGENCE') return 'danger';
    return 'warn';
};

const loadTransactions = async () => {
    loading.value = true;
    try {
        const params = {
            page: lazyParams.value.page,
            page_size: lazyParams.value.rows,
            settlement_from: todayIso(),
            ordering: 'settlement_date',
        };
        const res = await api.get('isaac-transactions/', { params });
        transactions.value = res.data?.results || res.data || [];
        totalRecords.value = res.data?.count ?? transactions.value.length;
    } catch {
        toast.add({
            severity: 'error',
            summary: 'Erro',
            detail: 'Não foi possível carregar a agenda de repasses.',
            life: 4000,
        });
    } finally {
        loading.value = false;
    }
};

const onPage = (event) => {
    lazyParams.value.page = event.page + 1;
    lazyParams.value.rows = event.rows;
    loadTransactions();
};

onMounted(loadTransactions);
</script>

<template>
    <div class="card">
        <Toast />
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
            <div>
                <h4 class="m-0 mb-1">Agenda Futura</h4>
                <p class="m-0 text-muted-color text-sm">
                    Previsão de repasses Isaac com liquidação a partir de hoje.
                </p>
            </div>
            <div class="finance-kpi-pill">
                <span class="text-muted-color text-sm">Total previsto nesta página</span>
                <strong class="text-primary text-lg">{{ formatCurrency(forecastTotal) }}</strong>
            </div>
        </div>

        <DataTable
            :value="transactions"
            :loading="loading"
            :lazy="true"
            :paginator="true"
            :rows="lazyParams.rows"
            :totalRecords="totalRecords"
            :rowsPerPageOptions="[10, 15, 25, 50]"
            dataKey="id"
            responsiveLayout="scroll"
            stripedRows
            @page="onPage"
        >
            <template #header>
                <span class="font-semibold">Repasses programados</span>
            </template>

            <template #empty>
                <div class="text-center py-6 text-muted-color">
                    Nenhum repasse futuro encontrado.
                </div>
            </template>

            <Column field="settlement_date" header="Liquidação" sortable>
                <template #body="{ data }">
                    <span class="font-medium">{{ formatDate(data.settlement_date) }}</span>
                </template>
            </Column>

            <Column field="competence_date" header="Competência">
                <template #body="{ data }">
                    {{ formatDate(data.competence_date) }}
                </template>
            </Column>

            <Column field="bruto" header="Bruto" bodyClass="text-right">
                <template #body="{ data }">
                    {{ formatCurrency(data.bruto) }}
                </template>
            </Column>

            <Column field="descontos" header="Descontos" bodyClass="text-right">
                <template #body="{ data }">
                    {{ formatCurrency(data.descontos) }}
                </template>
            </Column>

            <Column field="taxa_antecipacao" header="Antecipação" bodyClass="text-right">
                <template #body="{ data }">
                    <Tag
                        v-if="Number(data.taxa_antecipacao) > 0"
                        severity="warn"
                        :value="formatCurrency(data.taxa_antecipacao)"
                    />
                    <span v-else class="text-muted-color">—</span>
                </template>
            </Column>

            <Column field="valor_liquido" header="Líquido previsto" bodyClass="text-right">
                <template #body="{ data }">
                    <span class="font-semibold text-primary">{{ formatCurrency(data.valor_liquido) }}</span>
                </template>
            </Column>

            <Column field="reconciliation_status" header="Conciliação">
                <template #body="{ data }">
                    <Tag
                        :severity="reconciliationSeverity(data.reconciliation_status)"
                        :value="data.reconciliation_status_label || 'Pendente'"
                    />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<style scoped>
.finance-kpi-pill {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    padding: 0.75rem 1rem;
    border-radius: var(--content-border-radius, 8px);
    border: 1px solid var(--surface-border);
    background: color-mix(in srgb, var(--primary-color) 8%, var(--surface-card));
}
</style>
