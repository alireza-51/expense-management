from rest_framework import serializers
from categories.models import Category
from base.serializers import RecursiveField


class CategorySerializer(serializers.ModelSerializer):
    children = RecursiveField(many=True, read_only=True)

    class Meta:
        model = Category
        fields = (
            'id',
            'name',
            'type',
            'description',
            'color',
            'parent',
            'children',
        )
