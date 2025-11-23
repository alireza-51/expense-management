from django.urls import path, include
from .routers import router

urlpatterns = [
]

urlpatterns.extend(router.urls)