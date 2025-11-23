from django.urls import include, path

app_name = "categories"

urlpatterns = [
    path('v1/category/', include('categories.api.v1.urls'))
]
