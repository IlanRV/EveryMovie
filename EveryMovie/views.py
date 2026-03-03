import itertools
import requests
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MovieList, MovieListItem


TMDB_BASE = "https://api.themoviedb.org/3"


def vote_threshold_from_total(total_results: int) -> int:
    """
    Dynamic vote_count.gte based on how many movies exist for the filter.
    Bigger catalogue => stricter minimum votes.
    """
    if total_results >= 10000:
        return 2000
    if total_results >= 5000:
        return 1000
    if total_results >= 2000:
        return 500
    if total_results >= 800:
        return 250
    if total_results >= 300:
        return 120
    if total_results >= 120:
        return 60
    return 20


def home(request):
    return render(request, "EveryMovie/home.html")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")
        if not username or not email or not password:
            messages.error(request, "All fields are required.")
        elif password != password2:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already in use.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return redirect("home")
    return render(request, "EveryMovie/signup.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, "EveryMovie/login.html")


def logout_view(request):
    logout(request)
    return redirect("home")


def movie_detail(request, movie_id):
    """Fetch full movie details + credits from TMDB and render the detail page."""
    api_key = settings.TMDB_API_KEY

    # Movie details (overview, vote_average, release_date, genres, runtime, etc.)
    detail_url = f"{TMDB_BASE}/movie/{movie_id}"
    detail_resp = requests.get(
        detail_url,
        params={"api_key": api_key, "language": "en-US"},
        timeout=15,
    )
    if not detail_resp.ok:
        return render(request, "EveryMovie/movie.html", {"error": "Movie not found."})

    movie = detail_resp.json()

    # Credits (we need the director)
    credits_url = f"{TMDB_BASE}/movie/{movie_id}/credits"
    credits_resp = requests.get(
        credits_url,
        params={"api_key": api_key, "language": "en-US"},
        timeout=15,
    )
    director = None
    cast = []
    if credits_resp.ok:
        credits = credits_resp.json()
        for member in credits.get("crew", []):
            if member.get("job") == "Director":
                director = member.get("name")
                break
        cast = credits.get("cast", [])[:10]  # top 10 cast members

    # User's lists (for the "Add to list" dropdown)
    user_lists = []
    if request.user.is_authenticated:
        user_lists = MovieList.objects.filter(user=request.user)

    context = {
        "movie": movie,
        "director": director,
        "cast": cast,
        "user_lists": user_lists,
    }
    return render(request, "EveryMovie/movie.html", context)


def genres(request):
    """Return official movie genres plus observed 2-genre combinations.

    We keep this light by *sampling* popular / highly-rated movies and
    deriving all 2-genre pairs that actually appear in that sample.
    """
    url = f"{TMDB_BASE}/genre/movie/list"
    params = {
        "api_key": settings.TMDB_API_KEY,
        "language": "en-US",
    }
    response = requests.get(url, params=params, timeout=15)

    # If the genre list call fails, just proxy the error payload.
    if not response.ok:
        return JsonResponse(response.json(), status=response.status_code)

    data = response.json()
    genres_list = data.get("genres", []) if isinstance(data, dict) else []

    # Build a mapping so we can turn genre IDs back into names.
    id_to_name = {
        g.get("id"): g.get("name")
        for g in genres_list
        if isinstance(g, dict) and "id" in g and "name" in g
    }

    pairs = []

    if id_to_name:
        discover_url = f"{TMDB_BASE}/discover/movie"
        observed_pairs = set()

        # A small set of sampling queries to cover both popularity and rating.
        sample_queries = [
            {"sort_by": "popularity.desc"},
            {"sort_by": "vote_average.desc", "vote_count.gte": 200},
        ]

        for query in sample_queries:
            for page in range(1, 4):  # first 3 pages of each query
                sample_params = {
                    "api_key": settings.TMDB_API_KEY,
                    "include_adult": False,
                    "include_video": False,
                    "language": "en-US",
                    "page": page,
                    **query,
                }
                try:
                    r = requests.get(discover_url, params=sample_params, timeout=10)
                except requests.RequestException:
                    continue

                if not r.ok:
                    continue

                payload = r.json()
                for movie in payload.get("results", []):
                    genre_ids = movie.get("genre_ids") or []
                    # remove unknown IDs and duplicates inside a movie
                    cleaned = sorted({gid for gid in genre_ids if gid in id_to_name})
                    if len(cleaned) < 2:
                        continue
                    for g1, g2 in itertools.combinations(cleaned, 2):
                        observed_pairs.add((g1, g2))

        # Turn observed ID pairs into labelled pair objects for the frontend.
        for g1, g2 in sorted(observed_pairs):
            name1 = id_to_name.get(g1)
            name2 = id_to_name.get(g2)
            if not name1 or not name2:
                continue
            pairs.append(
                {
                    "id": f"{g1},{g2}",  # directly usable as with_genres value
                    "ids": [g1, g2],
                    "label": f"{name1}/{name2}",
                }
            )

    payload = {"genres": genres_list, "pairs": pairs}
    return JsonResponse(payload, status=response.status_code)


def discover(request):
    genre = request.GET.get("genre")
    country = request.GET.get("country")
    sort = request.GET.get("sort", "rating")
    page = request.GET.get("page", "1")

    if not genre or not country:
        return JsonResponse({"error": "Missing genre or country"}, status=400)

    sort_map = {
        "rating": "vote_average.desc",
        "az": "original_title.asc",
    }

    url = f"{TMDB_BASE}/discover/movie"

    base_params = {
        "api_key": settings.TMDB_API_KEY,
        "with_genres": genre,
        "with_origin_country": country,
        "include_adult": False,
        "include_video": False,
        "language": "en-US",
        "page": page,
    }

    # ---------- Non-rating sorts: keep simple ----------
    if sort != "rating":
        params = {
            **base_params,
            "sort_by": sort_map.get(sort, "vote_average.desc"),
        }
        response = requests.get(url, params=params, timeout=15)
        return JsonResponse(response.json(), status=response.status_code)

    # ---------- Rating sort: dynamic quality filter ----------
    # 1) Probe to estimate catalogue size (total_results) for this filter
    # Use popularity.desc for the probe so we don't bias the probe itself by vote filters
    probe_params = {**base_params, "sort_by": "popularity.desc", "page": 1}
    probe_resp = requests.get(url, params=probe_params, timeout=15)
    probe_json = probe_resp.json() if probe_resp.ok else {}
    total_results = int(probe_json.get("total_results", 0))

    # 2) Set threshold based on catalogue size
    threshold = vote_threshold_from_total(total_results)

    # 3) Fetch with a threshold; if too few results, relax stepwise
    def fetch_with_threshold(vote_gte: int):
        params = {
            **base_params,
            "sort_by": "vote_average.desc",
            "vote_count.gte": vote_gte,
        }
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        return r, data, vote_gte

    response, data, used_threshold = fetch_with_threshold(threshold)

    # If results are too sparse, relax. (Tune these numbers as you like.)
    results = data.get("results", []) if isinstance(data, dict) else []
    relax_steps = [500, 250, 120, 60, 20]

    if len(results) < 12:
        for t in relax_steps:
            if t < used_threshold:
                r2, d2, used2 = fetch_with_threshold(t)
                r2_results = d2.get("results", []) if isinstance(d2, dict) else []
                if len(r2_results) >= 12:
                    response, data, used_threshold = r2, d2, used2
                    break

    # Add metadata (optional, but useful for debugging / UI display)
    if isinstance(data, dict):
        data["_quality"] = {
            "vote_count_gte_used": used_threshold,
            "total_results_estimate": total_results,
        }

    return JsonResponse(data, status=response.status_code)


def search_movies(request):
    """Free-text movie search API backed by TMDB /search/movie.

    Returns JSON so the frontend can render results in the same grid
    used for genre/country discovery.
    """
    query = (request.GET.get("q") or "").strip()
    page = request.GET.get("page", "1")

    if not query:
        return JsonResponse({"results": [], "error": "Missing query parameter 'q'."}, status=400)

    url = f"{TMDB_BASE}/search/movie"
    params = {
        "api_key": settings.TMDB_API_KEY,
        "language": "en-US",
        "include_adult": False,
        "page": page,
        "query": query,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
    except requests.RequestException:
        return JsonResponse({"results": [], "error": "Search service unavailable."}, status=502)

    data = resp.json() if resp.ok else {"results": [], "error": "Upstream TMDB error."}
    return JsonResponse(data, status=resp.status_code)


def api_trending(request):
    """Return trending-style movies, with optional country filter.

    We approximate "trending this week" by taking the most popular
    movies and optionally restricting by origin country.
    """
    country = (request.GET.get("country") or "").strip().upper()
    page = request.GET.get("page", "1")

    url = f"{TMDB_BASE}/discover/movie"
    params = {
        "api_key": settings.TMDB_API_KEY,
        "language": "en-US",
        "include_adult": False,
        "include_video": False,
        "sort_by": "popularity.desc",
        "page": page,
    }

    if country:
        params["with_origin_country"] = country

    try:
        resp = requests.get(url, params=params, timeout=15)
    except requests.RequestException:
        return JsonResponse({"results": [], "error": "Trending service unavailable."}, status=502)

    data = resp.json() if resp.ok else {"results": [], "error": "Upstream TMDB error."}
    return JsonResponse(data, status=resp.status_code)


# ──────────────────────────────────────────────
# Movie Lists – CRUD
# ──────────────────────────────────────────────

@login_required(login_url="login")
def my_lists(request):
    """Show all lists belonging to the logged-in user."""
    lists = MovieList.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "EveryMovie/my_lists.html", {"lists": lists})


@login_required(login_url="login")
def create_list(request):
    """Create a new list (POST only)."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "List name cannot be empty.")
        elif MovieList.objects.filter(user=request.user, name=name).exists():
            messages.error(request, "You already have a list with that name.")
        else:
            MovieList.objects.create(user=request.user, name=name)
            messages.success(request, f'List "{name}" created.')
    return redirect(request.POST.get("next", "my_lists"))


@login_required(login_url="login")
def delete_list(request, list_id):
    """Delete a list (POST only)."""
    if request.method == "POST":
        ml = get_object_or_404(MovieList, id=list_id, user=request.user)
        ml.delete()
        messages.success(request, "List deleted.")
    return redirect("my_lists")


@login_required(login_url="login")
def rename_list(request, list_id):
    """Rename a list (POST only)."""
    if request.method == "POST":
        ml = get_object_or_404(MovieList, id=list_id, user=request.user)
        new_name = request.POST.get("name", "").strip()
        if not new_name:
            messages.error(request, "Name cannot be empty.")
        elif MovieList.objects.filter(user=request.user, name=new_name).exclude(id=list_id).exists():
            messages.error(request, "You already have a list with that name.")
        else:
            ml.name = new_name
            ml.save()
            messages.success(request, "List renamed.")
    return redirect("my_lists")


@login_required(login_url="login")
def add_to_list(request, list_id):
    """Add a movie to a list (POST). Expects tmdb_id, title, poster_path."""
    if request.method == "POST":
        ml = get_object_or_404(MovieList, id=list_id, user=request.user)
        tmdb_id = request.POST.get("tmdb_id")
        title = request.POST.get("title", "Untitled")
        poster_path = request.POST.get("poster_path", "")
        if not tmdb_id:
            messages.error(request, "Missing movie id.")
        elif MovieListItem.objects.filter(movie_list=ml, tmdb_id=tmdb_id).exists():
            messages.error(request, f'"{title}" is already in "{ml.name}".')
        else:
            MovieListItem.objects.create(
                movie_list=ml,
                tmdb_id=int(tmdb_id),
                title=title,
                poster_path=poster_path,
            )
            messages.success(request, f'Added "{title}" to "{ml.name}".')
    # Redirect back to the movie page
    next_url = request.POST.get("next", "/")
    return redirect(next_url)


@login_required(login_url="login")
def remove_from_list(request, item_id):
    """Remove a movie from a list (POST only)."""
    if request.method == "POST":
        item = get_object_or_404(MovieListItem, id=item_id, movie_list__user=request.user)
        item.delete()
        messages.success(request, "Movie removed.")
    return redirect(request.POST.get("next", "my_lists"))


def api_lists(request):
    """Return all lists for the current user as JSON.

    Shape:
    {
      "lists": [
        {"id": 1, "name": "🍿 Friday", "item_count": 5, "created_at": "..."},
        ...
      ]
    }
    """
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)

    lists_qs = (
        MovieList.objects
        .filter(user=request.user)
        .annotate(item_count=Count("items"))
        .order_by("-created_at")
    )

    payload = {
        "lists": [
            {
                "id": ml.id,
                "name": ml.name,
                "item_count": ml.item_count,
                "created_at": ml.created_at.isoformat(),
            }
            for ml in lists_qs
        ]
    }
    return JsonResponse(payload, status=200)