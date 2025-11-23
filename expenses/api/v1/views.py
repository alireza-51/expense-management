from rest_framework import viewsets, permissions
from categories.models import Category
from expenses.models import Income, Expense
from .serializers import IncomeSerializer, ExpenseSerializer
from drf_spectacular.utils import extend_schema


class BaseTransactionViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for filtering by workspace and setting created_by/workspace automatically.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        workspace = getattr(self.request, 'workspace', None)
        return self.queryset.filter(workspace=workspace)

    def perform_create(self, serializer):
        serializer.save(
            workspace=getattr(self.request, 'workspace', None),
            created_by=self.request.user
        )


@extend_schema(tags=["Income"])
class IncomeViewSet(BaseTransactionViewSet):
    queryset = Income.objects.filter(category__type=Category.CategoryType.INCOME).select_related('category')
    serializer_class = IncomeSerializer


@extend_schema(tags=["Expense"])
class ExpenseViewSet(BaseTransactionViewSet):
    queryset = Expense.objects.filter(category__type=Category.CategoryType.EXPENSE).select_related('category')
    serializer_class = ExpenseSerializer
