from django.urls import path
from .views import LoginView, LogoutView, MeView, SignupView, CustomTokenRefreshView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
]
