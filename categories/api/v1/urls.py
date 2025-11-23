from django.urls import path
from .routers import router

urlpatterns = [
]

urlpatterns.extend(router.urls)