import time
import os
import re
import requests
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# -----------------------------------------------------
# 設定
# -----------------------------------------------------
URL = "https://jhomes.to-kousya.or.jp/search/jkknet/service/akiyaJyoukenStartInit"
WAIT_TIME = 10
RESULT_FILE = "result_name_madori.txt"
LATEST_FILE = "latest_result.txt"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")  # user/repo

# -----------------------------------------------------
# Seleniumでページ取得
# -----------------------------------------------------
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=options)
driver.get(URL)
time.sleep(3)

# 次ページリンククリック（あれば）
try:
    next_link = driver.find_element(By.XPATH, "//a[contains(@onclick, 'submitNext')]")
    next_link.click()
    time.sleep(WAIT_TIME)
except:
    time.sleep(WAIT_TIME)

if len(driver.window_handles) > 1:
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(3)

# 検索ボタンクリック
try:
    search_button = driver.find_element(By.XPATH, "//img[@alt='検索する']/parent::a")
    search_button.click()
    time.sleep(WAIT_TIME)
except:
    pass

html = driver.page_source
driver.quit()
soup = BeautifulSoup(html, "html.parser")

# -----------------------------------------------------
# データ抽出
# -----------------------------------------------------
results = []

# 住宅名（1件ページも含む）
name_tag = soup.find("div", class_="housename cls")
name_main = name_tag.get_text(strip=True) if name_tag else ""

# tr.ListTXT1 / ListTXT2 を対象にする
rows = soup.select("tr.ListTXT1, tr.ListTXT2")

for row in rows:
    tds = row.find_all("td")
    if len(tds) < 7:
        continue

    # 間取り
    madori = tds[4].get_text(strip=True)

    # 家賃
    yachin = tds[6].get_text(strip=True)

    # 住所から市区町村を抽出
    address_td = row.find_next("td", rowspan=True)
    city = ""
    if address_td:
        m = re.search(r"(.+?区)", address_td.get_text(strip=True))
        if m:
            city = m.group(1)

    results.append({
        "住宅名": name_main,
        "市区町村": city,
        "間取り": madori,
        "家賃": yachin
    })

# -----------------------------------------------------
# 保存
# -----------------------------------------------------
now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")
with open(RESULT_FILE, "w", encoding="utf-8") as f:
    f.write(f"取得日時: {now}\n")
    f.write(f"空き住戸数: {len(results)}件\n\n")
    f.write("住宅名 | 市区町村 | 間取り | 家賃\n")
    f.write("-" * 35 + "\n")
    for r in results:
        f.write(f"{r['住宅名']} | {r['市区町村']} | {r['間取り']} | {r['家賃']}\n")

print(f"💾 {RESULT_FILE} に {len(results)} 件保存しました。")

# -----------------------------------------------------
# Discord通知
# -----------------------------------------------------
def send_discord_message(content: str):
    if not DISCORD_WEBHOOK_URL:
        return
    data = {"content": f"📢 **空室情報更新**\n```{content}```", "username": "jkkchecker"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
    except:
        pass

def read_file_normalized(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    return [re.sub(r"\s+", " ", ln.replace("\u3000", " ").strip()) for ln in lines[3:]]

def read_full(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# 差分チェック
curr_main = read_file_normalized(RESULT_FILE)
prev_main = read_file_normalized(LATEST_FILE)

if prev_main == []:
    send_discord_message(read_full(RESULT_FILE)[:1900])
    print("📁 latest_result.txt が存在しません。初回通知を行います。")
elif curr_main != prev_main:
    send_discord_message(read_full(RESULT_FILE)[:1900])
    print("🔔 差分あり。Discordに通知します。")
else:
    print("✅ 内容に変更なし。Discord通知は行いません。")

# 最新ファイル上書き
with open(RESULT_FILE, "r", encoding="utf-8") as src, open(LATEST_FILE, "w", encoding="utf-8") as dst:
    dst.write(src.read())

# -----------------------------------------------------
# Git commit & push
# -----------------------------------------------------
try:
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", LATEST_FILE], check=True)
    subprocess.run(["git", "commit", "-m", f"Update {LATEST_FILE} ({now})"], check=True)
    push_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"
    subprocess.run(["git", "push", push_url, "HEAD:main"], check=True)
    print(f"✅ {LATEST_FILE} を GitHub にコミット & pushしました")
except subprocess.CalledProcessError:
    pass

print(f"🏠 実行時刻: {now}")
