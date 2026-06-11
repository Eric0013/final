from flask import Flask, request, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz

app = Flask(__name__)

# 原汁原味紫色漸層背景，加入現代微光暈與倒數計時版面
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 股神助手 2.0</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { 
            background: linear-gradient(135deg, #1e1035, #4e2a84, #764ba2); 
            min-height: 100vh; 
            color: #fff;
            font-family: 'PingFang TC', 'Microsoft JhengHei', sans-serif;
        }
        .card { 
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 20px; 
            transition: all 0.3s ease;
        }
        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 35px rgba(118, 75, 162, 0.4);
        }
        .result { 
            background: rgba(255, 255, 255, 0.95); 
            border-radius: 16px; 
            padding: 25px; 
            color: #212529; 
            box-shadow: inset 0 2px 5px rgba(0,0,0,0.1);
        }
        .market-badge {
            font-size: 0.9rem;
            padding: 6px 12px;
            border-radius: 50px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255,255,255,0.2);
            display: inline-block;
            margin-bottom: 15px;
        }
        .btn-primary {
            background: linear-gradient(45deg, #a855f7, #6366f1);
            border: none;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        }
        .btn-primary:hover {
            background: linear-gradient(45deg, #c084fc, #818cf8);
        }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="text-center mb-5">
            <h1 class="text-white display-4 fw-bold mb-2">📈 AI 股神助手 <span class="fs-3 text-warning">v2.0</span></h1>
            <p class="text-light opacity-75 lead">核心數據免鎖 IP 引擎 • 五大名師量化策略 • 新聞情緒雷達</p>
        </div>

        <div class="row justify-content-center">
            <div class="col-md-9 col-lg-8">
                <div class="card p-4">
                    <div class="card-body">
                        <form id="stockForm">
                            <div class="input-group mb-3">
                                <input type="text" class="form-control form-control-lg bg-dark text-white border-secondary" 
                                       id="symbol" placeholder="例如：2330.TW 或 NVDA" required>
                                <button class="btn btn-primary btn-lg px-4" type="submit">開始分析</button>
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
            resultDiv.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary mb-3" role="status"></div>
                    <p class="mb-0 text-secondary fw-bold">🔄 正在獵取美加/亞太數據、解鎖新聞雷達...</p>
                    <small class="text-muted">跨海 Session 對齊中，請稍候 3~5 秒</small>
                </div>
            `;

            try {
                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `symbol=${encodeURIComponent(symbol)}`
                });
                
                const data = await res.json();
                
                if (data.error) {
                    resultDiv.innerHTML = `<h4 class="mb-3 text-danger">⚠️ 分析失敗</h4><p>${data.error}</p>`;
                } else {
                    resultDiv.innerHTML = `
                        <div class="market-badge text-white">🕰️ 專案市場狀態：${data.market_status}</div>
                        <h4 class="mb-3 fw-bold text-dark">分析結果 - ${data.symbol}</h4>
                        ${data.report}
                    `;
                }
            } catch (err) {
                resultDiv.innerHTML = `<h4 class="mb-3 text-danger">錯誤</h4><p>網際網路回傳封包異常，請確認代碼後再試一次。</p>`;
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

# ==================== 酷功能 1：全球開盤時間偵測 ====================
def get_market_status(symbol):
    tw_tz = pytz.timezone('Asia/Taipei')
    now_tw = datetime.now(tw_tz)
    weekday = now_tw.weekday() # 0-6 (0是週一)
    hour, minute = now_tw.hour, now_tw.minute
    time_val = hour * 100 + minute

    if '.TW' in symbol.upper() or /^\d+$/.test(symbol):
        if weekday >= 5: return "🟢 台股週末休市中"
        if 900 <= time_val <= 1330: return "⚡ 台股盤中即時交易"
        if time_val < 900: return "⏳ 距離今日台股開盤還有一些時間"
        return "🌙 台股已收盤"
    else:
        # 美股夏令時間簡單判定 (4月~10月晚上9:30開盤，其餘10:30)
        is_dst = 4 <= now_tw.month <= 10
        start_time = 2130 if is_dst else 2230
        end_time = 400 if is_dst else 500
        
        if weekday >= 5: return "🟢 美股週末休市中"
        if hour >= 21 or hour < 5:
            if hour == 21 and minute < 30 and is_dst: return "🌅 美股盤前熱身中"
            return "⚡ 美股正值開盤激戰中"
        return "🌙 美股進入休市沉睡期"

# ==================== 核心大師分析邏輯 ====================
def get_stock_analysis_report(symbol):
    try:
        df = None
        # 智慧雙載防堵機制
        try:
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            df = yf.download(symbol, period="2y", auto_adjust=True, progress=False, session=session, threads=False)
        except:
            df = None

        if df is None or df.empty:
            backup_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
            r = requests.get(backup_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            result = r.json()['chart']['result'][0]
            timestamps = result['timestamp']
            quotes = result['indicators']['quote'][0]
            adj_close = result['indicators']['adjclose'][0]['adjclose']
            parsed_data = [{'Date': pd.to_datetime(t, unit='s'), 'Open': quotes['open'][i], 'High': quotes['high'][i], 'Low': quotes['low'][i], 'Close': adj_close[i]} for i, t in enumerate(timestamps) if quotes['open'][i] and adj_close[i]]
            df = pd.DataFrame(parsed_data).set_index('Date')

        if df.empty or len(df) < 200:
            return f"❌ 找不到股票代碼 「{symbol}」 或該股票歷史資料不足。"

        # 技術指標
        df['RSI'] = calculate_rsi(df['Close'], period=14)
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df.dropna(inplace=True)

        # 線性趨勢預測
        close_prices = df['Close'].tail(20).values
        slope, intercept = np.polyfit(np.arange(20), close_prices, 1)
        pred_price = slope * 20 + intercept
        current_price = df['Close'].iloc[-1]
        change_pct = ((pred_price - current_price) / current_price) * 100

        # 原本大師判斷
        buffett = current_price < df['SMA_200'].iloc[-1] * 1.15
        livermore = (current_price > df['EMA_20'].iloc[-1]) and (change_pct > 0)
        lynch = 50 < df['RSI'].iloc[-1] < 75
        wood = change_pct > 3.0
        simons = change_pct > 0.5

        # ==================== 酷功能 2：財經新聞標題情感評分 ====================
        ai_bot_status = "❌ 觀望"
        ai_color = "red"
        try:
            ticker = yf.Ticker(symbol)
            news_list = ticker.news[:3] # 抓最新 3 則新聞
            pos_keywords = ['up', 'growth', 'buy', 'bull', 'gain', 'positive', 'profit', 'highest', '創高', '大賺', '買進']
            score = 0
            for n in news_list:
                title = n.get('title', '').lower()
                for kw in pos_keywords:
                    if kw in title: score += 1
            if score >= 1 or change_pct > 1.5:
                ai_bot_status = "✅ 看多多頭"
                ai_color = "green"
        except:
            pass

        # 組合 HTML 報告
        report = f"""
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
            report += f"<p class='mb-1'><strong>{name}：</strong> <span style='color:{color}'>{status}</span></p>"
            if result: recommendation += 1

        # 加入酷功能 2 的評分結果顯示
        report += f"<p class='mb-1'><strong>🤖 AI 新聞情緒雷達：</strong> <span style='color:{ai_color}'>{ai_bot_status}</span></p>"
        if ai_bot_status.startswith("✅"): recommendation += 1

        report += f"<hr><h4 class='fw-bold'>💡 綜合建議：{recommendation}/6 位評審看好</h4>"

        if recommendation >= 4:
            report += "<h3 style='color:green' class='fw-bold'>🔥 強力買入指標！</h3>"
        elif recommendation == 3:
            report += "<h3 style='color:orange' class='fw-bold'>⚖️ 可以考慮分批進場</h3>"
        else:
            report += "<h3 style='color:gray' class='fw-bold'>💤 建議繼續觀望</h3>"

        return report

    except Exception as e:
        return f"❌ 系統核心元件處理異常: {str(e)}"

# ==================== 網站路由 ====================

@app.route('/')
def home():
    return HTML_TEMPLATE

@app.route('/analyze', methods=['POST'])
def analyze():
    symbol = request.form.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': '請輸入股票代碼'})
    
    market_status = get_market_status(symbol)
    report = get_stock_analysis_report(symbol)
    return jsonify({'report': report, 'symbol': symbol, 'market_status': market_status})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
