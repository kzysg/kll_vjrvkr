import time
import datetime
import re
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

# -----------------------------------------------------
# ブラウザ起動
# -----------------------------------------------------
options = Options()  
options.add_argument("--headless")  # 画面を表示しない
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=options)
driver.get(URL)
time.sleep(3)

# 待機ページから次のページへ進む（リンクをクリック）
try:
    next_link = driver.find_element(By.XPATH, "//a[contains(@onclick, 'submitNext')]")
    next_link.click()
    print("✅ 次のページへのリンクをクリックしました")
    time.sleep(WAIT_TIME)
except Exception as e:
    print("⚠️ リンククリック失敗（自動リダイレクト待機中）:", e)
    time.sleep(WAIT_TIME)

# ウィンドウハンドルを切り替える（新しいウィンドウが開いた場合）
if len(driver.window_handles) > 1:
    driver.switch_to.window(driver.window_handles[-1])
    print("✅ 新しいウィンドウに切り替えました")
    time.sleep(3)

# デバッグ: 現在のページのHTMLを保存
with open("page_source.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("📄 ページのHTMLを page_source.html に保存しました")

# -----------------------------------------------------
# 「世田谷区」と「大田区」にチェックを入れる
# -----------------------------------------------------
try:
    # 世田谷区 (value="12")
    checkbox_setagaya = driver.find_element(By.CSS_SELECTOR, 'input[value="12"][type="checkbox"]')
    checkbox_setagaya.click()
    print("✅ 世田谷区にチェックを入れました")
    time.sleep(0.5)

    # 大田区 (value="11")
    checkbox_ota = driver.find_element(By.CSS_SELECTOR, 'input[value="11"][type="checkbox"]')
    checkbox_ota.click()
    print("✅ 大田区にチェックを入れました")
    time.sleep(1)
except Exception as e:
    print("❌ チェックボックス操作エラー:", e)


# -----------------------------------------------------
# 「検索」ボタンをクリック
# -----------------------------------------------------
try:
    # 画像のalt属性で検索ボタンを探す
    search_button = driver.find_element(By.XPATH, "//img[@alt='検索する']/parent::a")
    search_button.click()
    print("✅ 検索ボタンをクリックしました")
    time.sleep(WAIT_TIME)
    
    # 検索結果ページのHTMLを保存
    with open("search_result.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("📄 検索結果ページを search_result.html に保存しました")
except Exception as e:
    print("❌ 検索ボタンクリック失敗:", e)

# -----------------------------------------------------
# 検索結果の取得（改良版：1件/複数件どちらにも対応）
# -----------------------------------------------------
html = driver.page_source
driver.quit()

soup = BeautifulSoup(html, "html.parser")

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

# -----------------------------------------------------
# 結果を result_name_madori.txt に保存
# -----------------------------------------------------
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open("result_name_madori.txt", "w", encoding="utf-8") as f:
    f.write(f"取得日時: {now}\n")
    f.write(f"空き住戸数: {len(results)}件\n\n")
    f.write("住宅名 | 市区町村 | 間取り | 家賃\n")
    f.write("-" * 60 + "\n")
    for r in results:
        f.write(f"{r['住宅名']} | {r['市区町村']} | {r['間取り']} | {r['家賃']}\n")

print(f"💾 result_name_madori.txt に {len(results)} 件保存しました。")



# -----------------------------------------------------
# 出力
# -----------------------------------------------------
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"🏠 実行時刻: {now}")


# -----------------------------------------------------
# Discord通知
# -----------------------------------------------------
import os
import requests

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
try:
    with open("result_name_madori.txt", "r", encoding="utf-8") as f:
        content = f.read()

    max_len = 1900
    chunks = [content[i:i+max_len] for i in range(0, len(content), max_len)]

    for chunk in chunks:
        data = {
            "content": f"📢 **空室情報更新**\n```{chunk}```",
            "username": "jkkchecker"
        }
        requests.post(DISCORD_WEBHOOK_URL, json=data)

    print("✅ Discord通知を送信しました。")

except Exception as e:
    print("⚠️ Discord通知に失敗しました:", e)
