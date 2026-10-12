---
description: 上網找某家手搖飲店（品牌或單一分店）的最新菜單，寫入 bubble-tea-menus.json 並推送上線
argument-hint: 店名，例如「米里 旗山店」
---

幫我把「$ARGUMENTS」的最新飲料菜單加進手搖飲選擇器（bubble-tea-picker.html）。

0. **先同步**：確認工作目錄沒有未提交的修改（有的話停下來問我），然後 `git checkout main && git pull --ff-only origin main`。
1. **上網找菜單**。依序優先採用：店家官網 → 官方 Facebook／Instagram 菜單貼文 → 外送平台（foodpanda、Uber Eats）該分店頁面 → 2025 年以後的網誌或媒體整理（菜單照片或逐項抄錄）。
   - 只收你在來源上確實看到的品項，不要憑記憶補。
   - 只收常態菜單，不含季節限定；保留店家自己的分類與品名（繁體中文），去掉價格、容量、冷熱標示與加料清單。
   - 找不到可靠來源就停下來告訴我，不要寫入。
2. **判斷是品牌還是單一分店**：
   - 連鎖品牌、各店菜單相同 → 建一筆品牌菜單，`--match` 寫品牌名（含常見別名、英文名，用 `|` 分隔）。
   - 只有這家分店菜單不同、或是只有一家的獨立店 → 建一筆分店菜單，`--id` 用「品牌-地名」（如 `mili-qishan`），`--match` 寫成「品牌.*地名」（如 `米里.*旗山`）。網頁會優先採用比對到最長文字的規則，所以分店菜單會蓋過品牌菜單。
   - 先執行 `python3 tools/menu_tool.py list` 看看是否已有這個品牌，已有就沿用它的 id 更新。
3. **寫入**：把菜單整理成文字（每行「分類：品項、品項、品項」），存成暫存檔後執行：
   ```
   python3 tools/menu_tool.py add --id <id> --name "<顯示名稱>" --match "<正規表示式>" \
     --url "<官網或粉專>" --source "<主要來源網址>" --source-date <菜單版本日期，如 2026-10> \
     --source-type <官網|官方粉專|外送平台|媒體整理> --confidence <high|medium|low> --menu-file <暫存檔>
   ```
   然後執行 `python3 tools/menu_tool.py check` 與 `python3 tools/menu_tool.py show <id>`，確認內容。
4. **推送上線**：
   ```
   git add bubble-tea-menus.json
   git commit -m "手搖飲菜單：新增／更新 <顯示名稱>"
   git push origin main
   ```
   推上 main 後 GitHub Pages 約 1 分鐘內會部署；使用者下次開啟頁面時會收到「菜單已更新」提示。
5. 最後用一段話告訴我：寫入了哪一筆（品牌或分店）、幾個品項、來源與可信度，以及有什麼不確定的地方。
