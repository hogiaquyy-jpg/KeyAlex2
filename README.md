# License Key API

Hệ thống tạo & xác thực license key cho phần mềm, viết bằng FastAPI + SQLite.

## 1. Cài đặt

```bash
pip install -r requirements.txt
```

## 2. Đặt admin secret

Đây là "mật khẩu" để gọi các API quản trị (tạo key, xem danh sách...).
**Đổi giá trị này, đừng dùng mặc định:**

```bash
export ADMIN_SECRET="chuoi-bi-mat-cua-ban"
```

Trên Windows (PowerShell): `$env:ADMIN_SECRET="chuoi-bi-mat-cua-ban"`

## 3. Chạy server

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Mở trình duyệt tới `http://localhost:8000` → trang quản trị để tạo/xem key.
Nhập đúng `ADMIN_SECRET` vào ô "Admin Key" trên trang.

Tài liệu API tự động (Swagger): `http://localhost:8000/docs`

## 4. Các API chính

### Tạo key (admin) — `POST /admin/generate-keys`
Header: `X-Admin-Key: <ADMIN_SECRET>`
```json
{
  "quantity": 10,
  "product_name": "MyApp Pro",
  "max_activations": 1,
  "expires_in_days": 365,
  "prefix": "PRO"
}
```

### Xem danh sách key (admin) — `GET /admin/keys`
Header: `X-Admin-Key: <ADMIN_SECRET>`

### Thu hồi key (admin) — `POST /admin/revoke`
```json
{ "license_key": "PRO-AB3CD-..." }
```

### Kích hoạt key (client — phần mềm của bạn gọi) — `POST /api/v1/activate`
Không cần admin key. Gọi khi người dùng nhập key lần đầu.
```json
{ "license_key": "PRO-AB3CD-...", "device_id": "may-tinh-cua-khach-001" }
```
`device_id` là bạn tự sinh ra để định danh máy khách (vd hash từ thông tin phần cứng).

### Kiểm tra key còn hợp lệ không — `POST /api/v1/validate`
Gọi định kỳ (vd mỗi lần mở app) để chắc key chưa bị thu hồi/hết hạn.
```json
{ "license_key": "PRO-AB3CD-...", "device_id": "may-tinh-cua-khach-001" }
```
Trả về `{"valid": true/false, "reason": "..."}`.

## 5. Ví dụ gọi từ phần mềm của bạn (Python)

```python
import requests

resp = requests.post("https://api-cua-ban.com/api/v1/activate", json={
    "license_key": "PRO-AB3CD-EFGHJ-KMNPQ-RSTUV",
    "device_id": "hwid-cua-may-nay"
})
print(resp.json())
```

## 7. Triển khai lên Render KHÔNG mất key (bắt buộc đọc)

> Web cũ lưu key trong file SQLite `licenses.db` nằm cạnh code. Gói free của Render
> **xóa toàn bộ file mỗi lần deploy / restart / sleep** → đó là lý do key "tự xóa".
> Bản này đã hỗ trợ Postgres: chỉ cần đặt `DATABASE_URL` là key nằm trên database
> ngoài, restart kiểu gì cũng không mất.

### Bước 1 — Tạo database Postgres free (Neon, không tự xóa sau 30 ngày)

1. Vào `neon.tech` đăng ký (free, không cần thẻ).
2. Tạo project → tạo database → copy **Connection string** (dạng
   `postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require`).

### Bước 2 — Chuyển key hiện có sang Postgres (chạy 1 lần trên máy bạn)

```powershell
python -m pip install "psycopg[binary]==3.2.1"
$env:DATABASE_URL="postgresql://...neon.tech/...?sslmode=require"
python migrate.py
```

(Chạy lại nhiều lần cũng an toàn: key đã có sẽ được bỏ qua.)

### Bước 3 — Cấu hình trên Render (KHÔNG upload file .db nữa)

Vào service → **Environment**, thêm 2 biến:

| Key            | Value                          |
| -------------- | ------------------------------ |
| `DATABASE_URL` | connection string Neon ở trên  |
| `ADMIN_SECRET` | chuỗi bí mật mạnh (đổi khác `30012012`) |

Save → Render tự deploy lại. Từ giờ **đừng bấm Restart / Clear build cache** khi không cần,
và đừng upload file code qua Dashboard (mỗi lần là 1 lần deploy).

### Bước 4 — Giữ web luôn thức + backup

- **Giữ thức (free):** tạo monitor free trên `uptimerobot.com` ping URL web mỗi 5 phút.
  (Gói free Render có 750 giờ/tháng — vừa đủ 1 web chạy 24/7.)
- **Backup:** trên trang quản trị có nút **⬇ Backup** (tải toàn bộ key về file JSON).
  Backup mỗi tuần 1 lần. Mất gì thì bấm **⬆ Khôi phục** chọn file là xong.
- API tương ứng: `GET /admin/export`, `POST /admin/import` (header `X-Admin-Key`).

### Chạy local

Không đặt `DATABASE_URL` thì web dùng SQLite file `licenses.db` như cũ — deploy local
không ảnh hưởng gì.

### Lưu ý bảo mật

- Đặt `ADMIN_SECRET` mạnh, không commit vào git.
- Chạy sau reverse proxy có HTTPS (Nginx/Caddy) — đừng để lộ API ở HTTP trần.
- Cân nhắc giới hạn tốc độ gọi (rate limit) cho `/api/v1/activate` để tránh bị dò key.
- Có thể thêm chữ ký/mã hoá vào chính license key nếu muốn xác thực offline (không cần gọi API mỗi lần) — nói mình biết nếu bạn cần hướng đó.
