#!/usr/bin/env python3
"""下载Vue和ECharts到本地"""
import urllib.request
import os

lib_dir = os.path.join(os.path.dirname(__file__), 'lib')
os.makedirs(lib_dir, exist_ok=True)

urls = {
    'vue.global.js': 'https://cdn.jsdelivr.net/npm/vue@3.5.39/dist/vue.global.js',
    'echarts.min.js': 'https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js',
}

for filename, url in urls.items():
    try:
        print(f"下载 {filename} ...")
        urllib.request.urlretrieve(url, os.path.join(lib_dir, filename))
        size = os.path.getsize(os.path.join(lib_dir, filename))
        print(f"  OK: {size/1024:.0f} KB")
    except Exception as e:
        print(f"  FAIL: {e}")
