import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from starlette.middleware.base import BaseHTTPMiddleware

from database import init_db, get_db, import_backup
from key_utils import generate_license_key

# ============================================================
# APP KHỞI TẠO
# ============================================================
app = FastAPI(title="License Key API")

# Middleware cho ngrok (bỏ cảnh báo)
class NgrokSkipWarningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.headers.__dict__["_list"].append(
            (b"ngrok-skip-browser-warning", b"1")
        )
        response = await call_next(request)
        return response

app.add_middleware(NgrokSkipWarningMiddleware)

# ============================================================
# CẤU HÌNH
# ============================================================
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "30012012")

# Khởi tạo database
init_db()

ADMIN_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin.html")

# ============================================================
# ROUTES
# ============================================================
@app.get("/")
def root():
    """Trang chủ - đọc file admin.html trực tiếp"""
    if os.path.exists(ADMIN_HTML):
        with open(ADMIN_HTML, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        return {"message": "Admin page not found. Please create admin.html"}

# ---- Xác thực admin ----
def require_admin(x_admin_key: Optional[str] = Header(None)):
    if not x_admin_key or x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Sai hoặc thiếu X-Admin-Key")
    return True

# ==================== SCHEMAS ====================
def _now() -> str:
    """Timestamp hiện tại dạng ISO. Dùng chung cho SQLite và Postgres
    (tránh hàm datetime('now') chỉ có trên SQLite)."""
    return datetime.utcnow().isoformat()


class GenerateKeysRequest(BaseModel):
    quantity: int = 1
    product_name: str
    customer_email: Optional[EmailStr] = None
    max_activations: int = 1
    expires_in_days: Optional[int] = None
    prefix: Optional[str] = ""
    note: Optional[str] = None

class RevokeRequest(BaseModel):
    license_key: str

class ActivateRequest(BaseModel):
    license_key: str
    device_id: str

class ValidateRequest(BaseModel):
    license_key: str
    device_id: str

# ==================== ADMIN: SINH KEY ====================
@app.post("/admin/generate-keys", dependencies=[Depends(require_admin)])
def generate_keys(req: GenerateKeysRequest):
    if req.quantity < 1 or req.quantity > 1000:
        raise HTTPException(400, "quantity phải từ 1 đến 1000")

    expires_at = None
    if req.expires_in_days:
        expires_at = (datetime.utcnow() + timedelta(days=req.expires_in_days)).isoformat()

    created_keys = []
    with get_db() as db:
        for _ in range(req.quantity):
            while True:
                key = generate_license_key(req.prefix or "")
                exists = db.execute(
                    "SELECT 1 FROM licenses WHERE license_key = ?", (key,)
                ).fetchone()
                if not exists:
                    break
            db.execute(
                """INSERT INTO licenses
                   (license_key, product_name, customer_email, max_activations, expires_at, note)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (key, req.product_name, req.customer_email, req.max_activations, expires_at, req.note),
            )
            created_keys.append(key)
        db.commit()

    return {"created": len(created_keys), "keys": created_keys}

# ==================== ADMIN: DANH SÁCH ====================
@app.get("/admin/keys", dependencies=[Depends(require_admin)])
def list_keys(product_name: Optional[str] = None, status: Optional[str] = None):
    query = "SELECT * FROM licenses WHERE 1=1"
    params = []
    if product_name:
        query += " AND product_name = ?"
        params.append(product_name)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"

    with get_db() as db:
        rows = db.execute(query, params).fetchall()
        result = []
        for row in rows:
            activations = db.execute(
                "SELECT device_id, activated_at FROM activations WHERE license_id = ?",
                (row["id"],),
            ).fetchall()
            item = dict(row)
            item["activations"] = [dict(a) for a in activations]
            item["activations_used"] = len(activations)
            result.append(item)
    return result

# ==================== ADMIN: THU HỒI / KHÔI PHỤC ====================
@app.post("/admin/revoke", dependencies=[Depends(require_admin)])
def revoke_key(req: RevokeRequest):
    with get_db() as db:
        cur = db.execute(
            "UPDATE licenses SET status = 'revoked' WHERE license_key = ?",
            (req.license_key,),
        )
        db.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Không tìm thấy key")
    return {"status": "revoked", "license_key": req.license_key}

@app.post("/admin/reactivate", dependencies=[Depends(require_admin)])
def reactivate_key(req: RevokeRequest):
    with get_db() as db:
        cur = db.execute(
            "UPDATE licenses SET status = 'active' WHERE license_key = ?",
            (req.license_key,),
        )
        db.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Không tìm thấy key")
    return {"status": "active", "license_key": req.license_key}

# ==================== ADMIN: XÓA KEY VĨNH VIỄN ====================
@app.delete("/admin/keys/{license_key}", dependencies=[Depends(require_admin)])
def delete_key_permanently(license_key: str):
    with get_db() as db:
        lic = db.execute(
            "SELECT id FROM licenses WHERE license_key = ?", (license_key,)
        ).fetchone()
        if not lic:
            raise HTTPException(404, "Không tìm thấy key")
        db.execute("DELETE FROM activations WHERE license_id = ?", (lic["id"],))
        db.execute("DELETE FROM licenses WHERE license_key = ?", (license_key,))
        db.commit()
    return {"status": "deleted", "license_key": license_key}

# ==================== API CLIENT ====================
def _get_license(db, license_key: str):
    return db.execute(
        "SELECT * FROM licenses WHERE license_key = ?", (license_key,)
    ).fetchone()

def _check_expired(row) -> bool:
    if row["expires_at"] is None:
        return False
    return datetime.utcnow() > datetime.fromisoformat(row["expires_at"])

@app.post("/api/v1/activate")
def activate(req: ActivateRequest):
    with get_db() as db:
        lic = _get_license(db, req.license_key)
        if not lic:
            raise HTTPException(404, "License key không tồn tại")
        if lic["status"] != "active":
            raise HTTPException(403, "License key đã bị thu hồi")
        if _check_expired(lic):
            raise HTTPException(403, "License key đã hết hạn")

        existing = db.execute(
            "SELECT 1 FROM activations WHERE license_id = ? AND device_id = ?",
            (lic["id"], req.device_id),
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE activations SET last_validated_at = ? "
                "WHERE license_id = ? AND device_id = ?",
                (_now(), lic["id"], req.device_id),
            )
            db.commit()
            return {
                "status": "activated",
                "product_name": lic["product_name"],
                "expires_at": lic["expires_at"],
            }

        used = db.execute(
            "SELECT COUNT(*) as c FROM activations WHERE license_id = ?", (lic["id"],)
        ).fetchone()["c"]
        if used >= lic["max_activations"]:
            raise HTTPException(403, "Đã đạt giới hạn số lần kích hoạt cho key này")

        db.execute(
            "INSERT INTO activations (license_id, device_id) VALUES (?, ?)",
            (lic["id"], req.device_id),
        )
        db.commit()

    return {
        "status": "activated",
        "product_name": lic["product_name"],
        "expires_at": lic["expires_at"],
    }

@app.post("/api/v1/validate")
def validate(req: ValidateRequest):
    with get_db() as db:
        lic = _get_license(db, req.license_key)
        if not lic:
            return {"valid": False, "reason": "not_found"}
        if lic["status"] != "active":
            return {"valid": False, "reason": "revoked"}
        if _check_expired(lic):
            return {"valid": False, "reason": "expired"}

        activated = db.execute(
            "SELECT 1 FROM activations WHERE license_id = ? AND device_id = ?",
            (lic["id"], req.device_id),
        ).fetchone()
        if not activated:
            return {"valid": False, "reason": "device_not_activated"}

        db.execute(
            "UPDATE activations SET last_validated_at = ? "
            "WHERE license_id = ? AND device_id = ?",
            (_now(), lic["id"], req.device_id),
        )
        db.commit()

    return {"valid": True, "product_name": lic["product_name"], "expires_at": lic["expires_at"]}


# ==================== ADMIN: BACKUP (EXPORT / IMPORT) ====================
@app.get("/admin/export", dependencies=[Depends(require_admin)])
def export_backup():
    """Tải toàn bộ key + activation về file JSON. Backup định kỳ để không bao giờ mất key."""
    with get_db() as db:
        licenses = [dict(r) for r in db.execute("SELECT * FROM licenses ORDER BY id").fetchall()]
        activations = [dict(r) for r in db.execute("SELECT * FROM activations ORDER BY id").fetchall()]
    fname = "licenses-backup-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S") + ".json"
    return JSONResponse(
        content={"exported_at": _now(), "licenses": licenses, "activations": activations},
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


class ImportBackupRequest(BaseModel):
    licenses: list = []
    activations: list = []


@app.post("/admin/import", dependencies=[Depends(require_admin)])
def import_backup_file(req: ImportBackupRequest):
    """Khôi phục từ file backup (key đã tồn tại thì bỏ qua, không ghi đè)."""
    with get_db() as db:
        n_lic, n_act = import_backup(db, {"licenses": req.licenses, "activations": req.activations})
    return {"imported_licenses": n_lic, "imported_activations": n_act}