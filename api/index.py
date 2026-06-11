from flask import Flask, request, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)

# 單一檔案網頁範本 (整合 TradingView 趨勢線 + KD線)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 股神助手 + KD趨勢圖</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #1e1e2f, #2d1b4e); color: #f4f4f7; min-height: 100vh; }
        .card { background-color: #252538; border: none; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); color: #f4f4f7; }
        .result-box { background: #1e1e2f; border-radius: 12px; padding: 25px; border: 1px solid #3d3d5c; font-size: 1.15rem; line-height: 1.8; }
        .chart-container { background: #1e1e2f; border-radius: 12px; padding: 10px; border: 1px solid #3d3d5c; min-height: 500px; position: relative; }
        .form-control { background-color: #151522; border: 1px solid #3d3d5c; color: #fff; }
        .form-control:focus { background-color: #151522; color: #fff; border-color: #667eea; box-shadow: none; }
        hr { border-color: #3d3d5c; }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="text-center mb-5">
            <h1 class="text-white display-4 fw-bold">📈 AI 股神助手</h1>
            <p class="text-muted lead">五大名師策略審查與 TradingView 頂級動態 K 線圖表</p>
        </div>

        <div class="row justify-content-center">
            <div class="col-md-10">
                
                <div class="card p-4 mb-4">
                    <form id="stockForm">
                        <div class="input-group input-group-lg">
                            <input type="text" class="form-control" id="symbol" placeholder="例如：2330 或 NVDA (台股免加.TW)" required>
                            <button class="btn btn-primary px-5" type="submit" style="background: linear-gradient(to right, #667eea, #764ba2); border: none;">開始分析</button>
                        </div>
                    </form>
                </div>

                <div id="outputSection" style="display: none;">
                    
                    <div class="card p-4 mb-4">
                        <h5 class="mb-3 text-info">📊 技術趨勢圖 (內建 EMA 趨勢線 與 KD 指標線)</h5>
                        <div class="chart-container">
                            <div id="tradingview_chart" style="height: 480px;"></div>
                        </div>
                    </div>
                    
                    <div class="card p-4">
                        <h5 class="mb-3 text-warning">📋 策略分析報告</h5>
                        <div id="result" class="result-box"></div>
                    </div>

                </div>

            </div>
        </div>
    </div>

    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    
    <script>
        document.getElementById('stockForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            let symbolInput = document.getElementById('symbol').value.trim().toUpperCase();
            const outputSection = document.getElementById('outputSection');
            const resultDiv = document.getElementById('result');
            
            outputSection.style.display = 'block';
            resultDiv.innerHTML = '<p class="text-center text-muted">🔄 正在計算技術指標與大師策略...</p>';

            // 1. 自動校正股票代碼格式以適應 TradingView 官方命名空間
            let tvSymbol = symbolInput;
            if (/^\d+$/.test(symbolInput)) {
                tvSymbol = "TWSE:" + symbolInput; // 純數字自動判斷為台灣加權交易所股票
            }

            // 2. 初始化 TradingView 趨勢圖 + 強制載入 MA (均線) 與 Stochastic (KD線)
            new TradingView.widget({
                "autosize": true,
                "symbol": tvSymbol,
                "interval": "D",
                "timezone": "Asia/Taipei",
                "theme": "dark",
                "style": "1", // 1 代表專業 K 線型態趨勢圖
                "locale": "zh_TW",
                "toolbar_bg": "#1e1e2f",
                "enable_publishing": false,
                "hide_side_toolbar": true,
                "allow_symbol_change": false,
                "container_id": "tradingview_chart",
                "studies": [
                    "MASimple@tv-basicstudies",      // 在圖表主體疊加一條移動平均趨勢線
                    "Stochastic@tv-basicstudies"     // 在圖表下方獨立新增 K/D 指標線區塊
                ]
            });

            // 3. 向後端發送請求獲取文字報告
            try {
                let backendSymbol = symbolInput;
                if (/^\d+$/.test(symbolInput)) {
                    backendSymbol = symbolInput + ".TW";
                }

                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `symbol=${encodeURIComponent(backendSymbol)}`
                });
                
                const data = await res.json();
                
                if (data.error) {
                    resultDiv.innerHTML = `<p class="text-warning">⚠️ 策略報告提示：${data.error}</p><p class="text-muted fs-6">註：若文字報告更新較慢，請優先參考上方 TradingView 提供的即時動態 K 棒、均線與下方 KD 線進行判斷！</p>`;
                    return;
                }

                resultDiv.innerHTML = data.report;

            } catch (err) {
                resultDiv.innerHTML = `<p class="text-danger">報告載入失敗，請參考上方即時圖表。</p>`;
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

def get_stock_analysis_report(symbol):
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        })

        df = yf.download(symbol, period="2y", auto_adjust=True, progress=False, session=session, threads=False)
        
        if df is None or df.empty or len(df) < 200:
            return f"暫時無法連線至 Yahoo 財經獲取文字量化數據。請參考上方 K 線與 KD 圖進行自主研判。"

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['RSI'] = calculate_rsi(df['Close'], period=14)
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df.dropna(inplace=True)

        close_prices = df['Close'].tail(20).values
        x = np.arange(len(close_prices))
        y = close_prices
        slope, intercept = np.polyfit(x, y, 1)
        pred_price = slope * 20 + intercept

        current_price = df['Close'].iloc[-1]
        change_pct = ((pred_price - current_price) / current_price) * 100

        buffett = current_price < df['SMA_200'].iloc[-1] * 1.15
        livermore = (current_price > df['EMA_20'].iloc[-1]) and (change_pct > 0)
        lynch = 50 < df['RSI'].iloc[-1] < 75
        wood = change_pct > 3.0
        simons = change_pct > 0.5

        report = f"""
        📊 <strong>股票代碼：</strong> {symbol}<br>
        💰 <strong>當前價格：</strong> {current_price:.2f}<br>
        🤖 <strong>AI 趨勢預測下個交易日：</strong> {pred_price:.2f} 
        <span style="color:{'#ef5350' if change_pct > 0 else '#26a69a'}">({change_pct:+.2f}%)</span>
        <hr>
        <h4>五大名師看法：</h4>
        """

        masters = [
            ("👴 巴菲特", "價格合理", "價格太貴", buffett),
            ("🎩 李佛摩", "趨勢向上", "趨勢不明", livermore),
            ("👓 彼得・林區", "動能強勁", "進入整理", lynch),
            ("🚀 凱薩琳 ・ 伍德", "具爆發力", "成長緩慢", wood),
            ("💻 詹姆斯 ・ 西蒙斯", "數據勝率高", "數據勝率低", simons),
        ]

        recommendation = 0
        for name, good, bad, result in masters:
            status = f"✅ {good}" if result else f"❌ {bad}"
            color = "#ef5350" if result else "#26a69a"
            report += f"<p><strong>{name}：</strong> <span style='color:{color}'>{status}</span></p>"
            if result: recommendation += 1

        report += f"<hr><h4>💡 綜合建議：{recommendation}/5 位大師看好</h4>"
        if recommendation >= 4: report += "<h3 style='color:#ef5350'>🔥 強力買入指標！</h3>"
        elif recommendation == 3: report += "<h3 style='color:orange'>⚖️ 可以考慮分批進場</h3>"
        else: report += "<h3 style='color:gray'>💤 建議繼續觀望</h3>"

        return report

    except Exception as e:
        return f"數據庫繁忙中，請優先查看上方即時動態趨勢圖表。"

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
