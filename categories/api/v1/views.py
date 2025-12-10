from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from rest_framework import viewsets, permissions, pagination, filters
from categories.models import Category
from .serializers import CategorySerializer
from drf_spectacular.utils import extend_schema


class CategoryFilter(django_filters.FilterSet):
    """Filter for Category model"""
    type = django_filters.ChoiceFilter(choices=Category.CategoryType.choices)
    parent = django_filters.NumberFilter(field_name='parent__id', lookup_expr='exact')
    color = django_filters.CharFilter(field_name='color', lookup_expr='iexact')
    
    class Meta:
        model = Category
        fields = ['type', 'parent', 'color']


@extend_schema(tags=["Category"])
class CategoryVeiwSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(parent__isnull=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = pagination.PageNumberPagination

    filterset_class = CategoryFilter
    search_fields = ["name", "description"]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['name', 'created_at', 'edited_at']
    ordering = ['name']
