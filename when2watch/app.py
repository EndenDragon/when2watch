from flask import Flask, url_for, session, redirect, jsonify, abort, render_template
from config import config

from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from authlib.common.security import generate_token
from expiringdict import ExpiringDict

app = Flask(__name__)

app.secret_key = config["app-secret"]

oauth = OAuth()
oauth.init_app(app)

code_verifier = generate_token(48)

mal = oauth.register("mal", 
    client_id = config["client-id"],
    client_secret = config["client-secret"],
    access_token_url = "https://myanimelist.net/v1/oauth2/token",
    authorize_url = "https://myanimelist.net/v1/oauth2/authorize",
    api_base_url = "https://api.myanimelist.net/v2/"
)

cache = ExpiringDict(max_len=2000, max_age_seconds=43200)

@app.route("/login")
def login():
    code_challenge = create_s256_code_challenge(code_verifier)
    session["code_challenge"] = code_challenge
    redirect_uri = url_for("authorize", _external=True)
    return mal.authorize_redirect(redirect_uri, code_challenge=code_challenge)

@app.route("/authorize")
def authorize():
    token = mal.authorize_access_token(code_verifier=session["code_challenge"])
    session["token"] = token
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api")
def api():
    if "token" not in session:
        abort(401)
    user = get_user()
    animelist = {}
    animelist["watching"] = perform_filter(get_user_animelist("watching"))
    animelist["plan_to_watch"] = perform_filter(get_user_animelist("plan_to_watch"))
    return jsonify(user=user, animelist=animelist)

def perform_filter(animelist):
    result = []
    for anime in animelist:
        anime = anime["node"]
        details = get_anime_details(anime["id"])
        if details["status"] == "currently_airing":
            anime["broadcast"] = details.get("broadcast", None)
            result.append(anime)
    return result

def get_anime_details(anime_id):
    if anime_id in cache:
        return cache[anime_id]
    resp = mal.get("anime/{}?fields=id,title,status,broadcast".format(anime_id), token=session["token"])
    resp.raise_for_status()
    result = resp.json()
    cache[anime_id] = result
    return result

def get_user():
    resp = mal.get("users/@me", token=session["token"])
    resp.raise_for_status()
    return resp.json()

def get_user_animelist(status=None):
    data = []
    while len(data) % 1000 == 0:
        params = {"limit": 1000, "offset": len(data)}
        if status:
            params["status"] = status
        resp = mal.get("users/@me/animelist", params=params, token=session["token"])
        resp.raise_for_status()
        resp_json = resp.json()
        data.extend(resp_json["data"])
        if not resp_json.get("paging", None) or not resp_json["paging"].get("next", None):
            break
    return data
