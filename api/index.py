from flask import Flask, request, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)

# 100% 恢復一開始最原始、美麗的紫色漸層純文字畫面
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
        .result { background: white; border-radius: 12px; padding: 20px; color: #333; }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="text-center mb-5">
            <h1 class="text-white display-4">📈 AI 股神助手</h1>
            <p class="text-white lead">輸入股票代碼，獲得五大名師量化數據分析</p>
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

            try {
                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `symbol=${encodeURIComponent(symbol)}`
                });
                
                const data = await res.json();
                
                if (data.error) {
                    resultDiv.innerHTML = `<h4 class="mb-3 text-danger">分析失敗</h4><p>${data.error}</p>`;
                } else {
                    resultDiv.innerHTML = `<h4 class="mb-3">分析結果 - ${data.symbol}</h4>${data.report}`;
                }
            } catch (err) {
                resultDiv.innerHTML = `<h4 class="mb-3 text-danger">錯誤</h4><p>伺服器回應異常，請確認代碼是否輸入正確。</p>`;
            }
        });
    </script>
</body>
</html>
'''

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))

# ==================== 核心大師分析邏輯 (智慧雙載防堵 IP 機制) ====================
def get_stock_analysis_report(symbol):
    try:
        df = None
        
        # 軌道 1：使用偽裝 Session 機制嘗試經由 yfinance 下載
        try:
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            df = yf.download(symbol, period="2y", auto_adjust=True, progress=False, session=session, threads=False)
        except:
            df = None

        # 軌道 2：如果 Vercel 的 IP 真的被 Yahoo 擋死導致 df 空白，立刻切換至備用直連網址解鎖數據
        if df is None or df.empty:
            backup_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            r = requests.get(backup_url, headers=headers, timeout=10)
            y_data = r.json()
            
            result = y_data['chart']['result'][0]
            timestamps = result['timestamp']
            quotes = result['indicators']['quote'][0]
            adj_close = result['indicators']['adjclose'][0]['adjclose']
            
            # 重組為符合 pandas 的結構
            parsed_data = []
            for i in range(len(timestamps)):
                if quotes['open'][i] and adj_close[i]:
                    parsed_data.append({
                        'Date': pd.to_datetime(timestamps[i], unit='s'),
                        'Open': quotes['open'][i],
                        'High': quotes['high'][i],
                        'Low': quotes['low'][i],
                        'Close': adj_close[i]
                    })
            df = pd.DataFrame(parsed_data).set_index('Date')

        if df.empty or len(df) < 200:
            return f"❌ 找不到股票代碼 「{symbol}」 或該股票歷史資料不足。"

        # 計算原始指標
        df['RSI'] = calculate_rsi(df['Close'], period=14)
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df.dropna(inplace=True)

        # 線性預測公式
        close_prices = df['Close'].tail(20).values
        x = np.arange(len(close_prices))
        slope, intercept = np.polyfit(x, close_prices, 1)
        pred_price = slope * 20 + intercept

        current_price = df['Close'].iloc[-1]
        change_pct = ((pred_price - current_price) / current_price) * 100

        # 大師判斷邏輯
        buffett = current_price < df['SMA_200'].iloc[-1] * 1.15
        livermore = (current_price > df['EMA_20'].iloc[-1]) and (change_pct > 0)
        lynch = 50 < df['RSI'].iloc[-1] < 75
        wood = change_pct > 3.0
        simons = change_pct > 0.5

        # 完全還原當初一模一樣的文字報告 HTML 格式
        report = f"""
        📊 <strong>股票代碼：</strong> {symbol}<br>
        💰 <strong>當前價格：</strong> {current_price:.2f} USD<br>
        🤖 <strong>AI 趨勢預測下個交易日：</strong> {pred_price:.2f} 
        <span style="color:{'green' if change_pct > 0 else 'red'}">({change_pct:+.2f}%)</span>
        <hr>
        <h4>五大名師看法：</h4>
        """

        masters = [
            ("👴 巴菲特", "價格合理", "價格太貴", buffett),
            ("🎩 李佛摩", "趨勢向上", "趨勢不明", livermore),
            ("👓 彼得・林區", "動能強勁", "進入整理", lynch),
            ("🚀 凱薩琳・伍德", "具爆發力", "成長緩慢", wood),
            ("💻 詹姆斯 * 西蒙斯", "數據勝率高", "數據勝率低", simons),
        ]

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
        return f"❌ 數據庫清洗異常: {str(e)}"

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
