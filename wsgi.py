from waitress import serve
from server import app  # ใช้ชื่อไฟล์ของคุณแทน server

if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=5000)
