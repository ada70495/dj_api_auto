"""本地被测服务：DJ 音乐播放器接口

启动：
    python mock_server/app.py
    $env:PORT=9301; python mock_server/app.py

环境变量：
    PORT         监听端口，默认 9300
    SIGN_CHECK   是否强制校验签名，默认 false
    SIGN_KEY     签名密钥，默认 mock-sign-key-2026

业务约定：HTTP 状态码统一 200，用响应体里的 code 区分结果
    200 成功 / 400 参数非法或状态不允许 / 401 未登录或签名错误 / 404 歌曲不存在 / 409 重复
"""
import hashlib
import os

from flask import Flask, jsonify, request

app = Flask(__name__)
app.json.ensure_ascii = False

SIGN_CHECK = os.getenv("SIGN_CHECK", "false").strip().lower() in ("1", "true", "yes")
SIGN_KEY = os.getenv("SIGN_KEY", "mock-sign-key-2026")

EQ_MODES = {"normal", "rock", "jazz", "vocal"}
PLAY_MODES = {"sequence", "loop", "single", "random"}

SONGS = [
    {"song_id": 1, "name": "夜航", "artist": "Mock Band", "duration": 214},
    {"song_id": 2, "name": "霓虹", "artist": "Mock Band", "duration": 188},
    {"song_id": 3, "name": "晚风", "artist": "Mock Band", "duration": 240},
    {"song_id": 4, "name": "回声", "artist": "Mock Band", "duration": 196},
]


def init_state():
    return {
        "current": None,      # 当前歌曲 ID
        "playing": False,
        "volume": 50,
        "eq": "normal",
        "play_mode": "sequence",
    }


STATE = init_state()


def ok(data=None, msg="success"):
    return jsonify({"code": 200, "msg": msg, "data": data})


def fail(code, msg):
    return jsonify({"code": code, "msg": msg, "data": None})


def body():
    return request.get_json(silent=True) or {}


def find_song(song_id):
    return next((s for s in SONGS if s["song_id"] == song_id), None)


def make_sign(method, path, payload):
    """签名算法：方法 + 路径 + 按键排序的入参 + 密钥，做 MD5"""
    parts = [method.upper(), path]
    if isinstance(payload, dict):
        for key in sorted(payload):
            parts.append(f"{key}={payload[key]}")
    raw = "&".join(parts) + "&key=" + SIGN_KEY
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


@app.before_request
def check_sign():
    if not SIGN_CHECK:
        return None
    if request.path in ("/health", "/__admin/reset"):
        return None
    incoming = request.headers.get("X-Sign", "")
    payload = body() if request.method in ("POST", "PUT", "DELETE") else request.args.to_dict()
    if not incoming or incoming != make_sign(request.method, request.path, payload):
        return fail(401, "签名校验失败")
    return None


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "mock-dj-api", "sign_check": SIGN_CHECK})


@app.post("/__admin/reset")
def reset():
    global STATE
    STATE = init_state()
    return ok({"reset": True})


# ---------------- 用户 ----------------
@app.post("/user/login")
def login():
    data = body()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username:
        return fail(400, "用户名不能为空")
    if password != "123456":
        return fail(401, "用户名或密码错误")
    return ok({"token": "mock-token-testuser-2026", "user_id": 1001, "username": username})


# ---------------- 歌单与播放 ----------------
@app.get("/dj/playlist")
def dj_playlist():
    return ok({"total": len(SONGS), "list": SONGS})


@app.get("/dj/status")
def dj_status():
    """播放器当前状态：音量、均衡器、播放模式、播放中曲目"""
    song = find_song(STATE["current"]) if STATE["current"] is not None else None
    return ok(
        {
            "volume": STATE["volume"],
            "eq": STATE["eq"],
            "play_mode": STATE["play_mode"],
            "playing": STATE["playing"],
            "current": STATE["current"],
            "current_name": song["name"] if song else None,
        }
    )


@app.post("/dj/play")
def dj_play():
    data = body()
    song_id = data.get("song_id")
    if song_id is None:
        return fail(400, "song_id 不能为空")
    song = find_song(song_id)
    if song is None:
        return fail(404, "歌曲不存在")
    STATE["current"] = song_id
    STATE["playing"] = True
    return ok(
        {
            "song_id": song_id,
            "name": song["name"],
            "playing": True,
            "duration": song["duration"],
        }
    )


@app.post("/dj/pause")
def dj_pause():
    if STATE["current"] is None or not STATE["playing"]:
        return fail(400, "当前没有正在播放的歌曲")
    STATE["playing"] = False
    return ok({"song_id": STATE["current"], "playing": False})


def _switch(direction):
    if STATE["current"] is None:
        return fail(400, "当前没有正在播放的歌曲")
    index = next(i for i, s in enumerate(SONGS) if s["song_id"] == STATE["current"])
    song = SONGS[(index + direction) % len(SONGS)]
    STATE["current"] = song["song_id"]
    STATE["playing"] = True
    return ok(
        {
            "song_id": song["song_id"],
            "name": song["name"],
            "playing": True,
            "duration": song["duration"],
        }
    )


@app.post("/dj/next")
def dj_next():
    return _switch(1)


@app.post("/dj/prev")
def dj_prev():
    return _switch(-1)


# ---------------- 播放参数 ----------------
@app.post("/dj/volume")
def dj_volume():
    data = body()
    volume = data.get("volume")
    if not isinstance(volume, int) or isinstance(volume, bool) or not (0 <= volume <= 100):
        return fail(400, "音量必须在 0-100 之间")
    STATE["volume"] = volume
    return ok({"volume": volume})


@app.post("/dj/eq")
def dj_eq():
    data = body()
    mode = data.get("mode")
    if mode not in EQ_MODES:
        return fail(400, "均衡器模式仅支持 normal/rock/jazz/vocal")
    STATE["eq"] = mode
    return ok({"mode": mode})


@app.post("/dj/play_mode")
def dj_play_mode():
    data = body()
    mode = data.get("mode")
    if mode not in PLAY_MODES:
        return fail(400, "播放模式仅支持 sequence/loop/single/random")
    STATE["play_mode"] = mode
    return ok({"mode": mode})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "9300"))
    print(f"Mock DJ 服务启动：http://0.0.0.0:{port}  签名校验={SIGN_CHECK}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
