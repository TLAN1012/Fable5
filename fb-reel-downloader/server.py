#!/usr/bin/env python3
"""
FB Reel Downloader — 一個給 iOS 捷徑(Shortcut)用的小後端。

iPad 跑不了 yt-dlp，所以由這個服務代勞：
  - POST/GET /dl   貼一個 Facebook reel/影片網址 → 直接回傳 mp4（捷徑收下後存相簿/檔案）
  - POST/GET /info 同樣貼網址 → 回傳 JSON metadata（標題、作者、縮圖、時長…），方便日後做素材庫
  - GET  /health   健康檢查

安全：用一組 token 保護（環境變數 FB_DL_TOKEN）。只接受 facebook.com 網域，避免被當成
任意網址下載的跳板（SSRF）。
"""
import os
import re
import shutil
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify, send_file, abort, after_this_request
from yt_dlp import YoutubeDL

app = Flask(__name__)

# 一組你自己設的密碼；沒設的話服務會拒絕啟動式地警告（仍可跑，但任何人都能用）
TOKEN = os.environ.get("FB_DL_TOKEN", "")

# 只允許 Facebook 系網域，擋掉把本服務當成任意下載跳板的濫用
ALLOWED_HOST_RE = re.compile(
    r"^(?:[\w-]+\.)*(?:facebook\.com|fb\.watch|fb\.me)$", re.IGNORECASE
)

# yt-dlp 共用設定：抓最佳 mp4，安靜模式
def make_ydl_opts(outtmpl=None, download=False):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        # 偏好已合好音畫的單一 mp4（環境沒有 ffmpeg 也能用）；退而求其次抓最佳
        "format": "best[ext=mp4]/best",
        "restrictfilenames": True,
    }
    if outtmpl:
        opts["outtmpl"] = outtmpl
    return opts


def get_url_param():
    """從 query string、JSON body 或表單取得 url。"""
    if request.is_json:
        data = request.get_json(silent=True) or {}
        if data.get("url"):
            return data["url"].strip()
    return (request.values.get("url") or "").strip()


def check_token():
    if not TOKEN:
        # 沒設 token 就放行，但這是不安全的，README 會提醒
        return
    supplied = request.values.get("token") or request.headers.get("X-Token", "")
    if supplied != TOKEN:
        abort(403, description="invalid or missing token")


def validate_fb_url(url):
    from urllib.parse import urlparse

    if not url:
        abort(400, description="missing 'url'")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        abort(400, description="url must be http(s)")
    if not ALLOWED_HOST_RE.match(parsed.netloc):
        abort(400, description="only facebook.com / fb.watch / fb.me urls are allowed")
    return url


@app.after_request
def add_cors(resp):
    # 讓 GitHub Pages 上的靜態網頁能跨網域呼叫本服務
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Token"
    return resp


@app.route("/dl", methods=["OPTIONS"])
@app.route("/info", methods=["OPTIONS"])
def preflight():
    return ("", 204)


@app.get("/health")
def health():
    return jsonify(status="ok", token_protected=bool(TOKEN))


@app.route("/info", methods=["GET", "POST"])
def info():
    check_token()
    url = validate_fb_url(get_url_param())
    with YoutubeDL(make_ydl_opts(download=False)) as ydl:
        data = ydl.extract_info(url, download=False)
    # 挑出對素材庫有用的欄位
    fields = (
        "id", "title", "description", "uploader", "uploader_id",
        "duration", "width", "height", "thumbnail", "view_count",
        "like_count", "webpage_url", "ext", "filesize_approx",
    )
    out = {k: data.get(k) for k in fields}
    return jsonify(out)


@app.route("/dl", methods=["GET", "POST"])
def download():
    check_token()
    url = validate_fb_url(get_url_param())

    tmpdir = tempfile.mkdtemp(prefix="fbreel_")

    @after_this_request
    def cleanup(response):
        shutil.rmtree(tmpdir, ignore_errors=True)
        return response

    outtmpl = str(Path(tmpdir) / "%(id)s.%(ext)s")
    with YoutubeDL(make_ydl_opts(outtmpl=outtmpl, download=True)) as ydl:
        data = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(data)

    fpath = Path(filename)
    if not fpath.exists():
        # 某些情況下副檔名被改寫，掃資料夾找實際檔案
        files = list(Path(tmpdir).iterdir())
        if not files:
            abort(502, description="download produced no file")
        fpath = files[0]

    safe_title = re.sub(r"[^\w\-]+", "_", (data.get("title") or data.get("id") or "reel"))[:60]
    download_name = f"{safe_title}.{fpath.suffix.lstrip('.') or 'mp4'}"

    return send_file(
        fpath,
        mimetype="video/mp4",
        as_attachment=True,
        download_name=download_name,
        conditional=False,
    )


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(500)
@app.errorhandler(502)
def handle_err(e):
    return jsonify(error=getattr(e, "description", str(e)), code=getattr(e, "code", 500)), getattr(e, "code", 500)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    if not TOKEN:
        print("⚠️  警告：未設定 FB_DL_TOKEN，服務沒有密碼保護，任何人知道網址都能使用。")
    app.run(host="0.0.0.0", port=port)
