# EveryMovie

A movie discovery web application built with Django that lets users explore films by genre and country using The Movie Database (TMDB) API.

**Live site:** [everymovie.onrender.com](https://everymovie.onrender.com)

**API Documentation:** [API_DOCUMENTATION.md](API_DOCUMENTATION.md) (also submitted as PDF)

---

## Features

- **Genre Discovery** — Browse all TMDB genres plus dynamically detected genre pairs (e.g. Action/Comedy, Animation/Science Fiction)
- **Country & Sort Filters** — Discover movies from 16+ countries, sorted by popularity, rating, release date, or revenue
- **Trending Strip** — A horizontally scrolling panel of currently popular movies
- **Search** — Real-time movie search powered by TMDB
- **Movie Details** — Full movie pages with overview, director, cast, genres, runtime, and rating
- **User Accounts** — Sign up / log in with passwords secured via PBKDF2-SHA256 hashing with per-user salts
- **My Lists** — Authenticated users can create, rename, and delete personal movie lists, and add/remove movies
- **Animated Side Columns** — Scrolling poster strips on desktop driven by trending data
- **Dark Theme** — Fully styled dark UI with genre-coloured chips and gradient accents
- **Responsive** — Adapts layout for mobile and desktop

---

## Tech Stack

| Layer       | Technology                                      |
|-------------|--------------------------------------------------|
| Backend     | Python 3, Django 6                               |
| Database    | SQLite (via Django ORM)                          |
| External API| [TMDB API v3](https://developer.themoviedb.org/) |
| Frontend    | Django templates, vanilla JavaScript, CSS        |
| Deployment  | Render, Gunicorn, WhiteNoise                     |

---

## Project Structure

```
EveryMovie/
├── config/                 # Django project settings
│   ├── settings.py         # Configuration (env-based DEBUG, ALLOWED_HOSTS, TMDB key)
│   ├── urls.py             # Root URL config
│   └── wsgi.py             # WSGI entry point
├── EveryMovie/             # Main application
│   ├── models.py           # MovieList & MovieListItem models
│   ├── views.py            # All views and JSON API endpoints
│   ├── urls.py             # App URL routes
│   ├── tests.py            # Automated tests (8 test cases)
│   ├── admin.py            # Admin registration
│   └── templates/EveryMovie/
│       ├── base.html       # Shared layout, styling, side columns
│       ├── home.html       # Home page (genres, discover, search, trending)
│       ├── movie.html      # Movie detail page
│       ├── my_lists.html   # User's saved lists
│       ├── login.html      # Login form
│       └── signup.html     # Registration form
├── requirements.txt        # Python dependencies
├── manage.py               # Django management script
└── db.sqlite3              # SQLite database
```

---

## API Endpoints

| Method | URL                   | Description                                         | Auth Required |
|--------|-----------------------|------------------------------------------------------|:------------:|
| GET    | `/genres/`            | Returns all TMDB genres + observed genre pairs (JSON) | No           |
| GET    | `/discover/`          | Discover movies by genre & country (JSON)            | No           |
| GET    | `/search/?q=...`      | Search movies by title (JSON)                        | No           |
| GET    | `/api/trending/`      | Trending/popular movies, optional `country` & `page` | No           |
| GET    | `/api/lists/`         | Returns the authenticated user's lists (JSON)        | Yes          |

### Page Routes

| URL                          | Description                    |
|------------------------------|--------------------------------|
| `/`                          | Home page                      |
| `/movie/<id>/`               | Movie detail page              |
| `/signup/`                   | User registration              |
| `/login/`                    | User login                     |
| `/logout/`                   | Log out (redirects to home)    |
| `/my-lists/`                 | View and manage saved lists    |
| `/lists/create/`             | Create a new list (POST)       |
| `/lists/<id>/delete/`        | Delete a list (POST)           |
| `/lists/<id>/rename/`        | Rename a list (POST)           |
| `/lists/<id>/add/`           | Add a movie to a list (POST)   |
| `/lists/item/<id>/remove/`   | Remove a movie from a list (POST) |

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- A free [TMDB API key](https://www.themoviedb.org/settings/api)

### Local Development

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/EveryMovie.git
cd EveryMovie

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Create a .env file with your TMDB API key
echo TMDB_API_KEY=your_api_key_here > .env

# Run migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Running Tests

```bash
python manage.py test
```

This runs 8 automated tests covering:

- Genre, discover, search, and trending JSON endpoints
- Input validation (missing parameters return 400)
- User signup and authentication
- List creation and the `/api/lists/` JSON API
- Authentication enforcement on protected endpoints

---

## Deployment (Render)

The app is deployed on [Render](https://render.com) with the following configuration:

| Setting        | Value                                                                 |
|----------------|-----------------------------------------------------------------------|
| Build Command  | `pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| Start Command  | `gunicorn config.wsgi:application`                                    |
| Environment Vars | `TMDB_API_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=everymovie.onrender.com` |

Static files are served via [WhiteNoise](http://whitenoise.evans.io/).

---

## Security

- Passwords are hashed using Django's default **PBKDF2-SHA256** with per-user random salts (870,000+ iterations)
- CSRF protection enabled on all POST forms
- `DEBUG=False` in production
- Input validation on all API endpoints and forms
- `@login_required` enforced on list management views

---

## License

This project was built as coursework for a Web Services module. TMDB data is used under their [API Terms of Use](https://www.themoviedb.org/documentation/api/terms-of-use).
