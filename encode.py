import base64

with open("bpjs-drive-bot.json", "rb") as f:
    print(base64.b64encode(f.read()).decode())
