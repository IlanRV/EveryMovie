from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    # Auth
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # API endpoints
    path("genres/", views.genres, name="genres"),
    path("discover/", views.discover, name="discover"),
    path("search/", views.search_movies, name="search_movies"),
    path("api/lists/", views.api_lists, name="api_lists"),
    path("api/trending/", views.api_trending, name="api_trending"),

    # Movie detail
    path("movie/<int:movie_id>/", views.movie_detail, name="movie_detail"),

    # Lists
    path("my-lists/", views.my_lists, name="my_lists"),
    path("lists/create/", views.create_list, name="create_list"),
    path("lists/<int:list_id>/delete/", views.delete_list, name="delete_list"),
    path("lists/<int:list_id>/rename/", views.rename_list, name="rename_list"),
    path("lists/<int:list_id>/add/", views.add_to_list, name="add_to_list"),
    path("lists/item/<int:item_id>/remove/", views.remove_from_list, name="remove_from_list"),
]