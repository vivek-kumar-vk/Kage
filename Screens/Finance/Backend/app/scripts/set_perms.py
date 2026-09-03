import os
import subprocess
from services.db import DB_PATH


def set_perms():
    if not DB_PATH.exists():
        print(f"Notice: {DB_PATH} does not exist yet.")
        return 0

    if os.name == "nt":
        subprocess.run(['icacls', str(DB_PATH), '/inheritance:r', '/grant:r', f"{os.environ.get('USERNAME','%USERNAME%')}:F"])
        print(f"Set permissions for {DB_PATH} on Windows.")
    else:
        os.chmod(DB_PATH, 0o600)
        print(f"Set permissions for {DB_PATH} on POSIX.")

    return 0


if __name__ == "__main__":
    set_perms()
