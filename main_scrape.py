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
    f.write("-" * 35 + "\n")
    for r in results:
        f.write(f"{r['住宅名']} | {r['市区町村']} | {r['間取り']} | {r['家賃']}\n")

print(f"💾 result_name_madori.txt に {len(results)} 件保存しました。")




# -----------------------------------------------------
# 出力
# -----------------------------------------------------
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"🏠 実行時刻: {now}")

# --- 先頭は既存のスクレイピング処理（省略） ---
# （あなたの既存コードのまま result_name_madori.txt が出力される前提）



DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord_message(content: str):
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ DISCORD_WEBHOOK_URL が設定されていません。")
        return
    data = {"content": f"📢 **空室情報更新**\n```{content}```", "username": "jkkchecker"}
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
        print(f"📤 Discord POST -> status: {r.status_code}")
    except Exception as e:
        print("⚠️ Discord送信で例外:", e)

def read_file_normalized(path: str) -> str:
    """ファイルを読み、行ごとに正規化して返す（比較用）"""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    # 正規化ルール（必要に応じて調整）
    norm_lines = []
    for ln in lines:
        # 全角スペースを半角に、先頭/末尾の空白削除、連続スペースを単一に
        ln2 = ln.replace("\u3000", " ").strip()
        ln2 = re.sub(r"\s+", " ", ln2)
        norm_lines.append(ln2)
    return "\n".join(norm_lines)

def read_full(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# 比較対象
prev_file = "previous_result/result_name_madori.txt"
curr_file = "result_name_madori.txt"

print("🔎 比較処理開始")
print(f"-> 現在ファイル: {curr_file} (exists={os.path.exists(curr_file)})")
print(f"-> 前回ファイル: {prev_file} (exists={os.path.exists(prev_file)})")

if not os.path.exists(curr_file):
    print("❌ 現在の result_name_madori.txt が見つかりません。処理を中止します。")
else:
    # current の 4行目以降（比較用）を正規化して取得
    with open(curr_file, "r", encoding="utf-8") as f:
        curr_lines = f.read().splitlines()
    curr_main = curr_lines[3:] if len(curr_lines) > 3 else []
    # 正規化（行ごと）
    curr_main_norm = [re.sub(r"\s+", " ", ln.replace("\u3000", " ").strip()) for ln in curr_main]

    if not os.path.exists(prev_file):
        print("📁 前回データなし（previous_result が見つかりません）。初回通知を行います。")
        # 通知はファイル全体（1行目から）
        full = read_full(curr_file)
        send_discord_message(full[:1900])
    else:
        # 前回ファイルの 4行目以降を読み、正規化
        with open(prev_file, "r", encoding="utf-8") as f:
            prev_lines = f.read().splitlines()
        prev_main = prev_lines[3:] if len(prev_lines) > 3 else []
        prev_main_norm = [re.sub(r"\s+", " ", ln.replace("\u3000", " ").strip()) for ln in prev_main]

        # 比較（行単位で差分を取得）
        diff = list(difflib.unified_diff(prev_main_norm, curr_main_norm, lineterm=""))
        if not diff:
            print("✅ 前回と同一（正規化後）。Discord通知は行いません。")
        else:
            print("🔔 差分あり。差分の行数:", len(diff))
            # ログにdiffを全部出す（長ければ途中省略されますがGitHub上で見えます）
            print("\n".join(diff))
            # Discordには「ファイル全体」を送信（1行目から）
            full = read_full(curr_file)
            send_discord_message(full[:1900])

# 終了時、デバッグ用に previous_result ディレクトリの中を表示（Workflowログ確認用）
if os.path.isdir("previous_result"):
    print("📂 previous_result の中身:", os.listdir("previous_result"))
else:
    print("📂 previous_result ディレクトリは存在しません。")

#DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
#
#def send_discord_message(content: str):
#    """Discordに通知を送る"""
#    if not DISCORD_WEBHOOK_URL:
#        print("⚠️ DISCORD_WEBHOOK_URL が設定されていません。")
#        return
#    data = {
#        "content": f"📢 **空室情報更新**\n```{content}```",
#        "username": "jkkchecker"
#    }
#    requests.post(DISCORD_WEBHOOK_URL, json=data)

#def get_main_content(file_path: str) -> str:
#    """比較用：4行目以降のみ取得"""
#    with open(file_path, "r", encoding="utf-8") as f:
#        lines = f.read().splitlines()
#    return "\n".join(lines[3:]) if len(lines) > 3 else ""
#
#def get_full_content(file_path: str) -> str:
#    """通知用：ファイル全体を取得"""
#    with open(file_path, "r", encoding="utf-8") as f:
#        return f.read()

# -----------------------------------------------------
# 差分比較と通知
# -----------------------------------------------------
#prev_file = "previous_result/result_name_madori.txt"
#curr_file = "result_name_madori.txt"
#
#if os.path.exists(prev_file):
#    prev_content = get_main_content(prev_file)
#    curr_content = get_main_content(curr_file)
#    if prev_content.strip() != curr_content.strip():
#        print("🔔 内容が更新されています。Discordに通知します。")
#        full = get_full_content(curr_file)
#        send_discord_message(full[:1900])  # Discord制限(2000字弱)
#    else:
#        print("✅ 内容に変更なし。通知しません。")
#else:
#    print("📁 前回データなし。初回として通知します。")
#    full = get_full_content(curr_file)
#    send_discord_message(full[:1900])
#
# -----------------------------------------------------
# Discord通知
# -----------------------------------------------------

#DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
#try:
#    with open("result_name_madori.txt", "r", encoding="utf-8") as f:
#        content = f.read()
#    # ✅ 4行目以降だけログに表示
#    lines = content.splitlines()
#    if len(lines) > 3:
#        print("\n".join(lines[3:]))  # 4行目以降を結合して表示
#    else:
#        print("⚠️ ファイルに4行目以降がありません。")
#
#    max_len = 1900
#    chunks = [content[i:i+max_len] for i in range(0, len(content), max_len)]
#
#    for chunk in chunks:
#        data = {
#            "content": f"📢 **空室情報更新**\n```{chunk}```",
#            "username": "jkkchecker"
#        }
#        requests.post(DISCORD_WEBHOOK_URL, json=data)
#
#    print("✅ Discord通知を送信しました。")
#except Exception as e:
#    print("⚠️ Discord通知に失敗しました:", e)   





