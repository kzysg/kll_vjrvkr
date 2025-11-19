import time
import datetime
import re
import os
import requests
import difflib
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+


# ファイル名
RESULT_FILE = "result_name_madori.txt"
LATEST_FILE = "latest_result.txt"

# 環境変数
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # 自動トークン
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")  # user/repo

# -----------------------------------------------------
# スクレイピング設定
# -----------------------------------------------------
URL = "https://jhomes.to-kousya.or.jp/search/jkknet/service/akiyaJyoukenStartInit"
WAIT_TIME = 10

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=options)
driver.get(URL)
time.sleep(3)

# ページ遷移
try:
    next_link = driver.find_element(By.XPATH, "//a[contains(@onclick, 'submitNext')]")
    next_link.click()
    time.sleep(WAIT_TIME)
except:
    time.sleep(WAIT_TIME)

if len(driver.window_handles) > 1:
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(3)

#チェックボックス操作（世田谷区・大田区・板橋区）
for value in ["12", "11", "19"]:
    try:
        checkbox = driver.find_element(By.CSS_SELECTOR, f'input[value="{value}"][type="checkbox"]')
        checkbox.click()
        time.sleep(0.5)
    except:
        pass

# 検索ボタンクリック
try:
    search_button = driver.find_element(By.XPATH, "//img[@alt='検索する']/parent::a")
    search_button.click()
    time.sleep(WAIT_TIME)
except:
    pass

# HTML取得
html = driver.page_source
driver.quit()
soup = BeautifulSoup(html, "html.parser")
with open("page_source.html", "w", encoding="utf-8") as f:
    f.write(html)

# HTMLからテキスト抽出
lines = []
for tr in soup.find_all("tr"):
    cols = [td.get_text(strip=True) for td in tr.find_all("td")]  # trタグを順に処理
    if cols:
        line = "｜".join(cols)  # 列の間に｜を入れて1行に
        lines.append(line)
lines = [line for line in lines if line.strip()]  # 空白行や余分なスペースを削除

# 保存
text_path = "page_text.txt"
with open(text_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"💾 {text_path} にテキストを保存しました")



# 結果取得
#results = []
#rows = soup.find_all("tr", class_=re.compile(r"ListTXT[12]"))
#for row in rows:
#    cols = [td.get_text(strip=True) for td in row.find_all("td")]
#    if len(cols) >= 10:
#        name, city, madori, yachin = cols[1], cols[2], cols[5], cols[7]
#    else:
#        continue
#    # 募集番号など
#    a_tag = row.find("a", href=re.compile(r"senPage"))
#    if a_tag and "onclick" in a_tag.attrs:
#        m = re.search(r"senPage\('','([A-Z0-9]+)','(\d+)','(\d+)'\)", a_tag["onclick"])
#        boshuNo, jyutakuCd, yusenKbn = m.groups() if m else ("", "", "")
#    else:
#        boshuNo = jyutakuCd = yusenKbn = ""
#    results.append({
#        "住宅名": name,
#        "市区町村": city,
#        "間取り": madori,
#        "家賃": yachin,
#        "募集番号": boshuNo,
#        "住宅コード": jyutakuCd,
#        "優先区分": yusenKbn
#    })

# -----------------------------------------------------
# 検索結果の取得（改良版：1件/複数件どちらにも対応）
# -----------------------------------------------------

results = []

# 「ListTXT1」または「ListTXT2」クラスを持つ <tr> をすべて取得
rows = soup.find_all("tr", class_=re.compile(r"ListTXT[12]"))

for row in rows:
    cols = [td.get_text(strip=True) for td in row.find_all("td")]
    if len(cols) >= 10:
        name = cols[1]        # 住宅名
        city = cols[2]        # 市区町村
        madori = cols[5]      # 間取り
        yachin = cols[7]      # 家賃

    # onclick="senPage('','BOSHU123','456','1')" の情報を取得
    a_tag = row.find("a", href=re.compile(r"senPage"))
    if a_tag and "onclick" in a_tag.attrs:
        m = re.search(r"senPage\('','([A-Z0-9]+)','(\d+)','(\d+)'\)", str(a_tag["onclick"]))
        if m:
            boshuNo, jyutakuCd, yusenKbn = m.groups()
        else:
            boshuNo = jyutakuCd = yusenKbn = ""
    else:
        boshuNo = jyutakuCd = yusenKbn = ""

    results.append({
        "住宅名": name,
        "市区町村": city,
        "間取り": madori,
        "家賃": yachin,
        "募集番号": boshuNo,
        "住宅コード": jyutakuCd,
        "優先区分": yusenKbn
    })

# rows.txt に保存
with open("rows.txt", "w", encoding="utf-8") as f:
    for row in rows:
        f.write(str(row) + "\n")  # row は Tag オブジェクトなので文字列化


# result_name_madori.txt 保存
now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")  # JSTタイムゾーンを指定
with open(RESULT_FILE, "w", encoding="utf-8") as f:
    f.write(f"取得日時: {now}\n")
    f.write(f"空き住戸数: {len(results)}件\n\n")
    f.write("住宅名 | 市区町村 | 間取り | 家賃\n")
    f.write("-" * 35 + "\n")
    for r in results:
        f.write(f"{r['住宅名']} | {r['市区町村']} | {r['間取り']} | {r['家賃']}\n")

print(f"💾 result_name_madori.txt に {len(results)} 件保存しました。")

# Discord通知
def send_discord_message(content: str):
    if not DISCORD_WEBHOOK_URL:
        return
    data = {"content": f"📢 **空室情報更新**\n```{content}```", "username": "jkkchecker"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
    except:
        pass

# ファイル読み込み正規化
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


# latest_result.txt 上書き
with open(RESULT_FILE, "r", encoding="utf-8") as src, open(LATEST_FILE, "w", encoding="utf-8") as dst:
    dst.write(src.read())

# Git commit & push（自動トークン対応）
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



# -----------------------------------------------------
# 出力
# -----------------------------------------------------
now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")  # JSTタイムゾーンを指定
print(f"🏠 実行時刻: {now}")
