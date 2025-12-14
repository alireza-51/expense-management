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


class CategoryFlatSerializer(serializers.ModelSerializer):
    """Flat serializer for categories without nested children"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = Category
        fields = (
            'id',
            'name',
            'type',
            'description',
            'color',
            'parent',
            'parent_name',
            'created_at',
            'edited_at',
        )
