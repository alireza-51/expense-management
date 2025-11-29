from typing import Optional
from rest_framework import serializers
from expenses.models import Income, Expense
from jalali_date import datetime2jalali
from drf_spectacular.utils import extend_schema_field


class TransactionSerializer(serializers.ModelSerializer):
    transactioned_at_jalali = serializers.SerializerMethodField(read_only=True)
    transacted_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M",
        input_formats=[
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%SZ",
            "iso-8601",
        ]
    )


    class Meta:
        fields = [
            'id',
            'category',
            'amount',
            'transacted_at',
            'transactioned_at_jalali',
            'notes',
            'created_at',
            'edited_at',
        ]
        read_only_fields = ['id', 'created_at', 'edited_at', 'transactioned_at_jalali']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_transactioned_at_jalali(self, instance) -> Optional[str]:
        if not instance.transacted_at:
            return None
        # Convert Gregorian to Jalali and format nicely
        return datetime2jalali(instance.transacted_at).strftime('%Y-%m-%d %H:%M')
    
    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount cannot be negative.")
        return value


class IncomeSerializer(TransactionSerializer):
    class Meta(TransactionSerializer.Meta):
        model = Income
        # Inherits both fields and read_only_fields automatically

    def create(self, validated_data):
        request = self.context['request']
        validated_data['workspace'] = getattr(request, 'workspace', None)
        validated_data['created_by'] = request.user
        return super().create(validated_data)


class ExpenseSerializer(TransactionSerializer):
    class Meta(TransactionSerializer.Meta):
        model = Expense
        # Inherits both fields and read_only_fields automatically

    def create(self, validated_data):
        request = self.context['request']
        validated_data['workspace'] = getattr(request, 'workspace', None)
        validated_data['created_by'] = request.user
        return super().create(validated_data)
