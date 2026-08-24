from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AccountsPayableViewSet,
    CostCenterViewSet,
    FinanceReportViewSet,
    FinancialCategoryViewSet,
    IsaacTransactionViewSet,
)

router = DefaultRouter()
router.register(r'cost-centers', CostCenterViewSet, basename='cost-centers')
router.register(r'financial-categories', FinancialCategoryViewSet, basename='financial-categories')
router.register(r'isaac-transactions', IsaacTransactionViewSet, basename='isaac-transactions')
router.register(r'accounts-payable', AccountsPayableViewSet, basename='accounts-payable')
router.register(r'finance-reports', FinanceReportViewSet, basename='finance-reports')

urlpatterns = [
    path('', include(router.urls)),
]
