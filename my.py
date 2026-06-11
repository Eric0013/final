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
                    'time': int(timestamps[i] * 1000), 'Open': float(quotes['open'][i]), 'High': float(quotes['high'][i]), 'Low': float(quotes['low'][i]), 'Close': float(adj_close[i])
                })
        
        df = pd.DataFrame(parsed_data)
        if df.empty or len(df) < 200:
            return None, f"❌ 找不到股票代碼 「{symbol}」 或該股票歷史資料不足。", symbol

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

        tail_20 = df['Close'].tail(20).values
        slope, intercept = np.polyfit(np.arange(20), tail_20, 1)
        pred_raw = slope * 20 + intercept
        pred_price = float(pred_raw.item()) if hasattr(pred_raw, 'item') else float(pred_raw)
        
        current_price = float(df['Close'].iloc[-1])
        change_pct = float(((pred_price - current_price) / current_price) * 100.0)

        # 舊大師邏輯
        buffett = current_price < float(df['SMA_200'].iloc[-1]) * 1.15
        livermore = (current_price > float(df['EMA_20'].iloc[-1])) and (change_pct > 0.0)
        lynch = 50.0 < float(df['RSI'].iloc[-1]) < 75.0
        wood = change_pct > 3.0
        simons = change_pct > 0.5
        
        # 💡 張期凱：永遠看多買爆！直接塞 True
        chi_kai = True 

        # 票數計算總共 6 位大師
        recommendation = sum([buffett, livermore, lynch, wood, simons, chi_kai])

        report = f"""
        <div class="row mb-3">
            <div class="col-sm-6 text-secondary">💰 當前價格：<span class="text-white fw-bold fs-5">{current_price:.2f} {currency}</span></div>
            <div class="col-sm-6 text-secondary">🤖 AI 趨勢預測下個交易日：<span class="text-white fw-bold fs-5">{pred_price:.2f} {currency}</span> 
                <span style="color:{'#ef5350' if change_pct > 0 else '#26a69a'}; font-weight:bold;">({change_pct:+.2f}%)</span>
            </div>
        </div>
        <hr>
        <div class="report-grid">
            <div>
                <h6 class="fw-bold text-secondary mb-3">💡 六大名師看法</h6>
                <div class="masters-list">
                    <div>👴 巴菲特：<span style="color:{'#26a69a' if buffett else '#ef5350'}; font-weight:bold;">{'✅ 價格合理' if buffett else '❌ 價格太貴'}</span></div>
                    <div>👓 彼得・林區：<span style="color:{'#26a69a' if lynch else '#ef5350'}; font-weight:bold;">{'✅ 動能強勁' if lynch else '❌ 進入整理'}</span></div>
                    <div>🎩 李佛摩：<span style="color:{'#26a69a' if livermore else '#ef5350'}; font-weight:bold;">{'✅ 趨勢向上' if livermore else '❌ 趨勢不明'}</span></div>
                    <div>🚀 凱薩琳・伍德：<span style="color:{'#26a69a' if wood else '#ef5350'}; font-weight:bold;">{'✅ 具爆發力' if wood else '❌ 成長緩慢'}</span></div>
                    <div>💻 西蒙斯：<span style="color:{'#26a69a' if simons else '#ef5350'}; font-weight:bold;">{'✅ 數據勝率高' if simons else '❌ 數據勝率低'}</span></div>
                    <div>🔥 張期凱：<span style="color:#ef5350; font-weight:bold;">✅ 買爆</span></div>
                </div>
            </div>
            
            <div class="suggestion-box" style="background:{'rgba(239,83,80,0.06)' if recommendation >=4 else ('rgba(38,166,154,0.06)' if recommendation==3 else 'rgba(142,142,175,0.06)')}; border: 1px solid {'#ef5350' if recommendation >=4 else ('#26a69a' if recommendation==3 else '#3d3d66')};">
                <div class="text-secondary small mb-1">💡 綜合建議</div>
                <div class="fs-4 fw-bold text-white mb-2">{recommendation}/6 位大師看好</div>
                <div class="fs-5 fw-bold" style="color:{'#ef5350' if recommendation >=4 else ('#26a69a' if recommendation==3 else '#8e8eaf')}">
                    {'⚖️ 可以考慮分批進場' if recommendation == 3 else ('🔥 強力買入指標！' if recommendation >= 4 else '💤 建議繼續觀望')}
                </div>
            </div>
        </div>
        """

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
