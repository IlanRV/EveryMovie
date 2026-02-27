import requests
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import render


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


def genres(request):
    url = f"{TMDB_BASE}/genre/movie/list"
    params = {
        "api_key": settings.TMDB_API_KEY,
        "language": "en-US",
    }
    response = requests.get(url, params=params, timeout=15)
    return JsonResponse(response.json(), status=response.status_code)


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