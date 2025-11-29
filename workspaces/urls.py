from django.urls import include, path

app_name = "workspaces"

urlpatterns = [
    path('v1/workspace/', include('workspaces.api.v1.urls'))
]
