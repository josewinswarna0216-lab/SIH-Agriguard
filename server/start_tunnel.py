import sys
import time
from pyngrok import ngrok, conf

authtoken = sys.argv[1]
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5001

ngrok.set_auth_token(authtoken)
tunnel = ngrok.connect(port, "http")
print(f"PUBLIC_URL={tunnel.public_url}")
sys.stdout.flush()

while True:
    time.sleep(60)
