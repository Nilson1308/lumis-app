from rest_framework.pagination import PageNumberPagination

class DefaultPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class LargeResultsSetPagination(PageNumberPagination):
    """
    Use esta classe para Views que alimentam Dropdowns ou Relatórios
    onde precisamos de todos os registros de uma vez.
    """
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 10000