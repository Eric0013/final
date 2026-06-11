from flask import Flask, request, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)

# 單一檔案網頁範本 (上下結構，確保圖表100%顯示，鎖定近10日K線)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 股神助手 + 10日K線圖</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        body { background: linear-gradient(135deg, #1e1e2f, #2d1b4e); color: #f4f4f7; min-height: 100vh; }
        .card { background-color: #252538; border: none; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); color: #f4f4f7; }
        .result-box { background: #1e1e2f; border-radius: 12px; padding: 25px; border: 1px solid #3d3d5c; font-size: 1.15rem; line-height: 1.8; }
        #chart { background: #1e1e2f; border-radius: 12px; padding: 15px; border: 1px solid #3d3d5c; min-height: 380px; }
        .form-control { background-color: #151522; border: 1px solid #3d3d5c; color: #fff; }
        .form-control:focus { background-color: #151522; color: #fff; border-color: #667eea; box-shadow: none; }
        hr { border-color: #3d3d5c; }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="text-center mb-5">
            <h1 class="text-white display-4 fw-bold">📈 AI 股神助手</h1>
            <p class="text-muted lead">名師策略審查與動態 10日 K 線技術圖表</p>
        </div>

        <div class="row justify-content-center">
            <div class="col-md-9 col-lg-8">
                
                <div class="card p-4 mb-4">
                    <form id="stockForm">
                        <div class="input-group input-group-lg">
                            <input type="text" class="form-control" id="symbol" placeholder="例如：2330.TW、NVDA、AAPL" required>
                            <button class="btn btn-primary px-5" type="submit" style="background: linear-gradient(to right, #667eea, #764ba2); border: none;">開始分析</button>
                        </div>
                    </form>
                </div>

                <div id="outputSection" style="display: none;">
                    
                    <div class="card p-4 mb-4">
                        <h5 class="mb-3 text-info">📊 歷史技術 K 線圖 (最近10個交易日)</h5>
                        <div id="chart"></div>
                    </div>
                    
                    <div class="card p-4">
                        <h5 class="mb-3 text-warning">📋 策略分析報告</h5>
                        <div id="result" class="result-box"></div>
                    </div>

                </div>

            </div>
        </div>
    </div>

    <script>
        let chartInstance = null;

        document.getElementById('stockForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const symbol = document.getElementById('symbol').value.trim();
            const outputSection = document.getElementById('outputSection');
            const resultDiv = document.getElementById('result');
            const chartDiv = document.getElementById('chart');
            
            outputSection.style.display = 'block';
            resultDiv.innerHTML = '<p class="text-center text-muted">🔄 正在計算技術指標與大師策略...</p>';
            chartDiv.innerHTML = '<p class="text-center text-muted">🔄 正在載入近10日K線數據...</p>';

            try {
                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `symbol=${encodeURIComponent(symbol)}`
                });
                
                const data = await res.json();
                
                if (data.error) {
                    resultDiv.innerHTML = `<h4 class="text-danger">錯誤</h4><p>${data.error}</p>`;
                    chartDiv.innerHTML = '<p class="text-center text-danger">無法載入圖表</p>';
                    return;
                }

                // 1. 渲染文字報告
                resultDiv.innerHTML = data.report;

                // 2. 重組 K 線價格數據
                const candlestickData = data.k_data.map(item => {
                    const parts = item.date.split('-');
                    const timestamp = Date.UTC(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
                    return {
                        x: timestamp,
                        y: [item.open, item.high, item.low, item.close]
                    };
                });

                // 3. 重組 EMA20 均線數據
                const emaData = data.k_data.map(item => {
                    const parts = item.date.split('-');
                    const timestamp = Date.UTC(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
                    return {
                        x: timestamp,
                        y: item.ema20
                    };
                });

                // 4. 配置混合圖表 (K線 + EMA均線)
                const options = {
                    series: [
                        {
                            name: 'K線價',
                            type: 'candlestick',
                            data: candlestickData
                        },
                        {
                            name: 'EMA(20)趨勢線',
                            type: 'line',
                            data: emaData
                        }
                    ],
                    chart: {
                        type: 'line',
                        height: 380,
                        background: '#1e1e2f',
                        foreColor: '#cccccc',
                        toolbar: { show: true }
                    },
                    xaxis: { 
                        type: 'datetime',
                        labels: { datetimeUTC: true }
                    },
                    yaxis: { 
                        decimalsInFloat: 2
                    },
                    stroke: {
                        width: [1, 2.5] // K線框粗細, EMA線粗細
                    },
                    colors: ['#ef5350', '#ff9800'], // 均線顯示為亮橘色
                    plotOptions: {
                        candlestick: {
                            colors: {
                                upward: '#ef5350',  // 漲紅
                                downward: '#26a69a' // 跌綠
                            }
                        }
                    }
                };

                if (chartInstance) {
                    chartInstance.destroy();
                }
                chartDiv.innerHTML = '';
                chartInstance = new ApexCharts(chartDiv, options);
                chartInstance.render();

            } catch (err) {
                resultDiv.innerHTML = `<p class="text-danger">連線失敗: ${err}</p>`;
                chartDiv.innerHTML = '<p class="text-center text-danger">圖表組件載入異常</p>';
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
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        df = yf.download(symbol, period="2y", auto_adjust=True, progress=False, session=session)
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty or len(df) < 200:
            return None, f"❌ 找不到股票代碼 {symbol} 或資料不足 (需至少200個交易日)"

        # 技術指標計算
        df['RSI'] = calculate_rsi(df['Close'], period=14)
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df.dropna(inplace=True)

        # 【精準切換】：僅擷取最新「10天」的資料傳回前端，防止畫面擁擠
        k_df = df.tail(10).copy()
        k_data_list = []
        for index, row in k_df.iterrows():
            k_data_list.append({
                'date': index.strftime('%Y-%m-%d'),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2),
                'ema20': round(float(row['EMA_20']), 2)
            })

        # 純數學線性趨勢預測
        close_prices = df['Close'].tail(20).values
        x = np.arange(len(close_prices))
        y = close_prices
        slope, intercept = np.polyfit(x, y, 1)
        pred_price = slope * 20 + intercept

        current_price = df['Close'].iloc[-1]
        change_pct = ((pred_price - current_price) / current_price) * 100

        # 大師判斷邏輯
        buffett = current_price < df['SMA_200'].iloc[-1] * 1.15
        livermore = (current_price > df['EMA_20'].iloc[-1]) and (change_pct > 0)
        lynch = 50 < df['RSI'].iloc[-1] < 75
        wood = change_pct > 3.0
        simons = change_pct > 0.5

        # 產生報告 HTML 內容
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
            ("🚀 凱薩琳 * 伍德", "具爆發力", "成長緩慢", wood),
            ("💻 詹姆斯 * 西蒙斯", "數據勝率高", "數據勝率低", simons),
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

        return k_data_list, report

    except Exception as e:
        return None, f"❌ 分析過程中發生錯誤: {str(e)}"

# ==================== 網站路由 ====================

@app.route('/')
def home():
    return HTML_TEMPLATE

@app.route('/analyze', methods=['POST'])
def analyze():
    symbol = request.form.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': '請輸入股票代碼'})
    
    k_data, report = get_stock_analysis_report(symbol)
    if k_data is None:
        return jsonify({'error': report})
        
    return jsonify({'report': report, 'symbol': symbol, 'k_data': k_data})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
