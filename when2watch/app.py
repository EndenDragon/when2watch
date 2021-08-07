from flask import Flask, url_for, session, redirect, jsonify, abort, render_template, request
from config import config
import time

from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from authlib.common.security import generate_token
import datetime

app = Flask(__name__)

app.secret_key = config["app-secret"]

oauth = OAuth()
oauth.init_app(app)

code_verifier = generate_token(48)
app_start_stamp = time.time()

mal = oauth.register("mal",
    client_id = config["client-id"],
    client_secret = config["client-secret"],
    access_token_url = "https://myanimelist.net/v1/oauth2/token",
    authorize_url = "https://myanimelist.net/v1/oauth2/authorize",
    api_base_url = "https://api.myanimelist.net/v2/"
)

@app.route("/login")
def login():
    code_challenge = create_s256_code_challenge(code_verifier)
    session["code_challenge"] = code_challenge
    redirect_uri = url_for("authorize", _external=True)
    return mal.authorize_redirect(redirect_uri, code_challenge=code_challenge)

@app.route("/authorize")
def authorize():
    error = request.args.get("error", None)
    if not error:
        token = mal.authorize_access_token(code_verifier=session["code_challenge"])
        session["token"] = token
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/")
def index():
    return render_template("index.html", app_start_stamp=app_start_stamp)

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
    today = datetime.datetime.today()
    result = []
    for anime in animelist:
        anime = anime["node"]
        if anime["status"] == "currently_airing" \
                or (anime["status"] == "not_yet_aired" and anime.get("start_date", None) and len(anime["start_date"]) == 10 and today + datetime.timedelta(days=5) >= datetime.datetime.strptime(anime["start_date"], "%Y-%m-%d")) \
                or (anime["status"] == "finished_airing" and anime.get("end_date", None) and len(anime["end_date"]) == 10 and today - datetime.timedelta(days=7) <= datetime.datetime.strptime(anime["end_date"], "%Y-%m-%d")):
            result.append(anime)
    return result

def get_user():
    resp = mal.get("users/@me", token=session["token"])
    resp.raise_for_status()
    return resp.json()

def get_user_animelist(status=None):
    data = []
    while len(data) % 1000 == 0:
        params = {"limit": 1000, "offset": len(data), "fields": "list_status,broadcast,node.status,start_date,end_date"}
        if status:
            params["status"] = status
        resp = mal.get("users/@me/animelist", params=params, token=session["token"])
        resp.raise_for_status()
        resp_json = resp.json()
        data.extend(resp_json["data"])
        if not resp_json.get("paging", None) or not resp_json["paging"].get("next", None):
            break
    return data
