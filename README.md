# Hsing 投資儀表板

Streamlit 台股投資儀表板，整合持股追蹤、AI/鋼鐵族群溫度、法人籌碼、新聞、反轉指標與買賣策略。

## 本機執行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 部署到 Streamlit Community Cloud

1. 將 `app.py`、`requirements.txt`、`.gitignore`、`portfolio.example.csv` 推送到 GitHub repo。
2. 不要上傳 `portfolio.csv`，此檔案包含個人持股與成本。
3. 到 https://share.streamlit.io/ 建立 New app。
4. 選擇 repo、branch，Main file path 填 `app.py`。
5. Deploy。

## 私人資料

`portfolio.csv` 已加入 `.gitignore`。如果需要公開展示，請使用 `portfolio.example.csv` 這類範本資料；如果是個人使用，建議使用 private repo 或自行部署到需要登入的主機。