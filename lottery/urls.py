from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "lottery"

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="lottery/login.html", next_page="lottery:home"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="lottery:home"), name="logout"),
    path("check/", views.check, name="check"),
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/<uuid:uid>/", views.ticket_detail, name="ticket_detail"),
    path("stats/", views.stats, name="stats"),
]
