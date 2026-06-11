from flask import Flask, request, jsonify, make_response
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)

# 完美還原截圖：Cyberpunk 科技深色風、左右雙獨立圖表、下方雙欄大師卡片
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 股神助手 v3.7</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        body { 
            background: linear-gradient(135deg, #0f0f1a, #1a1a2e); 
            min-height: 100vh; 
            color: #f4f4f7; 
            font-family: 'PingFang TC', 'Microsoft JhengHei', sans-serif;
        }
        .navbar-brand-custom {
            font-size: 1.5rem;
            font-weight: bold;
            color: #fff;
            padding: 15px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .card-custom { 
            background: #151526; 
            border: 1px solid #252542; 
            border-radius: 12px; 
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }
        .form-control-custom {
            background-color: #1a1a30;
            border: 1px solid #3d3d66;
            color: #fff;
            border-radius: 6px;
        }
        .form-control-custom:focus {
            background-color: #1a1a30;
            color: #fff;
            border-color: #a855f7;
            box-shadow: 0 0 10px rgba(168, 85, 247, 0.3);
        }
        .btn-custom {
            background: #ffffff;
            color: #10101c;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 10px 24px;
            transition: all 0.2s;
        }
        .btn-custom:hover {
            background: #e2e8f0;
            transform: translateY(-1px);
        }
        /* 雙圖表左右排版容器 */
        .charts-wrapper {
            display: grid;
            grid-template-columns: 68% 30%;
            gap: 2%;
            background: #151526;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #252542;
        }
        .chart-box {
            background: #111122;
            border-radius: 8px;
            padding: 10px;
            border: 1px solid #1f1f38;
        }
        /* 下方大師報告雙欄對齊 */
        .report-grid {
            display: grid;
            grid-template-columns: 65% 32%;
            gap: 3%;
            margin-top: 20px;
        }
        .masters-list {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px 24px;
        }
        .suggestion-box {
            background: rgba(16, 185, 129, 0.05);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.1);
        }
        hr { border-color: rgba(255, 255, 255, 0.1); }
    </style>
</head>
<body>
    <div class="container py-4">
        <div class="d-flex justify-content-between align-items-center navbar-brand-custom mb-4">
            <div>📈 AI 股神助手 <span class="text-secondary fs-5" id="titleHeader">v3.7 | 技術趨勢圖 (近10日)</span></div>
            <div style="width: 450px;">
                <form id="stockForm" class="d-flex gap-2">
                    <input type="text" class="form-control form-control-custom" id="symbol" placeholder="例如：2330.TW 或 NVDA" required>
                    <button class="btn btn-custom text-nowrap" type="submit">開始分析</button>
                </form>
            </div>
        </div>

        <div id="outputSection" style="display: none;">
            
            <div class="charts-wrapper mb-4">
                <div>
                    <small class="text-muted d-block mb-2">📊 技術趨勢圖 (精準最近 10 個交易日 K線 + EMA20)</small>
                    <div id="klineChart" class="chart-box"></div>
                </div>
                <div>
                    <small class="text-muted d-block mb-2">📈 KD 指標軸 (0-100)</small>
                    <div id="kdChart" class="chart-box"></div>
                </div>
            </div>
            
            <div class="card-custom p-4">
                <h5 class="mb-4 text-white">📋 策略分析報告</h5>
                <div id="resultContent"></div>
            </div>

        </div>
    </div>

    <script>
        let klineChartInstance = null;
        let kdChartInstance = null;

        document.getElementById('stockForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const symbol = document.getElementById('symbol').value.trim().toUpperCase();
            const outputSection = document.getElementById('outputSection');
            const resultContent = document.getElementById('resultContent');
            const klineChartDiv = document.getElementById('klineChart');
            const kdChartDiv = document.getElementById('kdChart');
            
            outputSection.style.display = 'block';
            resultContent.innerHTML = '<p class="text-muted">🔄 正在計算量化核心指標與大師策略審查...</p>';
            klineChartDiv.innerHTML = '<p class="text-center text-muted py-5">載入中...</p>';
            kdChartDiv.innerHTML = '<p class="text-center text-muted py-5">載入中...</p>';

            try {
                const response = await fetch('/analyze?t=' + new Date().getTime(), {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `symbol=${encodeURIComponent(symbol)}`
                });
                const data = await response.json();
                
                if (data.error) {
                    resultContent.innerHTML = `<h4 class="text-danger">分析失敗</h4><p>${data.error}</p>`;
                    return;
                }

                // 更新頂部動態 Titile 抬頭
                document.getElementById('titleHeader').innerHTML = `v3.7 | ${data.stock_fullname} 技術趨勢圖 (近10日)`;

                // 渲染下方精心對齊的雙欄報告 HTML
                resultContent.innerHTML = data.report;

                // 準備圖表時間軸與數據
                const timestamps = data.k_data.map(item => item.time);
                
                const candlestickData = data.k_data.map(item => ({
                    x: item.time,
                    y: [item.open, item.high, item.low, item.close]
                }));
                const emaData = data.k_data.map(item => ({ x: item.time, y: item.ema20 }));
                const kData = data.k_data.map(item => ({ x: item.time, y: item.k }));
                const dData = data.k_data.map(item => ({ x: item.time, y: item.d }));

                // ➡️ 【左圖】配置：純粹俐落的 K線價 + EMA20均線趨勢
                const klineOptions = {
                    series: [
                        { name: 'K線價', type: 'candlestick', data: candlestickData },
                        { name: 'EMA20趨勢線', type: 'line', data: emaData }
                    ],
                    chart: { type: 'line', height: 380, background: '#111122', foreColor: '#8e8eaf', toolbar: { show: false } },
                    xaxis: { type: 'datetime', labels: { datetimeUTC: true, format: 'MM月dd日' } },
                    yaxis: { decimalsInFloat: 2, labels: { style: { colors: '#8e8eaf' } } },
                    stroke: { width: [1, 2.5] },
                    colors: ['#ef5350', '#ff9800'],
                    grid: { borderColor: '#1f1f38' },
                    plotOptions: { candlestick: { colors: { upward: '#ef5350', downward: '#26a69a' }, wick: { useFillColor: true } } }
                };

                // ➡️ 【右圖】配置：純粹乾淨的 KD 指標交叉線 (包含 80 超買與 20 超賣保底防線)
                const kdOptions = {
                    series: [
                        { name: 'K線 (KD)', data: kData },
                        { name: 'D線 (KD)', data: dData }
                    ],
                    chart: { type: 'line', height: 380, background: '#111122', foreColor: '#8e8eaf', toolbar: { show: false } },
                    xaxis: { type: 'datetime', labels: { datetimeUTC: true, format: 'MM月dd日' } },
                    yaxis: { max: 100, min: 0, tickAmount: 4, labels: { style: { colors: '#8e8eaf' } } },
                    stroke: { width: [2, 2], curve: 'smooth', dashArray: [0, 4] },
                    colors: ['#00b0ff', '#ffea00'],
                    grid: { borderColor: '#1f1f38' },
                    annotations: {
                        yaxis: [
                            { y: 80, borderColor: '#ef5350', strokeDashArray: 3, label: { text: '(Overbought)', style: { color: '#ef5350', background: 'transparent' } } },
                            { y: 20, borderColor: '#00b0ff', strokeDashArray: 3, label: { text: '(Oversold)', style: { color: '#00b0ff', background: 'transparent' } } }
                        ]
                    }
                };

                // 銷毀舊圖表實例並渲染新雙軸圖表
                if (klineChartInstance) klineChartInstance.destroy();
                if (kdChartInstance) kdChartInstance.destroy();
                
                klineChartDiv.innerHTML = '';
                kdChartDiv.innerHTML = '';
                
                klineChartInstance = new ApexCharts(klineChartDiv, klineOptions);
                kdChartInstance = new ApexCharts(kdChartDiv, kdOptions);
                
                klineChartInstance.render();
                kdChartInstance.render();

            } catch (err) {
                resultContent.innerHTML = `<h4 class="text-danger">錯誤</h4><p>技術面渲染封包異常，請重試。</p>`;
            }
        });
    </script>
