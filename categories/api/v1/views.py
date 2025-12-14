from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from rest_framework import viewsets, permissions, pagination, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from categories.models import Category
from .serializers import CategorySerializer, CategoryFlatSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter


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

    @extend_schema(
        summary="Get flat list of categories",
        description="Returns all categories in a flat list format (not hierarchical). "
                    "Useful for dropdowns and simple lists where you need all categories at once.",
        parameters=[
            OpenApiParameter(
                name='type',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by category type (expense or income)',
                enum=['expense', 'income'],
                required=False
            ),
        ],
        responses={200: CategoryFlatSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='flat', url_name='flat', pagination_class=None)
    def flat(self, request):
        """
        Get all categories in a flat list format.
        
        This endpoint returns all categories (both root and children) in a single
        flat list, without nested hierarchy. Useful for frontend components that
        need a simple list of all categories.
        
        Query parameters:
        - type: Filter by category type ('expense' or 'income')
        """
        queryset = Category.objects.all().select_related('parent')
        
        # Filter by type if provided
        category_type = request.query_params.get('type', None)
        if category_type:
            queryset = queryset.filter(type=category_type)
        
        # Apply search if provided
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Apply ordering
        ordering = request.query_params.get('ordering', 'name')
        if ordering.lstrip('-') in ['name', 'type', 'created_at', 'edited_at']:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('name')
        
        serializer = CategoryFlatSerializer(queryset, many=True)
        return Response(serializer.data)
