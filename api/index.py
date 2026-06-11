from flask import Flask, render_template, request, jsonify
import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

app = Flask(__name__)

# ...（你的 get_stock_analysis_report 函數保持不變）...

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    symbol = request.form.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': '請輸入股票代碼'})
    
    report = get_stock_analysis_report(symbol)
    return jsonify({'report': report, 'symbol': symbol})

def get_stock_analysis_report(symbol):
    try:
        # 抓取資料
        df = yf.download(symbol, period="2y", auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty or len(df) < 100:
            return f"❌ 找不到股票代碼 {symbol} 或資料不足"

        # 技術指標
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['SMA_200'] = ta.sma(df['Close'], length=200)
        df.dropna(inplace=True)

        if len(df) < 60:
            return "❌ 資料量不足，無法進行分析"

        # AI 預測 (LSTM)
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(df[['Open', 'High', 'Low', 'Close', 'Volume']])

        X, y = [], []
        for i in range(60, len(scaled_data)):
            X.append(scaled_data[i-60:i])
            y.append(scaled_data[i, 3])  # Close price

        X, y = np.array(X), np.array(y)

        model = Sequential([
            Input(shape=(60, 5)),
            LSTM(50, return_sequences=False),
            Dropout(0.1),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(X, y, epochs=3, batch_size=32, verbose=0)

        # 預測明天價格
        last_60_days = scaled_data[-60:].reshape(1, 60, 5)
        pred_scaled = model.predict(last_60_days, verbose=0)
        
        dummy = np.zeros((1, 5))
        dummy[0, 3] = pred_scaled[0, 0]
        pred_price = scaler.inverse_transform(dummy)[0, 3]

        current_price = df['Close'].iloc[-1]
        change_pct = ((pred_price - current_price) / current_price) * 100

        # 大師判斷
        buffett = current_price < df['SMA_200'].iloc[-1] * 1.15
        livermore = (current_price > df['EMA_20'].iloc[-1]) and (change_pct > 0)
        lynch = 50 < df['RSI'].iloc[-1] < 75
        wood = change_pct > 3.0
        simons = change_pct > 0.5

        # 產生報告
        report = f"""
        📊 <strong>股票代碼：</strong> {symbol}<br>
        💰 <strong>當前價格：</strong> {current_price:.2f} USD<br>
        🤖 <strong>AI 預測下個交易日：</strong> {pred_price:.2f} 
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
        print(f"Error: {e}")
        return "❌ 分析過程中發生錯誤，請確認股票代碼是否正確。"

# ==================== 網站路由 ====================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    symbol = request.form.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': '請輸入股票代碼'})
    
    report = get_stock_analysis_report(symbol)
    return jsonify({'report': report, 'symbol': symbol})

if __name__ == '__main__':
    # 建立 templates 資料夾與 index.html
    os.makedirs('templates', exist_ok=True)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write('''
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
            <p class="text-white lead">輸入股票代碼，獲得五大名師 + AI 深度分析</p>
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
            resultDiv.innerHTML = '<p class="text-center">🔄 正在進行深度學習分析，請稍候...</p>';

            const res = await fetch('/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: `symbol=${encodeURIComponent(symbol)}`
            });
            
            const data = await res.json();
            resultDiv.innerHTML = `<h4 class="mb-3">分析結果 - ${data.symbol}</h4>${data.report}`;
        });
    </script>
</body>
</html>
        ''')
    
    print("✅ 網站已準備好！")
    app.run(debug=True, port=5000)