</body>
</html>
'''

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

# ==================== 量化策略運算核心 ====================
def get_stock_analysis_data(symbol):
    try:
        api_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(api_url, headers=headers, timeout=10)
        y_data = r.json()
        
        result = y_data['chart']['result'][0]
        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]
        adj_close = result['indicators']['adjclose'][0]['adjclose']
        
        stock_fullname = result['meta'].get('shortName', symbol)
        currency = "TWD" if ".TW" in symbol.upper() else "USD"

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
            return None, f"❌ 找不到股票代碼 「{symbol}」 或該股票歷史資料不足。", symbol

        # 量化運算
        delta = df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        df['RSI'] = 100.0 - (100.0 / (1.0 + (avg_gain / (avg_loss + 1e-9))))
        
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        k_list, d_list = calculate_backend_kd(df['Close'], df['High'], df['Low'], 9)
        df['K'] = k_list
        df['D'] = d_list
        df.dropna(inplace=True)

        # 趨勢預測
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

        # 👴 ➡️ 100% 還原截圖中「高質感左右雙欄排版」的 HTML 架構！
        report = f"""
        <div class="row mb-3">
            <div class="col-sm-6 text-secondary">💰 當前價格：<span class="text-dark fw-bold fs-5">{current_price:.2f} {currency}</span></div>
            <div class="col-sm-6 text-secondary">🤖 AI 趨勢預測下個交易日：<span class="text-dark fw-bold fs-5">{pred_price:.2f} {currency}</span> 
                <span style="color:{'#ef5350' if change_pct > 0 else '#26a69a'}; font-weight:bold;">({change_pct:+.2f}%)</span>
            </div>
        </div>
        <hr>
        <div class="report-grid">
            <div>
                <h6 class="fw-bold text-secondary mb-3">💡 五大名師看法</h6>
                <div class="masters-list">
                    <div>👴 巴菲特：<span style="color:{'#ef5350' if buffett else '#26a69a'}; font-weight:bold;">{'✅ 價格合理' if buffett else '❌ 價格太貴'}</span></div>
                    <div>👓 彼得・林區：<span style="color:{'#ef5350' if lynch else '#26a69a'}; font-weight:bold;">{'✅ 動能強勁' if lynch else '❌ 進入整理'}</span></div>
                    <div>🎩 李佛摩：<span style="color:{'#ef5350' if livermore else '#26a69a'}; font-weight:bold;">{'✅ 趨勢向上' if livermore else '❌ 趨勢不明'}</span></div>
                    <div>🚀 凱薩琳・伍德：<span style="color:{'#ef5350' if wood else '#26a69a'}; font-weight:bold;">{'✅ 具爆發力' if wood else '❌ 成長緩慢'}</span></div>
                    <div>💻 西蒙斯：<span style="color:{'#ef5350' if simons else '#26a69a'}; font-weight:bold;">{'✅ 數據勝率高' if simons else '❌ 數據勝率低'}</span></div>
                </div>
            </div>
            
            <div class="suggestion-box" style="background:{'rgba(239,83,80,0.05)' if recommendation >=4 else ('rgba(26,166,154,0.05)' if recommendation==3 else 'rgba(142,142,175,0.05)')}; border-color:{'#ef5350' if recommendation >=4 else ('#26a69a' if recommendation==3 else '#8e8eaf')}">
                <div class="text-secondary small mb-1">💡 綜合建議</div>
                <div class="fs-4 fw-bold text-dark mb-2">{recommendation}/5 位大師看好</div>
                <div class="fs-5 fw-bold" style="color:{'#ef5350' if recommendation >=4 else ('#26a69a' if recommendation==3 else '#8e8eaf')}">
                    {'⚖️ ⚖️ 可以考慮分批進場' if recommendation == 3 else ('🔥 🔥 強力買入指標！' if recommendation >= 4 else '💤 建議繼續觀望')}
                </div>
            </div>
        </div>
        """

        # 嚴格精準切出 10 日交易日做渲染
        chart_df = df.tail(10)
        k_data_list = []
        for _, row in chart_df.iterrows():
            k_data_list.append({
                'time': int(row['time']), 'open': float(row['Open']), 'high': float(row['High']), 'low': float(row['Low']), 'close': float(row['Close']),
                'ema20': float(row['EMA_20']), 'k': float(row['K']), 'd': float(row['D'])
            })

        return {'report': report, 'k_data': k_data_list, 'stock_fullname': stock_fullname}, None, stock_fullname

    except Exception as e:
        return None, f"❌ 數據庫清洗異常: {str(e)}", symbol

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
        
    data, error, stock_name = get_stock_analysis_data(symbol)
    if error:
        return jsonify({'error': error})
        
    response = make_response(jsonify({'report': data['report'], 'symbol': symbol, 'k_data': data['k_data'], 'stock_fullname': stock_name}))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
