from rest_framework import routers
from .views import CategoryVeiwSet

router = routers.DefaultRouter()

router.register('categories', CategoryVeiwSet, basename='categories')
