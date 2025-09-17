# Music-Archiver

[![Build Status](https://img.shields.io/badge/build-pending-lightgrey.svg)](#) [![Coverage](https://img.shields.io/badge/coverage-tbc-lightgrey.svg)](#) [![License](https://img.shields.io/badge/license-MIT-blue.svg)](#license)

**Save, organise, and play web music links with albums, playlists, ratings, favourites, and social saving.**

- **Live Demo:** [https://music-archiver-498e27441f42.herokuapp.com/](https://music-archiver-498e27441f42.herokuapp.com/)
- **Repository:** [https://github.com/ie3ul2df/Music-Archiver](https://github.com/ie3ul2df/Music-Archiver)

---

## Table of Contents

- [Project Overview](#project-overview)
  - [UX](#ux)
- [Wireframes](#Low-and-High-Fidelity-Wireframes)
- [Architecture & Data Model](#architecture--data-model)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Quickstart](#quickstart)
  - [Configuration](#configuration)
- [Testing](#testing)
- [Deployment on Heroku](#deployment-on-heroku)
- [Testing](#testing)
- [Accessibility & Security](#accessibility--security)
- [Roadmap & Known Issues](#roadmap--known-issues)
- [Troubleshooting / FAQ](#troubleshooting--faq)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Project Overview

Music-Archiver is a Django web application for storing and streaming user-curated music links. It balances personal libraries with social discovery through collaborative saving, favourites, and ratings.

### UX

#### Project Goals

- Enable users to save, organise, and play web-hosted music links.
- Provide premium features via Stripe subscriptions.

#### Target Audience

- Music collectors who want lightweight playlists/albums from web sources.
- Creators who share albums with followers.

#### User Stories (MoSCoW)

- **Must**: As a user, I can register/log in so that my albums and playlists persist.
- **Must**: As a user, I can create albums and add tracks to organise my collection.
- **Must**: As a user, I can pay for Premium to unlock higher limits.
- **Should**: As a user, I can rate and favourite tracks/albums.
- **Could**: As a user, I can save snapshots of others’ albums.

#### Acceptance Criteria (examples)

- _Given_ I am logged in, _when_ I add a track URL, _then_ it appears in my album and is playable.
- _Given_ payment succeeds, _when_ I return to my profile, _then_ my plan shows as Premium and limits update.

#### Sitemap

- Home → Albums → Album Detail → Player
- Profile → My Albums / Playlists / Favourites
- Plans → Basket → Checkout (Stripe) → Success/Cancel
- Login/Register/Logout

#### Core Features

- User accounts with registration, login, and profile management.
- Album & track CRUD including uploads to Cloudinary or external URLs.
- Drag-and-drop track ordering for albums and playlists.
- Responsive media player with play/pause, next/previous, shuffle, progress, and volume controls.
- Favourites (♥), ratings (★), and recent play history for engagement insights.
- Save other users’ albums/tracks as snapshots with “update available” indicators.
- Search, filtering, and responsive Bootstrap-powered UI.
- Plan management: Free plan (e.g., 3 albums) vs Premium subscriptions via Stripe.
- Cloudinary storage quotas enforced per plan.

---

## Low and High Fidelity Wireframes

![Low Fidelity Home Wireframe](static/wireframes/low-fidelity-wireframes/home.png)
![High Fidelity Home Wireframe](static/wireframes/high-fidelity-wireframes/home.png)
![Low Fidelity Navbar Wireframe](static/wireframes/low-fidelity-wireframes/navbar.png)
![Low Fidelity music player Wireframe](static/wireframes/low-fidelity-wireframes/music-player-page.png)
![High Fidelity music player Wireframe](static/wireframes/high-fidelity-wireframes/music-player-page.png)
![Low Fidelity album and track card Wireframe](static/wireframes/low-fidelity-wireframes/album-card-and-track-card.png)
![High Fidelity track card Wireframe](static/wireframes/high-fidelity-wireframes/track-cards.png)
![Low Fidelity album-list-and-album-detail Wireframe](static/wireframes/low-fidelity-wireframes/album-list-and-album-detail.png)
![high Fidelity album-list Wireframe](static/wireframes/high-fidelity-wireframes/album-list.png)
![high Fidelity album-detail Wireframe](static/wireframes/high-fidelity-wireframes/album-detail.png)
![high Fidelity basket Wireframe](static/wireframes/high-fidelity-wireframes/basket.png)
![high Fidelity profile Wireframe](static/wireframes/high-fidelity-wireframes/profile-page.png)
![high Fidelity price Wireframe](static/wireframes/high-fidelity-wireframes/price-page.png)

---

## Architecture & Data Model

The application follows a standard Django project layout with Django apps for albums, playlists, profiles, and shared utilities. Static files are served via Whitenoise in production, while media uploads are stored in Cloudinary.

- **ERD:** [![Full ERD](static/erd/full-erd.svg)](static/erd/full-erd.svg)

### Data Model (Narrative)

- **User / Profile**: standard auth user; Profile adds avatar, display preferences.
- **Album**: `owner → User`, `name`, `description`, `is_public`, timestamps.
- **Track**: `owner → User`, `name`, `source_url` or `audio_file`, duration, meta.
- **AlbumTrack**: join with `album → Album`, `track → Track`, `position (int)`; enforces ordering.
- **Playlist** / **PlaylistItem**: similar to Album/AlbumTrack for personal queues.
- **Rating**: generic (album/track), `user → User`, `value (1–5)`, unique per (user, object).
- **Favorite**: user-object bookmark; unique per (user, object).
- **SavedAlbum / SavedTrack**: snapshot of others’ content; stores `name_snapshot`, update flags.
- **Plan** / **Subscription**: plan tier & limits; subscription links to Stripe IDs.

**Constraints & Integrity**

- `AlbumTrack`: `(album, position)` unique; default ordering by `position, id`.
- `Rating`: unique `(user, content_type, object_id)`.
- Useful indexes on `owner_id`, `(album_id, position)`.

---

## Tech Stack

- **Language & Runtime**

  - `Python 3.12+` (virtualenv)
  - `pip` + `requirements.txt` for dependencies

- **Web Framework**

  - `Django 5.x` (apps: `album`, `tracks`, `playlist`, `plans`, `basket`, `checkout`, `profile_page`, `home_page`, `ratings`, `save_system`)

- **Auth & Accounts**

  - `django-allauth` (email/social auth)
  - `django.contrib.sites` (required by allauth)
  - Django auth/sessions/messages
  - Guests can browse public albums but cannot create/edit or save content.
  - Registered users can CRUD their own albums/tracks, rate/favourite, save others’ albums.
  - Owners only: rename/detach/delete their items.
  - Admin users manage plans/subscriptions via Django admin.

- **Forms & Templating**

  - `django-crispy-forms` + `crispy-bootstrap5`
  - Django Templates with partials/includes and filters

- **Forms & Validation**

- **Auth forms**: django-allauth (email/password validation).
- **Album/Track forms**: server-side validation of required fields, URL format, file types; user-friendly error messages.
- **Checkout**: server-side verification of Stripe intent; flash messages on success/failure.
- Client-side: HTML5 validation + Bootstrap feedback; JS prevents duplicate submits where applicable.

- **Frontend**

  - `Bootstrap 5` (grid, utilities, responsive)
  - Vanilla JavaScript modules in `static/js` (player controls, ratings, AJAX/fetch)
  - Custom CSS + semantic HTML

- **JavaScript Features**

  - **Audio Player** (`static/js/music_player.js`): play/pause, progress, duration, volume, next/prev, shuffle.
  - **Album/Playlist UI** (`static/js/album_utils.js` etc.): drag-and-drop ordering, AJAX add/remove, favourites and ratings.
  - Progressive enhancement: server renders controls; JS upgrades behaviour; graceful fallbacks if JS disabled.

- **Database**

  - `PostgreSQL` (production, Neon)
  - `SQLite` (local development)
  - Django ORM + migrations

- **Media & Static**

  - `Cloudinary` + `django-cloudinary-storage` as default file storage
  - `Pillow` for image handling
  - Django `staticfiles` + `WhiteNoise` for static serving

- **Payments**

  - `Stripe` (server SDK) for subscriptions/checkout + secure webhooks
  - **Flow**: Plan → Basket → Checkout → Stripe Hosted Page → Webhook → Subscription active → Plan limits updated.
  - **Webhook endpoint**: `/checkout/webhook/`
  - **Test cards**: `4242 4242 4242 4242`, expiry: `12/32`, CVC: `123`, any postcode.
  - **Feedback**: success/cancel pages and on-site messages communicate outcome.

- **Serving & Deployment**

  - `Gunicorn` (WSGI)
  - `WhiteNoise` (serve `/static`)
  - `Heroku` (dynos, config vars, `collectstatic`)
  - `Procfile`, `runtime.txt`

- **Configuration & Env Vars**

  - `python-dotenv` / `django-environ` / `python-decouple`
  - Typical keys: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WH_SECRET`, `CLOUDINARY_URL`

- **Tooling & Workflow**
  - **Visual Studio Code** (Python/Django extensions)
  - **Git & GitHub** (source control, README)
  - **Heroku CLI** (deploy, logs, run commands)
  - **psql / pg_dump** (schema export for ERD)
  - **pgAdmin / DBeaver** (DB GUI, optional)
  - **Chrome DevTools** (network/console/layout)
  - **Windows PowerShell/CMD** (local dev shell)

---

## How It Fits Together

- **Django 5.x** provides models, views, URLs, and templates split into feature apps.
- **ORM → PostgreSQL/SQLite**: SQLite for dev; Neon/Postgres in prod via `DATABASE_URL`.
- **Cloudinary** stores media (audio/images) off-box; URLs delivered via CDN.
- **Static assets** are collected by `collectstatic` and served by **WhiteNoise** on Heroku.
- **Bootstrap + vanilla JS** power the responsive UI and interactivity (audio player, ratings, playlist toggles, favourites).
- **Stripe** handles billing: server-side intents + **webhooks** for reliable fulfillment.
- **Gunicorn** runs the Django app on Heroku; **WhiteNoise** serves static efficiently.
- **Env vars** isolate secrets/config between dev and prod.

---

## Deployment Flow (Heroku)

1. Commit & push to GitHub (or `git push heroku main`).
2. Heroku builds the slug and installs `requirements.txt`.
3. Run collectstatic (manually or automatically):
   ```bash
   heroku run python manage.py collectstatic --noinput
   ```

---

## Getting Started

### Quickstart

1. Clone the repository and enter the project directory:
   ```bash
   git clone https://github.com/ie3ul2df/Music-Archiver.git
   cd Music-Archiver
   ```
2. Create & activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Apply migrations and load any fixtures:
   ```bash
   python manage.py migrate
   ```
5. Create a superuser (optional but recommended):
   ```bash
   python manage.py createsuperuser
   ```
6. Run the development server:
   ```bash
   python manage.py runserver
   ```

#### Ready Checklist

- [ ] `.venv` activated
- [ ] `.env` created with required keys
- [ ] Database migrated without errors
- [ ] Admin user created (for dashboard access)

### Configuration

Create a `.env` file in the project root using the template below:

```env
SECRET_KEY=changeme
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
CLOUDINARY_URL=cloudinary://...
STRIPE_PUBLIC_KEY=pk_live_or_test
STRIPE_SECRET_KEY=sk_live_or_test
STRIPE_WEBHOOK_SECRET=whsec_...
```

> ℹ️ **Tip:** When running locally with SQLite, you can omit `DATABASE_URL` and rely on default Django settings.

Static files are collected to `BASE_DIR / "staticfiles"` and served via Whitenoise in production.

---

## Deployment on Heroku

1. Provision a Heroku app and add a PostgreSQL add-on.
2. Set **Config Vars** for every key listed in the `.env` example above.
3. Ensure the `Procfile` contains:
   ```Procfile
   web: gunicorn your_project_module.wsgi
   ```
4. First deploy checklist:
   - [ ] Set `DISABLE_COLLECTSTATIC=1` **before** the first deploy to avoid build failures.
   - [ ] Deploy via GitHub or `git push heroku main`.
   - [ ] Run `python manage.py migrate` on the dyno.
   - [ ] Create an admin user with `python manage.py createsuperuser`.
   - [ ] Remove `DISABLE_COLLECTSTATIC` and run `python manage.py collectstatic`.

> ⚠️ **Whitenoise Pitfall:** Always commit `staticfiles` to `.gitignore`. Let Heroku collect static assets during deploy; missing `STATIC_ROOT` configuration will trigger `ImproperlyConfigured` errors.

> ⚠️ **Gunicorn Module:** Replace `your_project_module` with the actual Django project package name (e.g., `music_project`). A typo here causes immediate “Application Error” responses on Heroku.

---

## Testing

### Manual Test Matrix (sample)

| Feature    | Scenario       | Steps            | Expected                    | Result |
| ---------- | -------------- | ---------------- | --------------------------- | ------ |
| Register   | Valid details  | Submit form      | User created & logged in    | ✅     |
| Album CRUD | Create album   | Fill name → Save | Album appears in list       | ✅     |
| Player     | Play web track | Click ▶          | Audio plays; time updates   | ✅     |
| Checkout   | Test card      | Pay via Stripe   | Success page; plan upgraded | ✅     |

### Validators & Linters

- **HTML** (W3C): Pass (screenshots in `docs/testing/`).
- **CSS** (Jigsaw): Pass.
- **JS** (e.g., ESLint/JSHint): No critical issues.
- **Python** (PEP8/flake8): Clean or documented exceptions.

### Lighthouse

- Mobile & Desktop scores for Performance/Accessibility/Best Practices/SEO (screenshots included).

### Browsers & Devices

- Chrome, Firefox, Edge, Safari 15+; iOS/Android (key pages tested with screenshots).

### Bug Log

- Issue → reproduction → root cause → fix → commit hash (see `docs/bugs.md`).

---

## Accessibility & Security

- Keyboard-accessible media player controls with `aria-label` support on icon buttons.
- GDPR compliance: users can delete their account and purge associated data upon request.
- Copyright notice: Music-Archiver only streams user-supplied links/files and does not host or distribute copyrighted content.

---

## Roadmap & Known Issues

- [ ] Implement collaborative playlists with real-time updates.
- [ ] Add offline caching for recently played tracks.
- [ ] Improve notifications for updated saved albums/tracks.
- [ ] Document Cloudinary quota handling edge cases.
- Known issue: Drag-and-drop uses HTML5 API; Safari versions < 15 may have inconsistent behaviour.

---

## Troubleshooting / FAQ

- **Static files not loading on Heroku?** Ensure `collectstatic` runs after unsetting `DISABLE_COLLECTSTATIC` and that Whitenoise middleware is above Django’s `SecurityMiddleware`.
- **Heroku “Application Error” after deploy?** Check the `Procfile` entry, confirm Gunicorn is installed, and verify `ALLOWED_HOSTS` includes the Heroku domain.
- **Cloudinary returning 401/403?** Double-check `CLOUDINARY_URL` and plan quota; regenerate API keys if the account was reset.
- **Stripe webhook failing locally?** Use the Stripe CLI to forward events and ensure `STRIPE_WEBHOOK_SECRET` matches the CLI output.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Add tests for your changes.
4. Run the test suite and update documentation as needed.
5. Submit a pull request with a clear summary and testing evidence.

---

## License

Distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contact

For questions or support, please open an issue on GitHub or reach out directly:

- **Email:** [arash11javadi@gmail.com](mailto:arash11javadi@gmail.com)
- **Website:** [arashjavadi.com](https://arashjavadi.com)
- **GitHub:** [@arash12javadi](https://github.com/arash12javadi)
- **Phone:** [+44 7506 205023](tel:+447506205023)
- **Address:** Guildford Cres, Cardiff, CF10 2HA, United Kingdom
