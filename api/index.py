
        /* 策略分析報告一體化面板 */
        .card-custom { 
            background: rgba(21, 21, 38, 0.7);
            border: 1px solid rgba(61, 61, 102, 0.4);
            border-radius: 14px; 
            backdrop-filter: blur(10px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
        }
        .report-grid {
            display: grid;
            grid-template-columns: 65% 32%;
            gap: 3%;
            margin-top: 20px;
        }
        .masters-list {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px 28px;
        }
        .suggestion-box {
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        hr { border-color: rgba(255, 255, 255, 0.12); }
    </style>
</head>
<body>
    <div class="container">
        
        <div id="mainWrapper" class="main-wrapper">
            <div class="hero-header w-100" id="headerNode">
                <h1 class="hero-title" id="appTitle">📈 AI 股神助手</h1>
                <div class="version-badge mt-2" id="versionNode">六大名師聯手量化分析面板 <span class="badge bg-dark text-secondary">v4.0</span></div>
            </div>

            <div class="search-container mb-4" id="searchNode">
                <form id="stockForm" class="d-flex gap-2 w-100">
                    <input type="text" class="form-control form-control-custom w-100" id="symbol" placeholder="例如：2330.TW 或 NVDA" required>
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
            
            const mainWrapper = document.getElementById('mainWrapper');
            const appTitle = document.getElementById('appTitle');
            const headerNode = document.getElementById('headerNode');
            const searchNode = document.getElementById('searchNode');
            
            const outputSection = document.getElementById('outputSection');
            const resultContent = document.getElementById('resultContent');
            const klineChartDiv = document.getElementById('klineChart');
            const kdChartDiv = document.getElementById('kdChart');
            
            mainWrapper.classList.add('searched');
            if(!headerNode.classList.contains('setup-done')) {
                headerNode.appendChild(searchNode);
                headerNode.classList.add('setup-done');
            }
            
            outputSection.style.display = 'block';
            resultContent.innerHTML = '<p class="text-muted">🔄 正在同步六大名師開會共識中...</p>';
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

                appTitle.innerHTML = `📈 AI 股神助手 <span class="text-secondary fs-5">v4.0 | ${data.stock_fullname} 技術趨勢圖 (近10日)</span>`;
                document.getElementById('versionNode').style.display = 'none';

                resultContent.innerHTML = data.report;

                const candlestickData = data.k_data.map(item => ({ x: item.time, y: [item.open, item.high, item.low, item.close] }));
                const emaData = data.k_data.map(item => ({ x: item.time, y: item.ema20 }));
                const kData = data.k_data.map(item => ({ x: item.time, y: item.k }));
                const dData = data.k_data.map(item => ({ x: item.time, y: item.d }));

                const klineOptions = {
                    series: [
                        { name: 'K線價', type: 'candlestick', data: candlestickData },
                        { name: 'EMA20趨勢線', type: 'line', data: emaData }
                    ],
                    chart: { type: 'line', height: 380, background: '#0b0b14', foreColor: '#8e8eaf', toolbar: { show: false } },
                    xaxis: { type: 'datetime', labels: { datetimeUTC: true, format: 'MM月dd日' } },
                    yaxis: { decimalsInFloat: 2, labels: { style: { colors: '#8e8eaf' } } },
                    stroke: { width: [1, 2.5] },
                    colors: ['#ef5350', '#ff9800'],
                    grid: { borderColor: '#1c1c30' },
                    plotOptions: { candlestick: { colors: { upward: '#ef5350', downward: '#26a69a' }, wick: { useFillColor: true } } }
                };

                const kdOptions = {
                    series: [
                        { name: 'K線 (KD)', data: kData },
                        { name: 'D線 (KD)', data: dData }
                    ],
                    chart: { type: 'line', height: 380, background: '#0b0b14', foreColor: '#8e8eaf', toolbar: { show: false } },
                    xaxis: { type: 'datetime', labels: { datetimeUTC: true, format: 'MM月dd日' } },
                    yaxis: { max: 100, min: 0, tickAmount: 4, labels: { style: { colors: '#8e8eaf' } } },
                    stroke: { width: [2, 2], curve: 'smooth', dashArray: [0, 4] },
                    colors: ['#00b0ff', '#ffea00'],
                    grid: { borderColor: '#1c1c30' },
                    annotations: {
                        yaxis: [
                            { y: 80, borderColor: '#ef5350', strokeDashArray: 3, label: { text: '(Overbought)', style: { color: '#ef5350', background: 'transparent' } } },
                            { y: 20, borderColor: '#00b0ff', strokeDashArray: 3, label: { text: '(Oversold)', style: { color: '#00b0ff', background: 'transparent' } } }
                        ]
                    }
                };

                if (klineChartInstance) klineChartInstance.destroy();
                if (kdChartInstance) kdChartInstance.destroy();
                
                klineChartDiv.innerHTML = '';
                kdChartDiv.innerHTML = '';
                
                klineChartInstance = new ApexCharts(klineChartDiv, klineOptions);
                kdChartInstance = new ApexCharts(kdChartDiv, kdOptions);
                
                klineChartInstance.render();
                kdChartInstance.render();

            } catch (err) {
                resultContent.innerHTML = `<h4 class="text-danger">錯誤</h4><p>量化技術面渲染異常，請重試。</p>`;
            }
        });
    </script>
</body>
</html>
'''
