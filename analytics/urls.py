from django.urls import include, path

app_name = "analytics"

urlpatterns = [
    path('v1/dashboard/', include('analytics.api.v1.dashboard.urls')),
    path('v1/analytics/', include('analytics.api.v1.analytics.urls')),
]

