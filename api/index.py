from flask import Flask, request, jsonify, make_response
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)

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
            <p class="text-white lead">輸入股票代碼，獲得五大名師量化數據分析 <span class="badge bg-success text-white">v2.2 Final</span></p>
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
            const symbol = document.getElementById('symbol').value.trim().toUpperCase();
            const resultDiv = document.getElementById('result');
            
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<p class="text-center">🔄 正在計算技術指標與大師策略，請稍候...</p>';

            try {
                const response = await fetch('/analyze?t=' + new Date().getTime(), {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `symbol=${encodeURIComponent(symbol)}`
                });
                
                const data = await response.json();
                
                if (data.error) {
                    resultDiv.innerHTML = `<h4 class="mb-3 text-danger">分析失敗</h4><p>${data.error}</p>`;
                } else {
                    resultDiv.innerHTML = `<h4 class="mb-3">分析結果 - ${data.symbol}</h4>${data.report}`;
                }
            } catch (err) {
                resultDiv.innerHTML = `<h4 class="mb-3 text-danger">錯誤</h4><p>伺服器連線異常，請確認代碼後重試。</p>`;
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

# ==================== 核心大師分析邏輯 ====================
def get_stock_analysis_report(symbol):
    try:
        df = None
        stock_fullname = symbol
        
        try:
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            df = yf.download(symbol, period="2y", auto_adjust=True, progress=False, session=session, threads=False)
            if df is not None and not df.empty:
                ticker = yf.Ticker(symbol)
                stock_fullname = ticker.info.get('longName', symbol)
        except:
            df = None

        if df is None or df.empty:
            backup_url = f"https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?range=2y&interval=1d"
            r = requests.get(backup_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            result = r.json()['chart']['result'][0]
            timestamps = result['timestamp']
            quotes = result['indicators']['quote'][0]
            adj_close = result['indicators']['adjclose'][0]['adjclose']
            
            try:
                stock_fullname = result['meta'].get('shortName', symbol)
            except:
                stock_fullname = symbol
            
            parsed_data = [{'Date': pd.to_datetime(timestamps[i], unit='s'), 'Open': quotes['open'][i], 'High': quotes['high'][i], 'Low': quotes['low'][i], 'Close': adj_close[i]} for i in range(len(timestamps)) if quotes['open'][i] and adj_close[i]]
            df = pd.DataFrame(parsed_data).set_index('Date')

        if df.empty or len(df) < 200:
            return f"❌ 找不到股票代碼 「{symbol}」 或該股票歷史資料不足。"

        currency = "TWD" if ".TW" in symbol.upper() else "USD"

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
        current_price = float(df['Close'].iloc[-1])
        change_pct = float(((pred_price - current_price) / current_price) * 100)

        # 💡 修正關鍵：強制將最後一筆的均線數值轉為純 float 數值，徹底避免 Series 比較引發的 ambiguous 異常
        last_sma200 = float(df['SMA_200'].iloc[-1])
        last_ema20 = float(df['EMA_20'].iloc[-1])
        last_rsi = float(df['RSI'].iloc[-1])

        # 大師判斷邏輯
        buffett = current_price < last_sma200 * 1.15
        livermore = (current_price > last_ema20) and (change_pct > 0)
        lynch = 50 < last_rsi < 75
        wood = change_pct > 3.0
        simons = change_pct > 0.5

        report = f"""
        📊 <strong>股票名稱：</strong> {stock_fullname} ({symbol})<br>
        💰 <strong>當前價格：</strong> {current_price:.2f} {currency}<br>
        🤖 <strong>AI 趨勢預測下個交易日：</strong> {pred_price:.2f} {currency} 
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
            if result: recommendation += 1

        report += f"<hr><h4>💡 綜合建議：{recommendation}/5 位大師看好</h4>"
        if recommendation >= 4: report += "<h3 style='color:green'>🔥 強力買入指標！</h3>"
        elif recommendation == 3: report += "<h3 style='color:orange'>⚖️ 可以考慮分批進場</h3>"
        else: report += "<h3 style='color:gray'>💤 建議繼續觀望</h3>"

        return report

    except Exception as e:
        return f"❌ 數據庫清洗異常: {str(e)}"

@app.route('/')
def home():
    response = make_response(HTML_TEMPLATE)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route('/analyze', methods=['POST'])
def analyze():
    symbol = request.form.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': '請輸入股票代碼'})
    report = get_stock_analysis_report(symbol)
    
    response = make_response(jsonify({'report': report, 'symbol': symbol}))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
