from flask import Flask, request, jsonify, make_response
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)

# 完美保留最純粹的紫色漸層，兼顧圖表與文字報告
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 股神助手</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        body { background: linear-gradient(135deg, #667eea, #764ba2); min-height: 100vh; color: #fff; }
        .card { border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(5px); border: 1px solid rgba(255,255,255,0.2); }
        .result-card { background: white; border-radius: 15px; padding: 25px; color: #333; box-shadow: 0 10px 30px rgba(0,0,0,0.15); }
        #chart { background: #1e1e2f; border-radius: 12px; padding: 15px; border: 1px solid #3d3d5c; min-height: 420px; }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="text-center mb-5">
            <h1 class="text-white display-4 fw-bold">📈 AI 股神助手</h1>
            <p class="text-white lead">動態 10日 K線/KD 技術圖表 ＆ 五大名師量化分析 <span class="badge bg-success">v3.5 Ultimate</span></p>
        </div>

        <div class="row justify-content-center">
            <div class="col-md-9 col-lg-8">
                
                <div class="card p-4 mb-4">
                    <div class="card-body">
                        <form id="stockForm">
                            <div class="input-group">
                                <input type="text" class="form-control form-control-lg" 
                                       id="symbol" placeholder="例如：2330.TW 或 NVDA" required>
                                <button class="btn btn-primary btn-lg" type="submit">開始分析</button>
                            </div>
                        </form>
                    </div>
                </div>

                <div id="outputSection" style="display: none;">
                    <div class="card p-4 mb-4">
                        <h5 class="mb-3 text-white">📊 技術趨勢圖 (最近10個交易日 K線 + EMA均線 + KD線)</h5>
                        <div id="chart"></div>
                    </div>
                    
                    <div class="result-card p-4 mb-4">
                        <h5 class="mb-3 fw-bold text-dark">📋 策略分析報告</h5>
                        <div id="result"></div>
                    </div>
                </div>

            </div>
        </div>
    </div>

    <script>
        let chartInstance = null;

        document.getElementById('stockForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const symbol = document.getElementById('symbol').value.trim().toUpperCase();
            const outputSection = document.getElementById('outputSection');
            const resultDiv = document.getElementById('result');
            const chartDiv = document.getElementById('chart');
            
            outputSection.style.display = 'block';
            resultDiv.innerHTML = '<p class="text-center text-secondary">🔄 正在計算技術指標與大師策略，請稍候...</p>';
            chartDiv.innerHTML = '<p class="text-center text-white">🔄 正在載入近10日K線與KD數據...</p>';

            try {
                // 1. 一律由後端 Python 發送中繼請求，100% 避開瀏覽器 CORS 跨網域阻擋
                const response = await fetch('/analyze?t=' + new Date().getTime(), {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `symbol=${encodeURIComponent(symbol)}`
                });
                
                const data = await response.json();
                
                if (data.error) {
                    resultDiv.innerHTML = `<h4 class="mb-3 text-danger">分析失敗</h4><p>${data.error}</p>`;
                    chartDiv.innerHTML = '<p class="text-center text-danger">⚠️ 圖表數據因後端異常無法呈現</p>';
                    return;
                }

                // 2. 渲染下方大師文字報告
                resultDiv.innerHTML = data.report;

                // 3. 處理後端傳回的 10 日繪圖數據
                const candlestickData = data.k_data.map(item => ({
                    x: item.time,
                    y: [item.open, item.high, item.low, item.close]
                }));

                const emaGraphData = data.k_data.map(item => ({ x: item.time, y: item.ema20 }));
                const kGraphData = data.k_data.map(item => ({ x: item.time, y: item.k }));
                const dGraphData = data.k_data.map(item => ({ x: item.time, y: item.d }));

                // 4. 渲染 ApexCharts
                const options = {
                    series: [
                        { name: 'K線價', type: 'candlestick', data: candlestickData },
                        { name: 'EMA20均線', type: 'line', data: emaGraphData },
                        { name: 'K線 (KD)', type: 'line', data: kGraphData },
                        { name: 'D線 (KD)', type: 'line', data: dGraphData }
                    ],
                    chart: { type: 'line', height: 420, background: '#1e1e2f', foreColor: '#cccccc', toolbar: { show: true } },
                    xaxis: { type: 'datetime', labels: { datetimeUTC: true } },
                    yaxis: [
                        { seriesName: 'K線價', decimalsInFloat: 2, title: { text: "價格軸" } },
                        { seriesName: 'K線價', show: false },
                        { seriesName: 'K線 (KD)', max: 100, min: 0, opposite: true, title: { text: "KD指標軸 (0-100)" } },
                        { seriesName: 'K線 (KD)', max: 100, min: 0, show: false }
                    ],
                    stroke: { width: [1, 2.5, 2, 2], dashArray: [0, 0, 0, 4] },
                    colors: ['#ef5350', '#ff9800', '#00b0ff', '#ffea00'],
                    plotOptions: { candlestick: { colors: { upward: '#ef5350', downward: '#26a69a' } } }
                };

                if (chartInstance) { chartInstance.destroy(); }
                chartDiv.innerHTML = '';
                chartInstance = new ApexCharts(chartDiv, options);
                chartInstance.render();

            } catch (err) {
                resultDiv.innerHTML = `<h4 class="mb-3 text-danger">錯誤</h4><p>網絡連線異常，請重試。</p>`;
                chartDiv.innerHTML = '<p class="text-center text-danger">⚠️ 圖表組件載入異常</p>';
            }
        });
    </script>
</body>
</html>
'''

# 後端 Python 計算 KD 線公式
def calculate_backend_kd(df_close, df_high, df_low, period=9):
    k_vals = [50.0]
    d_vals = [50.0]
    
    for i in range(len(df_close)):
        if i < period - 1:
            if i > 0:
                k_vals.append(50.0)
                d_vals.append(50.0)
            continue
            
        sub_high = df_high.iloc[i - period + 1 : i + 1]
        sub_low = df_low.iloc[i - period + 1 : i + 1]
        max_h = float(sub_high.max())
        min_l = float(sub_low.min())
        
        current_close = float(df_close.iloc[i])
        rsv = 50.0 if max_h == min_l else ((current_close - min_l) / (max_h - min_l)) * 100.0
        
        next_k = (2.0/3.0) * k_vals[-1] + (1.0/3.0) * rsv
        next_d = (2.0/3.0) * d_vals[-1] + (1.0/3.0) * next_k
        k_vals.append(next_k)
        d_vals.append(next_d)
        
    return k_vals, d_vals

# ==================== 核心量化核心邏輯 ====================
def get_stock_analysis_data(symbol):
    try:
        # 100% 走不鎖海外雲端 IP、不需要 Session 憑證的免簽官方直接 API
        api_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(api_url, headers=headers, timeout=10)
        y_data = r.json()
        
        result = y_data['chart']['result'][0]
        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]
        adj_close = result['indicators']['adjclose'][0]['adjclose']
        
        stock_fullname = result['meta'].get('shortName', symbol)
        currency = "TWD" if ".TW" in symbol.upper() else "USD"

        # 解析並轉換
        parsed_data = []
        for i in range(len(timestamps)):
            if quotes['open'][i] is not None and adj_close[i] is not None:
                parsed_data.append({
                    'time': int(timestamps[i] * 1000),
                    'Open': float(quotes['open'][i]),
                    'High': float(quotes['high'][i]),
                    'Low': float(quotes['low'][i]),
                    'Close': float(adj_close[i])
                })
        
        df = pd.DataFrame(parsed_data)
        if df.empty or len(df) < 200:
            return None, f"❌ 找不到股票代碼 「{symbol}」 或該股票歷史資料不足。"

        # 指標運算
        delta = df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        df['RSI'] = 100.0 - (100.0 / (1.0 + (avg_gain / (avg_loss + 1e-9))))
        
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        # 計算 KD 線
        k_list, d_list = calculate_backend_kd(df['Close'], df['High'], df['Low'], 9)
        df['K'] = k_list
        df['D'] = d_list
        df.dropna(inplace=True)

        # 線性預測
        tail_20 = df['Close'].tail(20).values
        slope, intercept = np.polyfit(np.arange(20), tail_20, 1)
        pred_raw = slope * 20 + intercept
        pred_price = float(pred_raw.item()) if hasattr(pred_raw, 'item') else float(pred_raw)
        
        current_price = float(df['Close'].iloc[-1])
        change_pct = float(((pred_price - current_price) / current_price) * 100.0)

        # 大師判斷
        buffett = current_price < float(df['SMA_200'].iloc[-1]) * 1.15
        livermore = (current_price > float(df['EMA_20'].iloc[-1])) and (change_pct > 0.0)
        lynch = 50.0 < float(df['RSI'].iloc[-1]) < 75.0
        wood = change_pct > 3.0
        simons = change_pct > 0.5

        # 組合純文字 HTML 報告
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

        # 打包最新 10 天數據供前台繪圖
        chart_df = df.tail(10)
        k_data_list = []
        for _, row in chart_df.iterrows():
            k_data_list.append({
                'time': int(row['time']),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'ema20': float(row['EMA_20']),
                'k': float(row['K']),
                'd': float(row['D'])
            })

        return {'report': report, 'k_data': k_data_list}, None

    except Exception as e:
        return None, f"❌ 數據庫清洗異常: {str(e)}"

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
        
    data, error = get_stock_analysis_data(symbol)
    if error:
        return jsonify({'error': error})
        
    response = make_response(jsonify({'report': data['report'], 'symbol': symbol, 'k_data': data['k_data']}))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
