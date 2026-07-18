import os
import urllib.parse
from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# SerpApi Anahtarınız
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "6c482eb3dd0f7542289036642f28d30497ef787fd83fce663e96c1af60d8a643")

def google_rank_checker(keyword, target_domain):
    pages_data = []  # Sayfa sayfa gruplanmış verileri tutacak
    global_rank = 1
    clean_target = target_domain.replace("https://", "").replace("http://", "").replace("www.", "").lower().strip()
    target_rank = None

    if not SERPAPI_KEY:
        return [], None

    # Tam olarak 1. sayfadan 20. sayfaya kadar tek tek döngü kuruyoruz
    for page_num in range(1, 21):
        start = (page_num - 1) * 10
        url = "https://serpapi.com/search.json"
        params = {
            "q": keyword,
            "engine": "google",
            "hl": "tr",        # Türkçe dil seçeneği
            "gl": "tr",        # Türkiye lokasyonu
            "num": 10,         # Her sayfada kesinlikle 10 arama sonucu
            "start": start,    # Sayfa başlangıç indeksi (0, 10, 20... 190)
            "api_key": SERPAPI_KEY
        }

        page_items = []
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                organic_results = data.get("organic_results", [])

                for item in organic_results:
                    title = item.get("title", "")
                    href = item.get("link", "")
                    
                    if href:
                        is_target = clean_target in href.lower()

                        if is_target and target_rank is None:
                            target_rank = global_rank

                        page_items.append({
                            "global_rank": global_rank,
                            "title": title,
                            "url": href,
                            "is_target": is_target
                        })
                        global_rank += 1
            else:
                print(f"{page_num}. Sayfa Çekilemedi. HTTP Kodu: {response.status_code}")
        except Exception as e:
            print(f"{page_num}. Sayfada Bağlantı Hatası: {e}")
        
        # Her sayfanın sonucunu (boş olsa bile) listeye ekliyoruz ki arayüzde sayfa blokları oluşsun
        pages_data.append({
            "page_num": page_num,
            "items": page_items
        })

    return pages_data, target_rank

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
            results, target_rank = google_rank_checker(keyword, domain)
            
            if not results:
                status_message = "Google sonuçları çekilemedi. Lütfen API anahtarınızı kontrol edin."

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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
