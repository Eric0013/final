from flask import Flask, request, jsonify, make_response
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)

# v4.0 Master Edition：加入傳奇分析師 🔥張期凱 (只會說買爆)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 股神助手 v4.0</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        body { 
            background: linear-gradient(135deg, #09090e, #120c1f, #1a102f); 
            min-height: 100vh; 
            color: #f4f4f7; 
            font-family: 'PingFang TC', 'Microsoft JhengHei', sans-serif;
            overflow-x: hidden;
            padding-bottom: 50px;
        }
        
        .main-wrapper {
            min-height: 85vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            transition: all 0.6s cubic-bezier(0.25, 1, 0.5, 1);
            width: 100%;
        }
        
        .main-wrapper.searched {
            min-height: auto;
            justify-content: flex-start;
            align-items: stretch;
            padding-top: 20px;
        }

        .hero-header {
            text-align: center;
            margin-bottom: 2rem;
            transition: all 0.6s ease;
        }
        .main-wrapper.searched .hero-header {
            text-align: left;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 15px;
        }

        .hero-title {
            font-size: 2.5rem;
            font-weight: bold;
            text-shadow: 0 0 25px rgba(168, 85, 247, 0.3);
            margin: 0;
        }
        .main-wrapper.searched .hero-title {
            font-size: 1.6rem;
        }

        .version-badge {
            font-size: 1rem;
            color: #a855f7;
            font-weight: normal;
        }

        .search-container {
            width: 100%;
            max-width: 650px;
            transition: all 0.6s cubic-bezier(0.25, 1, 0.5, 1);
        }
        .main-wrapper.searched .search-container {
            max-width: 450px;
            margin: 0 !important;
        }

        .form-control-custom {
            background-color: rgba(26, 26, 48, 0.8);
            border: 1px solid #3d3d66;
            color: #fff;
            padding: 14px 22px;
            font-size: 1.1rem;
            border-radius: 10px;
            backdrop-filter: blur(5px);
            transition: all 0.3s;
        }
        .main-wrapper.searched .form-control-custom {
            padding: 9px 18px;
            font-size: 1rem;
            border-radius: 7px;
        }
        .form-control-custom:focus {
            background-color: #1a1a30;
            color: #fff;
            border-color: #c084fc;
            box-shadow: 0 0 18px rgba(192, 132, 252, 0.5);
        }

        .btn-custom {
            background: #ffffff;
            color: #0f0f1a;
            font-weight: bold;
            border: none;
            border-radius: 10px;
            padding: 14px 32px;
            font-size: 1.1rem;
            transition: all 0.2s;
        }
        .main-wrapper.searched .btn-custom {
            padding: 9px 24px;
            font-size: 1rem;
            border-radius: 7px;
        }
        .btn-custom:hover {
            background: #f1f5f9;
            transform: translateY(-1px);
        }

        /* 左右雙圖表排版 */
        .charts-wrapper {
            display: grid;
            grid-template-columns: 68% 30%;
            gap: 2%;
            background: rgba(21, 21, 38, 0.7);
            padding: 22px;
            border-radius: 14px;
            border: 1px solid rgba(61, 61, 102, 0.4);
            backdrop-filter: blur(10px);
        }
        .chart-box {
            background: #0b0b14;
            border-radius: 10px;
            padding: 12px;
            border: 1px solid #1c1c30;
        }