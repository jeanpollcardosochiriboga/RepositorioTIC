#!/usr/bin/env python3
# Esc2 refresh_movies.py — versión con PÓSTERS LOCALES (2026-06-14).
# Cambio vs. original: cada póster TMDB se descarga a /data/www/posters/ y el
# campo "image" apunta a una ruta local (/posters/<archivo>.jpg). Así la cartelera
# muestra pósters reales SIN depender de internet al cargar la página (antes el
# <img> remoto fallaba sin internet y el onerror caía a un emoji).
# Si la descarga de un póster falla, se conserva la URL remota como respaldo.
import json, os, sys, ssl, tempfile
from urllib import request, parse, error

TMDB_BASE = "https://api.themoviedb.org/3"
IMG_BASE  = "https://image.tmdb.org/t/p/w500"
EMOJIS    = ["🎬", "🎭", "🎪", "🎨", "🎟️", "🍿"]
OUT_PATH  = os.environ.get("MOVIES_OUT", "/data/www/movies.json")
POSTERS_DIR = os.path.join(os.path.dirname(OUT_PATH), "posters")
TIMEOUT   = 12

def tmdb_get(path, params, token):
    url = f"{TMDB_BASE}{path}?{parse.urlencode(params)}"
    req = request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    ctx = ssl.create_default_context()
    with request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))

def download_image(poster_path):
    """Baja el póster a www/posters/ y devuelve la ruta local servida.
    Respaldo: si falla la descarga, devuelve la URL remota de TMDB."""
    remote = f"{IMG_BASE}{poster_path}"
    fname = os.path.basename(poster_path)          # ej. rmCkNtz....jpg
    dest = os.path.join(POSTERS_DIR, fname)
    local_url = f"/posters/{fname}"
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return local_url
    try:
        os.makedirs(POSTERS_DIR, exist_ok=True)
        ctx = ssl.create_default_context()
        req = request.Request(remote, headers={"User-Agent": "Mozilla/5.0"})
        with request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            data = r.read()
        if len(data) < 1000:
            return remote
        fd, tmp = tempfile.mkstemp(dir=POSTERS_DIR, prefix=".poster.", suffix=".jpg")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, 0o644)
        os.replace(tmp, dest)
        return local_url
    except Exception as e:
        print(f"WARN: no se pudo bajar póster {fname} ({e}) — uso URL remota", file=sys.stderr)
        return remote

def map_movies(results, badge):
    out = []
    for i, m in enumerate(results):
        poster = m.get("poster_path")
        if not poster:
            continue
        overview = (m.get("overview") or "").strip()
        description = overview[:97] + "..." if len(overview) > 100 else overview
        out.append({
            "id": m["id"],
            "title": m.get("title") or m.get("original_title") or "Sin título",
            "description": description or "Próximo estreno en cartelera",
            "synopsis": overview or "Sinopsis no disponible.",
            "duration": "—",
            "poster": EMOJIS[i % len(EMOJIS)],
            "badge": badge,
            "rating": "+12",
            "image": download_image(poster),
        })
    return out

def write_atomic(path, data):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".movies.", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

def main():
    token = os.environ.get("TMDB_TOKEN", "").strip()
    if not token:
        print("ERROR: TMDB_TOKEN no configurado — se conserva movies.json existente", file=sys.stderr)
        sys.exit(2)

    language = os.environ.get("TMDB_LANGUAGE", "es-MX")
    region   = os.environ.get("TMDB_REGION", "EC")
    min_n    = int(os.environ.get("TMDB_MIN_MOVIES", "4"))

    attempts = []
    if region:
        attempts.append(("/movie/now_playing", {"language": language, "region": region, "page": 1}, "ESTRENO"))
    attempts.append(("/movie/now_playing", {"language": language, "page": 1}, "ESTRENO"))
    attempts.append(("/movie/popular",     {"language": language, "page": 1}, "POPULAR"))

    movies = []
    badge = "ESTRENO"
    last_err = None
    for path, params, attempt_badge in attempts:
        try:
            data = tmdb_get(path, params, token)
            candidates = map_movies(data.get("results", []), attempt_badge)
            print(f"INFO: {path} (region={params.get('region','-')}) → {len(candidates)} películas", file=sys.stderr)
            if len(candidates) >= min_n:
                movies = candidates
                badge = attempt_badge
                break
            if len(candidates) > len(movies):
                movies = candidates
                badge = attempt_badge
        except (error.URLError, error.HTTPError, TimeoutError) as e:
            last_err = e
            print(f"WARN: {path} falló ({e})", file=sys.stderr)

    if not movies:
        print(f"ERROR: TMDB inalcanzable o sin resultados ({last_err}) — se conserva movies.json existente", file=sys.stderr)
        sys.exit(3)

    movies = movies[:12]
    write_atomic(OUT_PATH, movies)
    print(f"OK: movies.json refrescado ({len(movies)} películas, fuente={badge.lower()}, pósters locales)")

if __name__ == "__main__":
    main()
