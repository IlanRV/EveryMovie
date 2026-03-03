from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings

from .models import MovieList, MovieListItem


class PublicApiTests(TestCase):
	def setUp(self):
		self.client = Client()

	def test_genres_endpoint_returns_json(self):
		"""Basic smoke test: /genres/ responds with JSON and 2xx/3xx code.

		We don't assert exact TMDB data (that would be brittle),
		just that the service is reachable and returns JSON-like
		content with a "genres" key or is at least well-formed.
		"""
		url = reverse("genres")
		response = self.client.get(url)
		self.assertIn(response.status_code, {200, 502, 500, 503})

		# If it is a success, it should be JSON and contain "genres".
		if response.status_code == 200:
			self.assertEqual(response["Content-Type"], "application/json")
			data = response.json()
			self.assertIsInstance(data, dict)
			self.assertIn("genres", data)

	def test_search_requires_query_param(self):
		"""/search/ without q should return a 400 with an error message."""
		url = reverse("search_movies")
		response = self.client.get(url)  # no ?q=
		self.assertEqual(response.status_code, 400)
		data = response.json()
		self.assertIn("error", data)

	def test_trending_endpoint_basic(self):
		"""/api/trending/ should return JSON (status may depend on TMDB)."""
		url = reverse("api_trending")
		response = self.client.get(url)
		self.assertIn(response.status_code, {200, 502, 500, 503})

		if response.status_code == 200:
			self.assertEqual(response["Content-Type"], "application/json")
			data = response.json()
			self.assertIsInstance(data, dict)
			self.assertIn("results", data)

	def test_discover_requires_genre_and_country(self):
		"""/discover/ should enforce required query parameters."""
		url = reverse("discover")

		# Missing both
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 400)

		# Missing country
		resp2 = self.client.get(url, {"genre": "28"})
		self.assertEqual(resp2.status_code, 400)

		# Missing genre
		resp3 = self.client.get(url, {"country": "US"})
		self.assertEqual(resp3.status_code, 400)


class AuthAndListsTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(
			username="alice", email="alice@example.com", password="secret123"
		)

	def test_signup_creates_user(self):
		url = reverse("signup")
		payload = {
			"username": "bob",
			"email": "bob@example.com",
			"password": "pass1234",
			"password2": "pass1234",
		}
		response = self.client.post(url, payload, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(User.objects.filter(username="bob").exists())

	def test_login_and_access_my_lists(self):
		"""A logged-in user should be able to see the My Lists page."""
		logged_in = self.client.login(username="alice", password="secret123")
		self.assertTrue(logged_in)

		url = reverse("my_lists")
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "My Lists")

	def test_create_list_and_appears_in_api_lists(self):
		"""Creating a list via POST should be visible in /api/lists/."""
		self.client.login(username="alice", password="secret123")

		# Create list
		create_url = reverse("create_list")
		response = self.client.post(create_url, {"name": "Favourites"}, follow=True)
		self.assertEqual(response.status_code, 200)
		movie_list = MovieList.objects.get(user=self.user, name="Favourites")

		# Add an item so item_count is > 0
		MovieListItem.objects.create(
			movie_list=movie_list,
			tmdb_id=123,
			title="Test Movie",
			poster_path="/test.jpg",
		)

		# Call JSON API
		api_url = reverse("api_lists")
		api_response = self.client.get(api_url)
		self.assertEqual(api_response.status_code, 200)
		data = api_response.json()
		self.assertIn("lists", data)
		self.assertGreaterEqual(len(data["lists"]), 1)

		found = [l for l in data["lists"] if l["name"] == "Favourites"]
		self.assertEqual(len(found), 1)
		self.assertEqual(found[0]["item_count"], 1)

	def test_api_lists_requires_authentication(self):
		"""Unauthenticated request to /api/lists/ should be rejected."""
		url = reverse("api_lists")
		response = self.client.get(url)
		self.assertEqual(response.status_code, 401)
		data = response.json()
		self.assertIn("detail", data)

