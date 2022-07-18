from flask import Flask, url_for, session, redirect, jsonify, abort, render_template, request
from config import config
import time

from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from authlib.common.security import generate_token
import datetime

app = Flask(__name__)

app.secret_key = config["app-secret"]
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=7)
app.config["SESSION_REFRESH_EACH_REQUEST"] = False

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
        session.permanent = True
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
    date = request.args.get("date", None)
    if date:
        try:
            date = datetime.datetime.strptime(date, "%m-%d-%Y")
        except:
            date = datetime.datetime.today()
    else:
        date = datetime.datetime.today()
    user = get_user()
    animelist = {}
    animelist["watching"] = perform_filter(get_user_animelist("watching"), date)
    animelist["plan_to_watch"] = perform_filter(get_user_animelist("plan_to_watch"), date)
    return jsonify(user=user, animelist=animelist)

def perform_filter(animelist, date):
    result = []
    for anime in animelist:
        anime = anime["node"]
        modifier = 1
        if anime.get("media_type", None) == "movie":
            modifier = 6
        if anime["status"] == "currently_airing" and (date.date() == datetime.datetime.today().date() or anime.get("end_date", None) is None) \
                or (anime["status"] == "not_yet_aired" and anime.get("start_date", None) and len(anime["start_date"]) == 10 and date + datetime.timedelta(days=5) >= datetime.datetime.strptime(anime["start_date"], "%Y-%m-%d")) \
                or (anime["status"] == "finished_airing" and anime.get("end_date", None) and len(anime["end_date"]) == 10 and date - datetime.timedelta(days=7 * modifier) <= datetime.datetime.strptime(anime["end_date"], "%Y-%m-%d")):
            result.append(anime)
    return result

def get_user():
    resp = mal.get("users/@me", token=session["token"])
    resp.raise_for_status()
    return resp.json()

def get_user_animelist(status=None):
    data = []
    while len(data) % 1000 == 0:
        params = {"limit": 1000, "offset": len(data), "fields": "list_status,broadcast,node.status,start_date,end_date,media_type,average_episode_duration,my_list_status,my_list_status{{comments}}", "nsfw": "true"}
        if status:
            params["status"] = status
        resp = mal.get("users/@me/animelist", params=params, token=session["token"])
        resp.raise_for_status()
        resp_json = resp.json()
        data.extend(resp_json["data"])
        if not resp_json.get("paging", None) or not resp_json["paging"].get("next", None):
            break
    return data

@app.route("/raw")
def raw():
    if "token" not in session:
        abort(401)
    status = request.args.get("status", None)
    animelist = {}
    animelist = get_user_animelist(status)
    return jsonify(animelist=animelist)
