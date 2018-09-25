from rest_framework.pagination import PageNumberPagination


class StandardResultPagination(PageNumberPagination):
    """自定义分页类"""
    page_size = 2
    page_size_query_param = 'page_size'
    max_page_size = 20
