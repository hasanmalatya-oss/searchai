import os
import urllib.parse
from flask import Flask, render_template, request
import requests
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# API Anahtarınız (Render Environment'tan veya direkt buradan okunur)
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "6c482eb3dd0f7542289036642f28d30497ef787fd83fce663e96c1af60d8a643")

def fetch_page(page_num, keyword):
    """Her sayfayı SerpApi üzerinden bağımsız ve güvenli şekilde çeker"""
    start = (page_num - 1) * 10
    url = "https://serpapi.com/search.json"
    params = {
        "q": keyword,
        "engine": "google",
        "hl": "tr",
        "gl": "tr",
        "num": 10,
        "start": start,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            organic = data.get("organic_results")
            # Eğer gelen veri liste değilse (None veya Hata mesajı ise) boş liste döndür
            if isinstance(organic, list):
                return page_num, organic
            else:
                print(f"[Log] Sayfa {page_num}: Organik sonuç listesi alınamadı.")
        else:
            print(f"[Log] Sayfa {page_num} API Hatası: Durum Kodu {response.status_code}")
    except Exception as e:
        print(f"[Log] Sayfa {page_num} Bağlantı Hatası: {e}")
    return page_num, []

def google_rank_checker(keyword, target_domain):
    clean_target = target_domain.replace("https://", "").replace("http://", "").replace("www.", "").lower().strip()
    
    # 20 sayfaya aynı anda paralel istek atılıyor (Zaman aşımını önler)
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_page, p, keyword) for p in range(1, 21)]
        raw_results = [f.result() for f in futures]
    
    # Sayfaları 1'den 20'ye doğru sırala
    raw_results.sort(key=lambda x: x[0])
    
    pages_data = []
    global_rank = 1
    target_rank = None
    
    for page_num, organic_results in raw_results:
        page_items = []
        
        # Çökme Koruması: organic_results mutlaka geçerli bir liste olmalı
        if isinstance(organic_results, list):
            for item in organic_results:
                if not isinstance(item, dict):
                    continue
                title = item.get("title", "Başlıksız Sonuç")
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

        try:
            if domain and keyword:
                results, target_rank = google_rank_checker(keyword, domain)
                if not results:
                    status_message = "Google sonuçları çekilemedi. API kotanızı veya anahtarınızı kontrol edin."
        except Exception as e:
            # 🚀 EN KRİTİK KORUMA: Kod hata alsa bile site çökmez, hatayı ekrana yazar.
            status_message = f"Sorgu sırasında teknik bir hata oluştu: {str(e)}"

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
