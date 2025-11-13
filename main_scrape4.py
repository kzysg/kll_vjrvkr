import time
import datetime
import re
import os
import requests
import difflib
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# -----------------------------------------------------
# 設定
# -----------------------------------------------------
URL = "https://jhomes.to-kousya.or.jp/search/jkknet/service/akiyaJyoukenStartInit"
WAIT_TIME = 10  # ページロード待機秒数
RESULT_FILE = "result_name_madori.txt"
PREV_FILE = "previous_result.txt"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# -----------------------------------------------------
# 関数定義
# -----------------------------------------------------
def send_discord_message(content: str):
    """Discordに通知"""
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ Discord Webhook が未設定")
        return
    data = {
        "content": f"📢 **空室情報更新**\n```{content}```",
        "username": "jkkchecker"
    }
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
        print(f"📤 Discord POST -> status: {r.status_code}")
    except Exception as e:
        print("⚠️ Discord送信で例外:", e)


def read_file_normalized(path: str):
    """4行目以降を正規化して読み込む"""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    norm_lines = [re.sub(r"\s+", " ", ln.replace("\u3000", " ").strip()) for ln in lines[3:]]
    return norm_lines


def read_full(path: str):
    """ファイル全体を読み込む"""
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# -----------------------------------------------------
# スクレイピング開始
# -----------------------------------------------------
print("🚀 スクレイピング開始")

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=options)
driver.get(URL)
time.sleep(3)

# 「次へ」ボタンをクリック
try:
    next_link = driver.find_element(By.XPATH, "//a[contains(@onclick, 'submitNext')]")
    next_link.click()
    print("✅ ページ遷移")
    time.sleep(WAIT_TIME)
except Exception as e:
    print("⚠️ 自動リダイレクト待機:", e)
    time.sleep(WAIT_TIME)

# 新しいウィンドウへ
if len(driver.window_handles) > 1:
    driver.switch_to.window(driver.window_handles[-1])
    print("✅ 新ウィンドウ切替")
    time.sleep(3)

# 検索条件入力
#try:
#    driver.find_element(By.CSS_SELECTOR, 'input[value="12"][type="checkbox"]').click()
#    driver.find_element(By.CSS_SELECTOR, 'input[value="11"][type="checkbox"]').click()
#    print("✅ 世田谷区・大田区を選択")
#except Exception as e:
#    print("❌ チェックボックスエラー:", e)

# 検索実行
#try:
#    search_button = driver.find_element(By.XPATH, "//img[@alt='検索する']/parent::a")
#    search_button.click()
#    print("✅ 検索ボタンクリック")
#    time.sleep(WAIT_TIME)
#except Exception as e:
#    print("❌ 検索ボタンクリック失敗:", e)
#
html = driver.page_source
driver.quit()

# -----------------------------------------------------
# 検索結果の抽出
# -----------------------------------------------------
soup = BeautifulSoup(html, "html.parser")
results = []
rows = soup.find_all("tr", class_=re.compile(r"ListTXT[12]"))

for row in rows:
    cols = [td.get_text(strip=True) for td in row.find_all("td")]
    if len(cols) >= 10:
        name = cols[1]
        city = cols[2]
        madori = cols[5]
        yachin = cols[7]
    else:
        continue

    a_tag = row.find("a", href=re.compile(r"senPage"))
    boshuNo = jyutakuCd = yusenKbn = ""
    if a_tag and "onclick" in a_tag.attrs:
        m = re.search(r"senPage\('','([A-Z0-9]+)','(\d+)','(\d+)'\)", str(a_tag["onclick"]))
        if m:
            boshuNo, jyutakuCd, yusenKbn = m.groups()

    results.append({
        "住宅名": name,
        "市区町村": city,
        "間取り": madori,
        "家賃": yachin,
        "募集番号": boshuNo,
        "住宅コード": jyutakuCd,
        "優先区分": yusenKbn
    })

# -----------------------------------------------------
# 結果をファイルに保存
# -----------------------------------------------------
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
with open(RESULT_FILE, "w", encoding="utf-8") as f:
    f.write(f"取得日時: {now}\n")
    f.write(f"空き住戸数: {len(results)}件\n\n")
    f.write("住宅名 | 市区町村 | 間取り | 家賃\n")
    f.write("-" * 35 + "\n")
    for r in results:
        f.write(f"{r['住宅名']} | {r['市区町村']} | {r['間取り']} | {r['家賃']}\n")

print(f"💾 {RESULT_FILE} に {len(results)} 件保存しました。")

# -----------------------------------------------------
# 差分比較
# -----------------------------------------------------
curr_main = read_file_normalized(RESULT_FILE)
prev_main = read_file_normalized(PREV_FILE)

if not os.path.exists(PREV_FILE) or prev_main == []:
    print("📁 前回データなし → 初回通知")
    full = read_full(RESULT_FILE)
    send_discord_message(full[:1900])

elif curr_main != prev_main:
    print("🔔 差分あり → Discord通知")
    diff = list(difflib.unified_diff(prev_main, curr_main, lineterm=""))
    print("\n".join(diff[:40]))  # ログ出力は最初の40行まで
    full = read_full(RESULT_FILE)
    send_discord_message(full[:1900])
else:
    print("✅ 差分なし → 通知スキップ")

# -----------------------------------------------------
# キャッシュ更新（日時も常に新規）
# -----------------------------------------------------
with open(RESULT_FILE, "r", encoding="utf-8") as src, open(PREV_FILE, "w", encoding="utf-8") as dst:
    dst.write(src.read())

print(f"📦 キャッシュ更新完了: {PREV_FILE}")

print(f"🏁 実行完了 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
