from django.urls import include, path

app_name = "analytics"

urlpatterns = [
    path('v1/dashboard/', include('analytics.api.v1.urls')),
]

