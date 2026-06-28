# FB Reel 下載器（後端服務）

一個給瀏覽器網頁 / iOS 捷徑用的小後端：貼一個 Facebook reel／影片網址，
伺服器用 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 抓好，把 **mp4** 回傳給你。

> **為什麼需要後端？** iPad、瀏覽器都跑不了 yt-dlp，而且瀏覽器因為 CORS 也不能直接抓
> facebook.com。所以前端網頁（[`../fb-reel.html`](../fb-reel.html)）只是輸入介面，
> 真正解析、下載影片的是這支 `server.py`。你要把它跑在某個地方（家裡電腦、雲端、VPS）。

---

## 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| `GET`/`POST` | `/dl?token=XXX&url=<reel網址>` | 抓影片並以 **mp4** 附件回傳 |
| `GET`/`POST` | `/info?token=XXX&url=<reel網址>` | 回傳 JSON metadata（標題、作者、縮圖、時長…），不下載影片 |
| `GET` | `/health` | 健康檢查 |

`url` 也可以放在 JSON body：`{"url": "https://www.facebook.com/reel/..."}`。
`token` 可放 query string 或 `X-Token` header。

**安全設計**
- 用環境變數 `FB_DL_TOKEN` 設一組密碼，沒帶對 token 一律 403。**請務必設定**，否則任何人知道你的網址都能用。
- 只接受 `facebook.com` / `fb.watch` / `fb.me` 網域，避免被當成任意網址下載的跳板。

> ⚠️ 自用工具。請只下載你有權使用的內容，並遵守 Facebook 服務條款與當地著作權法。

---

## 在電腦上跑（最快）

```bash
cd fb-reel-downloader
pip install -r requirements.txt
FB_DL_TOKEN=設一組你自己的密碼 PORT=8000 python server.py
```

打開 <http://localhost:8000/health> 看到 `{"status":"ok"}` 就成功了。
> 建議裝 `ffmpeg`（`brew install ffmpeg` / `apt install ffmpeg`），遇到音畫分離的影片才能合併。

## 用 Docker 跑

```bash
cd fb-reel-downloader
docker build -t fb-reel-dl .
docker run -p 8000:8000 -e FB_DL_TOKEN=你的密碼 fb-reel-dl
```
（映像檔已內含 ffmpeg。）

## 部署到雲端讓 iPad 也連得到

`fb-reel.html` 在公開網站上（GitHub Pages）走 **https**，所以後端也必須是 **https**，
否則瀏覽器會擋混合內容。幾個簡單選項：

- **Render / Railway / Fly.io**：直接吃這個 `Dockerfile`，部署後拿到一個 `https://xxx.onrender.com`。
  記得在平台的環境變數設 `FB_DL_TOKEN`。
- **家裡電腦 + Cloudflare Tunnel / Tailscale**：本機跑 `python server.py`，用 tunnel 對外發布成 https 網址。

拿到後端網址後，到網頁的「⚙ 後端設定」填入網址與 token（只會存在你裝置的瀏覽器，不上傳）。

---

## iOS 捷徑（Shortcut）— 從 FB App 分享直接下載到相簿

不想開網頁的話，可以做一個捷徑，從 Facebook App 的「分享」直接送過來。

1. 開「捷徑」App → 新增捷徑 → 右上「ⓘ」→ 開啟 **顯示於分享工作表**，
   接收類型選 **URL**。
2. 加入動作 **取得 URL 內容（Get Contents of URL）**：
   - URL 填：`https://你的後端網址/dl?token=你的密碼`
   - 方法（Method）：**POST**
   - 內文（Request Body）：**JSON**，新增一個欄位
     - 鍵 `url` ＝ 值選「**捷徑輸入（Shortcut Input）**」
   - （用 JSON body 傳網址，省去網址編碼的麻煩）
3. 加入動作 **儲存到相簿（Save to Photo Album）**，或 **儲存檔案（Save File）** 存到「檔案」。
4. 命名例如「下載 FB Reel」。

之後在 FB App 看到 reel → 分享 → 選「下載 FB Reel」→ 影片就存進相簿了。

> 大檔（幾十 MB）伺服器要先抓好才回傳，捷徑可能轉圈十幾秒，正常。

---

## 檔案

| 檔案 | 用途 |
|------|------|
| `server.py` | Flask 後端，`/dl`、`/info`、`/health` |
| `requirements.txt` | Python 相依套件 |
| `Dockerfile` | 容器化部署（含 ffmpeg） |
| `../fb-reel.html` | 前端網頁（GitHub Pages 上的輸入介面） |
