import random
import time
import urllib.parse
from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def get_random_headers():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com.tr/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

def google_rank_checker(keyword, target_domain, max_results=200):
    results = []
    # Her sayfada 10 sonuç, toplam 20 sayfa (0, 10, 20, 30... 190)
    pages = [i * 10 for i in range(20)]
    rank = 1

    clean_target = target_domain.replace("https://", "").replace("http://", "").replace("www.", "").lower().strip()
    target_rank = None
    session = requests.Session()

    for start in pages:
        # num=10 ile tam olarak sayfa başı 10 sonuç istiyoruz
        url = f"https://www.google.com/search?q={urllib.parse.quote(keyword)}&num=10&start={start}&hl=tr&gl=tr"
        
        try:
            response = session.get(url, headers=get_random_headers(), timeout=15)
            print(f"[Google Sorgusu] Sayfa: {int(start/10) + 1}/20 (Start: {start}) | HTTP Kodu: {response.status_code}")

            if response.status_code == 429:
                print("UYARI: Google bot korumasına (Too Many Requests) takıldı! Kalan sayfalar atlanıyor.")
                break
            elif response.status_code != 200:
                print(f"Beklenmeyen bir hata oluştu. Durum kodu: {response.status_code}")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            search_divs = soup.find_all("div", class_="g")

            if not search_divs:
                # Alternatif div sınıfları (Google yapısı değiştiğinde çalışması için)
                search_divs = soup.select("div.Mjs7Ob, div.tF2Cxc")

            if not search_divs:
                print(f"{int(start/10) + 1}. sayfada sonuç bulunamadı veya arama limitine ulaşıldı.")
                break

            for div in search_divs:
                link_tag = div.find("a")
                title_tag = div.find("h3")

                if link_tag and title_tag and link_tag.get("href"):
                    href = link_tag.get("href")
                    title = title_tag.get_text()

                    # Google'ın iç linklerini veya haritaları filtrele
                    if href.startswith("http") and "google.com" not in href:
                        is_target = clean_target in href.lower()

                        if is_target and target_rank is None:
                            target_rank = rank

                        results.append({
                            "rank": rank,
                            "title": title,
                            "url": href,
                            "is_target": is_target
                        })
                        rank += 1

                        if len(results) >= max_results:
                            return results, target_rank

            # Google'ı engellememek için 2 istek arası ZORUNLU BEKLEME SÜRESİ (20 istek yapılacağı için çok kritik)
            if start != pages[-1]:
                delay = random.uniform(3.0, 5.5)
                print(f"Sonraki sayfa için {delay:.1f} saniye bekleniyor...")
                time.sleep(delay)

        except Exception as e:
            print(f"Bağlantı Hatası: {e}")
            break

    return results, target_rank

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    target_rank = None
    searched = False
    domain = ""
    keyword = ""
    status_message = ""

    if request.method == "POST":
        domain = request.form.get("domain", "").strip()
        keyword = request.form.get("keyword", "").strip()
        searched = True

        if domain and keyword:
            results, target_rank = google_rank_checker(keyword, domain, 200)
            
            if not results:
                status_message = "Hiç sonuç alınamadı. Google tarafından IP'niz geçici olarak engellenmiş olabilir (429 Hatası). Lütfen modeminizi kapatıp açarak IP değiştirin."
            elif len(results) < 200:
                status_message = f"Sadece {len(results)} sonuç bulunabildi. (Google bot korumasına takılmış veya arama bittiği için işlem yarıda kesilmiş olabilir.)"

    return render_template(
        "index.html",
        results=results,
        target_rank=target_rank,
        searched=searched,
        domain=domain,
        keyword=keyword,
        status_message=status_message
    )

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)