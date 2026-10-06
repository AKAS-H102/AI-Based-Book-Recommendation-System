import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Set a real random value in production:  export SECRET_KEY="..."
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    DATABASE = os.environ.get("DATABASE", os.path.join(BASE_DIR, "data", "bookrec.db"))
    PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7      # 7 days
    BOOKS_PER_PAGE = 12
    MODEL_REFIT_SECONDS = 30       # re-train the recommender at most this often when new ratings arrive
    MAX_LOGIN_ATTEMPTS = 5         # per 5 minutes per username+IP
