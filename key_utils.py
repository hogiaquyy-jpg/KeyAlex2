import secrets
import string

# Bỏ các ký tự dễ nhầm lẫn: 0/O, 1/I/L
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
GROUP_LEN = 5
GROUPS = 4


def generate_license_key(prefix: str = "") -> str:
    """Sinh key dạng AAAAA-BBBBB-CCCCC-DDDDD (có thể thêm prefix, vd 'PRO')."""
    groups = []
    for _ in range(GROUPS):
        group = "".join(secrets.choice(ALPHABET) for _ in range(GROUP_LEN))
        groups.append(group)
    key = "-".join(groups)
    if prefix:
        key = f"{prefix.upper()}-{key}"
    return key
