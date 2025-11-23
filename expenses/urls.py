from django.urls import include, path

app_name = "expenses"

urlpatterns = [
    path('v1/transaction/', include('expenses.api.v1.urls'))
]
