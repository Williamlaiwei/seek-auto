# 版本更新紀錄 / Changelog

此檔記錄已發布版本的實際差異；完整操作流程、升級步驟與限制另見各版本說明。

## [v0.2.0 — 第二版](https://github.com/Williamlaiwei/seek-auto/releases/tag/v0.2.0) · 2026-11-24

### 使用介面

- SEEK 搜尋區由「預設收合」改為「預設展開」。進入首頁即可看到職稱／關鍵字、地點與 Search jobs 按鈕。
- 搜尋切換按鈕的初始 `aria-expanded` 改為 `true`，與實際顯示狀態一致；仍可按按鈕收合與再次展開。
- 頁面標示 `v0.2.0`，方便辨識目前使用的版本。

### 文件與版本交付

- 新增根目錄 `VERSION`，標示原始碼版本。
- README 標明第二版、發布日期，連結完整版本說明與更新紀錄。
- 新增 [第二版詳細說明](docs/releases/v0.2.0.md)：版本差異、安裝、完整操作流程、資料移轉、回復與已知限制。
- 發布 ZIP 加入 `.gitignore`、更新紀錄、第二版說明及 CI/CD 指南；持續採用檔案白名單，排除個人資料。
- GitHub Release 優先採用與版本標籤同名的 Markdown 說明；沒有對應檔案時才使用自動產生的說明。

### 相容性

- Python 需求維持 3.10+；日常執行仍不需安裝第三方 Python 套件或 Node.js。
- 本次沒有資料庫結構變更；可沿用 v0.1.0 的 `.local/` 資料夾。
- 職缺匯入、分析、Cover Letter 生成、修改、版本歷史與申請狀態均沿用既有功能。

## [v0.1.0 — 第一版](https://github.com/Williamlaiwei/seek-auto/releases/tag/v0.1.0) · 2026-11-22

### 初始獨立版本

- 發布以 Python 標準函式庫與原生 HTML/CSS/JavaScript 建立的本機 SEEK CL Studio。
- 支援 SEEK 網址匯入、澳洲職缺搜尋與手動貼上職缺描述。
- 提供個人背景、寫作偏好、Chat Completions 相容 AI 設定、職缺分析與英文 Cover Letter。
- 支援草稿編輯、自動儲存、重寫、歷史版本、複製、篩選、匯出與申請狀態追蹤。
- 修正 SEEK 職缺詳細內容的匯入，加入回歸測試。
- 加入 Windows／Linux 後端與瀏覽器檢查、發布 ZIP 測試、SHA-256 校驗與 GitHub Release 自動發布。

[比較 v0.1.0 與 v0.2.0](https://github.com/Williamlaiwei/seek-auto/compare/v0.1.0...v0.2.0)
