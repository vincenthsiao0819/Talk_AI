import socket
import subprocess

s = socket.socket()
s.bind(("0.0.0.0", 5005))
s.listen(5)
print("Mac ears listener started on port 5005")

while True:
    try:
        c, a = s.accept()
        data = c.recv(4096).decode('utf-8').strip()
        c.close()
        if data:
            print("Received from POS:", data)
            
            # 1. 雙向紀錄：發送 Telegram 訊息讓使用者知道 Lobster 聽到了什麼
            subprocess.Popen([
                "openclaw", "message", "send", 
                "--channel telegram --target", "telegram:5916594299", 
                "--message", f"🗣️ Lobster 聽到：{data}"
            ])
            
            # 2. 觸發極速大腦回答：覆寫模型為 DeepSeek-v4-Flash，並強制字數限制在 30 字內
            subprocess.Popen([
                "openclaw", "agent", 
                "--session-key", "agent:main:telegram:direct:5916594299", 
                "--model", "deepseek/deepseek-v4-flash",
                "--message", f"[客廳語音] {data} (請將回覆濃縮在 30 字以內，以便加速語音播報)", 
                "--deliver"
            ])
    except Exception as e:
        print("Error:", e)
