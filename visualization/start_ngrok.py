#!/usr/bin/env python3
"""启动ngrok并获取公网URL"""
import subprocess
import time
import json
import urllib.request

# 启动ngrok
print("Starting ngrok...")
proc = subprocess.Popen(['/opt/homebrew/bin/ngrok', 'http', '9998', '--region', 'ap'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# 等待ngrok启动
time.sleep(5)

# 获取公网URL
try:
    resp = urllib.request.urlopen('http://localhost:4040/api/tunnels')
    data = json.loads(resp.read().decode())
    
    for tunnel in data['tunnels']:
        if tunnel['proto'] == 'https':
            print(f"Public URL: {tunnel['public_url']}")
            print(f"Local URL: {tunnel['config']['addr']}")
            break
    else:
        print("Failed to get public URL")
        print(f"ngrok output: {proc.stderr.read().decode()[:500]}")
except Exception as e:
    print(f"Error: {e}")
    # 尝试读取ngrok输出
    try:
        outs, errs = proc.communicate(timeout=2)
        print(f"stdout: {outs.decode()[:500]}")
        print(f"stderr: {errs.decode()[:500]}")
    except:
        proc.kill()
        print("ngrok process killed")
