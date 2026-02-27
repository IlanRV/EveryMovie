from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    # your existing API endpoints:
    path("genres/", views.genres, name="genres"),
    path("discover/", views.discover, name="discover"),
    path("", views.home, name="home")
]