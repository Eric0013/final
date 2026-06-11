from flask import Flask, request, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)

# 單一檔案網頁範本 (HTML / CSS / JavaScript)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 股神助手</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea, #764ba2); min-height: 100vh; }
        .card { border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        .result { background: white; border-radius: 12px; padding: 20px; }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="text-center mb-5">
            <h1 class="text-white display-4">📈 AI 股神助手</h1>
            <p class="text-white lead">輸入股票代碼，獲得五大名師 + 趨勢預測深度分析</p>
        </div>

        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-body">
                        <form id="stockForm">
                            <div class="input-group mb-3">
                                <input type="text" class="form-control form-control-lg" 
                                       id="symbol" placeholder="例如：2330.TW 或 NVDA" required>
                                <button class="btn btn-primary btn-lg" type="submit">開始分析</button>
                            </div>
                        </form>

                        <div id="result" class="result mt-4" style="display:none;"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('stockForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const symbol = document.getElementById('symbol').value.trim();
            const resultDiv = document.getElementById('result');
            
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<p class="text-center">🔄 正在計算技術指標與大師策略，請稍候...</p>';

            const res = await fetch('/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: `symbol=${encodeURIComponent(symbol)}`
            });
            
            const data = await res.json();
            if (data.error) {
                resultDiv.innerHTML = `<h4 class="mb-3 text-danger">錯誤</h4><p>${data.error}</p>`;
            } else {
                resultDiv.innerHTML = `<h4 class="mb-3">分析結果 - ${data.symbol}</h4>${data.report}`;
            }
        });
    </script>
</body>
</html>
'''

# ==================== 純手寫技術指標函數 ====================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    
    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))

# ==================== 股票分析核心函數 ====================
def get_stock_analysis_report(symbol):
    try:
        # 1. 建立自訂的 requests Session，偽裝成一般 Chrome 瀏覽器，防止 Vercel 雲端 IP 被 Yahoo 封鎖
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Origin': 'https://finance.yahoo.com',
            'Referer': 'https://finance.yahoo.com'
        })

        # 使用 session 抓取資料
        df = yf.download(symbol, period="2y", auto_adjust=True, progress=False, session=session)
        
        # 處理 MultiIndex 欄位結構
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty or len(df) < 200:
            return f"❌ 找不到股票代碼 {symbol} 或 Yahoo 財經拒絕連線。請確認代碼（如 NVDA 或 2330.TW）。"

        # 2. 技術指標計算
        df['RSI'] = calculate_rsi(df['Close'], period=14)
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df.dropna(inplace=True)

        if len(df) < 20:
            return "❌ 資料清洗後數量不足，無法進行趨勢分析"

        # 3. 純數學線性趨勢預測
        close_prices = df['Close'].tail(20).values
        x = np.arange(len(close_prices))
        y = close_prices
        slope, intercept = np.polyfit(x, y, 1)
        pred_price = slope * 20 + intercept

        current_price = df['Close'].iloc[-1]
        change_pct = ((pred_price - current_price) / current_price) * 100

        # 4. 大師判斷邏輯
        buffett = current_price < df['SMA_200'].iloc[-1] * 1.15
        livermore = (current_price > df['EMA_20'].iloc[-1]) and (change_pct > 0)
        lynch = 50 < df['RSI'].iloc[-1] < 75
        wood = change_pct > 3.0
        simons = change_pct > 0.5

        # 5. 產生報告 HTML
        report = f"""
        📊 <strong>股票代碼：</strong> {symbol}<br>
        💰 <strong>當前價格：</strong> {current_price:.2f} USD<br>
        🤖 <strong>AI 趨勢預測下個交易日：</strong> {pred_price:.2f} 
        <span style="color:{'green' if change_pct > 0 else 'red'}">({change_pct:+.2f}%)</span>
        """

        masters = [
            ("👴 巴菲特", "價格合理", "價格太貴", buffett),
            ("🎩 李佛摩", "趨勢向上", "趨勢不明", livermore),
            ("👓 彼得・林區", "動能強勁", "進入整理", lynch),
            ("🚀 凱薩琳・伍德", "具爆發力", "成長緩慢", wood),
            ("💻 詹姆斯・西蒙斯", "數據勝率高", "數據勝率低", simons),
        ]

        report += "<hr><h4>五大名師看法：</h4>"
        recommendation = 0
        for name, good, bad, result in masters:
            status = f"✅ {good}" if result else f"❌ {bad}"
            color = "green" if result else "red"
            report += f"<p><strong>{name}：</strong> <span style='color:{color}'>{status}</span></p>"
            if result:
                recommendation += 1

        report += f"<hr><h4>💡 綜合建議：{recommendation}/5 位大師看好</h4>"

        if recommendation >= 4:
            report += "<h3 style='color:green'>🔥 強力買入指標！</h3>"
        elif recommendation == 3:
            report += "<h3 style='color:orange'>⚖️ 可以考慮分批進場</h3>"
        else:
            report += "<h3 style='color:gray'>💤 建議繼續觀望</h3>"

        return report

    except Exception as e:
        return f"❌ 分析過程中發生錯誤: {str(e)}"

# ==================== 網站路由 ====================

@app.route('/')
def home():
    return HTML_TEMPLATE

@app.route('/analyze', methods=['POST'])
def analyze():
    symbol = request.form.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': '請輸入股票代碼'})
    
    report = get_stock_analysis_report(symbol)
    return jsonify({'report': report, 'symbol': symbol})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
