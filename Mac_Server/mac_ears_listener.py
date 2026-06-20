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
            subprocess.Popen([
                "openclaw", "agent", 
                "--session-key", "agent:main:telegram:direct:5916594299", 
                "--message", f"[客廳語音] {data}", 
                "--deliver"
            ])
    except Exception as e:
        print("Error:", e)
