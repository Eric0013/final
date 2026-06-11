from flask import Flask, request, jsonify, make_response
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)

# 完美整合前端 ApexCharts（繪製近10日K線、均線與KD線）與最原始的紫色漸層
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 股神助手 + 10日KD趨勢圖</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        body { background: linear-gradient(135deg, #667eea, #764ba2); min-height: 100vh; color: #fff; }
        .card { border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(5px); border: 1px solid rgba(255,255,255,0.2); }
        .result { background: white; border-radius: 12px; padding: 20px; color: #333; }
        #chart { background: #1e1e2f; border-radius: 12px; padding: 15px; border: 1px solid #3d3d5c; min-height: 420px; }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="text-center mb-5">
            <h1 class="text-white display-4 fw-bold">📈 AI 股神助手</h1>
            <p class="text-white lead">動態 10日 K線/KD 技術圖表 ＆ 五大名師量化分析 <span class="badge bg-info text-dark">v3.0 Charts Integrated</span></p>
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
                    
                    <div class="card p-4 mb-4" style="background: white; color: #333; border-radius: 15px;">
                        <h5 class="mb-3 fw-bold">📋 策略分析報告</h5>
                        <div id="result" class="result p-0"></div>
                    </div>
                </div>

            </div>
        </div>
    </div>

    <script>
        let chartInstance = null;

        // 純前端免鎖 IP 計算 KD 線公式
        function calculateKD(closeArr, highArr, lowArr, period=9) {
            let kArr = [50];
            let dArr = [50];
            for (let i = 0; i < closeArr.length; i++) {
                if (i < period - 1) {
                    if (i > 0) { kArr.push(50); dArr.push(50); }
                    continue;
                }
                let subHigh = highArr.slice(i - period + 1, i + 1);
                let subLow = lowArr.slice(i - period + 1, i + 1);
                let maxHigh = Math.max(...subHigh);
                let minLow = Math.min(...subLow);
                let rsv = maxHigh === minLow ? 50 : ((closeArr[i] - minLow) / (maxHigh - minLow)) * 100;
                
                let nextK = (2/3) * kArr[kArr.length - 1] + (1/3) * rsv;
                let nextD = (2/3) * dArr[dArr.length - 1] + (1/3) * nextK;
                kArr.push(nextK);
                dArr.push(nextD);
            }
            return { K: kArr, D: dArr };
        }

        document.getElementById('stockForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const symbol = document.getElementById('symbol').value.trim().toUpperCase();
            const outputSection = document.getElementById('outputSection');
            const resultDiv = document.getElementById('result');
            const chartDiv = document.getElementById('chart');
            
            outputSection.style.display = 'block';
            resultDiv.innerHTML = '<p class="text-center">🔄 正在載入歷史交易數據並計算大師策略...</p>';
            chartDiv.innerHTML = '<p class="text-center text-white">🔄 正在繪製近10日 K 線與 KD 圖...</p>';

            try {
                // 1. 前端走使用者台灣 IP 安全直連 Yahoo 官方 API (永不鎖 IP)
                const yahooUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?range=2y&interval=1d`;
                const yResponse = await fetch(yahooUrl);
                const yData = await yResponse.json();
                
                const result = yData.chart.result[0];
                const timestamps = result.timestamp;
                const quotes = result.indicators.quote[0];
                const adjClose = result.indicators.adjclose[0].adjclose;

                // 2. 組裝資料
                let rawData = [];
                for(let i=0; i<timestamps.length; i++) {
                    if (quotes.open[i] && quotes.high[i] && quotes.low[i] && adjClose[i]) {
                        rawData.push({
                            time: timestamps[i] * 1000,
                            open: quotes.open[i],
                            high: quotes.high[i],
                            low: quotes.low[i],
                            close: adjClose[i]
                        });
                    }
                }

                // 3. 計算前台圖表需要疊加的 EMA20 均線與 KD 指標
                let closes = rawData.map(d => d.close);
                let highs = rawData.map(d => d.high);
                let lows = rawData.map(d => d.low);
                
                let ema20 = [];
                let k = 2 / (20 + 1);
                ema20[0] = closes[0];
                for (let i = 1; i < closes.length; i++) {
                    ema20[i] = closes[i] * k + ema20[i-1] * (1 - k);
                }
                let kd = calculateKD(closes, highs, lows, 9);

                // 4. 將抓到的純資料發送給後端 Python 做原本的名師策略邏輯審查 (安全賦值)
                const response = await fetch('/analyze?t=' + new Date().getTime(), {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `symbol=${encodeURIComponent(symbol)}`
                });
                const data = await response.json();
                resultDiv.innerHTML = data.report;

                // 5. 精準擷取最新 10 天數據準備繪圖
                let chartSlice = rawData.slice(-10);
                let emaSlice = ema20.slice(-10);
                let kSlice = kd.K.slice(-10);
                let dSlice = kd.D.slice(-10);

                const candlestickData = chartSlice.map(d => ({ x: d.time, y: [d.open, d.high, d.low, d.close] }));
                const emaGraphData = chartSlice.map((d, idx) => ({ x: d.time, y: emaSlice[idx] }));
                const kGraphData = chartSlice.map((d, idx) => ({ x: d.time, y: kSlice[idx] }));
                const dGraphData = chartSlice.map((d, idx) => ({ x: d.time, y: dSlice[idx] }));

                // 6. 配置與繪製 ApexCharts 圖表 (K線、均線共用主軸，KD單獨使用右側百份比副軸)
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
                    colors: ['#ef5350', '#ff9800', '#00b0ff', '#ffea00'], // 漲紅、均線橘、K線藍、D線黃
                    plotOptions: { candlestick: { colors: { upward: '#ef5350', downward: '#26a69a' } } }
                };

                if (chartInstance) { chartInstance.destroy(); }
                chartDiv.innerHTML = '';
                chartInstance = new ApexCharts(chartDiv, options);
                chartInstance.render();

            } catch (err) {
                resultDiv.innerHTML = `<h4 class="text-danger">❌ 載入失敗</h4><p>無法成功解析數據，請確認代碼（如 2330.TW）是否輸入正確。</p>`;
                chartDiv.innerHTML = '<p class="text-center text-danger">⚠️ 圖表數據渲染異常</p>';
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

# ==================== 後端 Python 核心評估函數 ====================
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
            backup_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
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

        # 技術指標計算
        df['RSI'] = calculate_rsi(df['Close'], period=14)
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df.dropna(inplace=True)

        # 線性預測公式
        close_prices = df['Close'].tail(20).values
        x = np.arange(len(close_prices))
        slope, intercept = np.polyfit(x, close_prices, 1)
        pred_price = float((slope * 20 + intercept).item()) if hasattr(slope * 20 + intercept, 'item') else float(slope * 20 + intercept)
        current_price = float(df['Close'].iloc[-1])
        change_pct = float(((pred_price - current_price) / current_price) * 100)

        last_sma200 = float(df['SMA_200'].iloc[-1])
        last_ema20 = float(df['EMA_20'].iloc[-1])
        last_rsi = float(df['RSI'].iloc[-1])

        # 大師判斷邏輯
        buffett = current_price < last_sma200 * 1.15
        livermore = (current_price > last_ema20) and (change_pct > 0)
        lynch = 50 < last_rsi < 75
        wood = change_pct > 3.0
        simons = change_pct > 0.5

        # 完全保留當初一模一樣的文字報告 HTML 格式 (整合名稱與智慧幣別)
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
