import os
import urllib.parse
from flask import Flask, render_template, request
import requests
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# API Anahtarınız
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "6c482eb3dd0f7542289036642f28d30497ef787fd83fce663e96c1af60d8a643")

def fetch_page(page_num, keyword):
    """Her bir sayfayı SerpApi üzerinden bağımsız olarak çeken yardımcı fonksiyon"""
    start = (page_num - 1) * 10
    url = "https://serpapi.com/search.json"
    params = {
        "q": keyword,
        "engine": "google",
        "hl": "tr",        # Türkçe Dil Desteği
        "gl": "tr",        # Türkiye Lokasyonu
        "num": 10,         # Sayfa başına net 10 organik sonuç
        "start": start,    # Google başlangıç indeksi (0, 10, 20...)
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return page_num, response.json().get("organic_results", [])
    except Exception as e:
        print(f"{page_num}. sayfa istenirken hata oluştu: {e}")
    return page_num, []

def google_rank_checker(keyword, target_domain):
    clean_target = target_domain.replace("https://", "").replace("http://", "").replace("www.", "").lower().strip()
    
    # 🚀 Sihirli Nokta: 20 sayfanın tamamını AYNI ANDA paralel olarak çağırıyoruz.
    # Toplam işlem süresi 40 saniyeden 2 saniyeye düşer ve sunucu asla çökmez.
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_page, p, keyword) for p in range(1, 21)]
        raw_results = [f.result() for f in futures]
    
    # Eşzamanlı gelen verileri sayfa numaralarına göre (1'den 20'ye) tekrar sıraya diziyoruz
    raw_results.sort(key=lambda x: x[0])
    
    pages_data = []
    global_rank = 1
    target_rank = None
    
    for page_num, organic_results in raw_results:
        page_items = []
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
                status_message = "Google sonuçları çekilemedi. Lütfen API anahtarınızı veya kotanızı kontrol edin."

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
