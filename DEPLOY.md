# Arsen Industrial 網站 — 上線步驟（Hostinger VPS 2.25.83.183）

VPS 上已有 /docker/traefik（處理 HTTPS）和 /docker/n8n-on87。
網站是第三個專案 /docker/arsen-site，用同一個 Traefik，不影響 n8n。

## 第一次設定
1. GoDaddy DNS：A @ → 2.25.83.183；CNAME www → arsen-industrial.com
2. 把 deploy/ 的 docker-compose.yml 和 nginx.conf 放到 VPS 的 /docker/arsen-site/
3. 上傳網站（Windows PowerShell，在 arsen-site 資料夾裡）：
   scp -r dist/* root@2.25.83.183:/docker/arsen-site/html/
4. VPS 上：cd /docker/arsen-site && docker compose up -d
5. 測試 https://arsen-industrial.com

## 之後更新內容
改 content/ → python build.py → 重做第 3 步的 scp（不用重啟容器）

## 正式開放 Google 收錄前
site.yaml 的 noindex 改成 false，換上真的信箱和規格。
