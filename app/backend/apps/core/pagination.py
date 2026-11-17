from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500

    def paginate_queryset(self, queryset, request, view=None):
        # Fără ordine stabilă, paginile se suprapun (rânduri dublate pe o pagină, lipsă pe alta). Se întâmplă când
        # lista e grupată (annotate cu Count / Sum anulează Meta.ordering): se pune ordinea modelului + id.
        if hasattr(queryset, "ordered") and not queryset.ordered:
            ordering = [*(queryset.model._meta.ordering or []), "pk"]
            queryset = queryset.order_by(*ordering)
        return super().paginate_queryset(queryset, request, view)
