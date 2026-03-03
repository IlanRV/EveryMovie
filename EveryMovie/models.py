from django.db import models
from django.conf import settings


class MovieList(models.Model):
    """A user-created movie list (e.g. 'Watch Later', 'Favourites')."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="movie_lists",
    )
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "name")  # no duplicate list names per user

    def __str__(self):
        return f"{self.user.username} – {self.name}"


class MovieListItem(models.Model):
    """A single movie saved inside a MovieList.

    We store only the TMDB movie id, title, and poster path so we don't need
    a local Movie table – everything else is fetched from TMDB on demand.
    """
    movie_list = models.ForeignKey(
        MovieList,
        on_delete=models.CASCADE,
        related_name="items",
    )
    tmdb_id = models.IntegerField()
    title = models.CharField(max_length=300)
    poster_path = models.CharField(max_length=300, blank=True, default="")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added_at"]
        unique_together = ("movie_list", "tmdb_id")  # no duplicates in one list

    def __str__(self):
        return f"{self.title} in {self.movie_list.name}"
