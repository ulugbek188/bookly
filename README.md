# Bookly

Bookly is a social platform for readers where users can share book posts, follow other readers, comment, and like posts.

## Features

- User registration and login
- Public and private accounts
- User profiles and avatars
- Book posts with title, description, gist, and cover
- Follow system with private account requests
- Personalized feed
- Comments with permissions
- Likes for posts and comments
- Secure session-based authentication

## Tech Stack

**Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, asyncpg, Alembic, Pydantic, bcrypt

**Frontend:** HTML, CSS, Vanilla JavaScript

## Deployment

The frontend and API can be deployed to separate hosts.

1. Set `window.BOOKLY_API_URL` in `frontend/assets/js/config.js` to the public HTTPS URL of the backend, for example `https://api.example.com`.
2. Set the backend `CORS_ORIGINS` environment variable to the frontend origin, for example `https://bookly.example.com`. Multiple origins are comma-separated.
3. Start the backend with a production server, for example `uvicorn src.main:app --host 0.0.0.0 --port 8000` from `backend`.

The API URL is also used for uploaded covers and avatars, so those files remain available when the frontend is hosted on Cloudflare Pages.