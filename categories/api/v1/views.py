from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets, permissions, pagination, filters
from categories.models import Category
from .serializers import CategorySerializer
from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Category"])
class CategoryVeiwSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(parent__isnull=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = pagination.PageNumberPagination

    filterset_fields = ["type"]
    search_fields = ["name", "description"]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
