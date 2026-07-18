import urllib.parse
from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# 🔑 BURAYA SERPAPI'DEN ALDIĞINIZ ÜCRETSİZ API ANAHTARINI YAPIŞTIRIN
SERPAPI_KEY = "6c482eb3dd0f7542289036642f28d30497ef787fd83fce663e96c1af60d8a643"

def google_rank_checker(keyword, target_domain, max_results=200):
    results = []
    rank = 1
    clean_target = target_domain.replace("https://", "").replace("http://", "").replace("www.", "").lower().strip()
    target_rank = None

    if not SERPAPI_KEY or SERPAPI_KEY == "BURAYA_API_ANAHTARINIZI_YAZIN":
        return [], None

    pages = [0, 100]

    for start in pages:
        url = "https://serpapi.com/search.json"
        params = {
            "q": keyword,
            "engine": "google",
            "hl": "tr",
            "gl": "tr",
            "num": 100,
            "start": start,
            "api_key": SERPAPI_KEY
        }

        try:
            response = requests.get(url, params=params, timeout=20)
            if response.status_code != 200:
                print(f"SerpApi Hatası: {response.status_code}")
                break

            data = response.json()
            organic_results = data.get("organic_results", [])

            if not organic_results:
                break

            for item in organic_results:
                title = item.get("title", "")
                href = item.get("link", "")
                
                if href:
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

        except Exception as e:
            print(f"API Bağlantı Hatası: {e}")
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

        if not SERPAPI_KEY or SERPAPI_KEY == "6c482eb3dd0f7542289036642f28d30497ef787fd83fce663e96c1af60d8a643":
            status_message = "Lütfen önce app.py içerisindeki SERPAPI_KEY alanına ücretsiz API anahtarınızı ekleyin."
        elif domain and keyword:
            results, target_rank = google_rank_checker(keyword, domain, 200)
            
            if not results:
                status_message = "Google araması gerçekleştirilemedi veya API kotanız bitti."
            elif len(results) < 200:
                status_message = f"Google üzerinde toplam {len(results)} sonuç bulunabildi."

    # Doğru Yerleşim: Bu satır artık 'if' bloğunun dışında, böylece site sorunsuz açılacak.
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
