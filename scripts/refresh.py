"""İçerik havuzunu baştan tazeler: site çek → parçala → embed.

Site içeriği değiştiğinde çalıştırılır (yayında zamanlı görev olarak da kurulabilir).

Kullanım:
    python scripts/refresh.py
"""

import os
import subprocess
import sys

ADIMLAR = [
    ("Site çekiliyor", "scripts/fetch_site.py"),
    ("Parçalanıyor", "scripts/chunk_site.py"),
    ("Embed ediliyor", "scripts/embed_chunks.py"),
]


def main() -> None:
    env = {**os.environ, "PYTHONPATH": "."}
    for baslik, script in ADIMLAR:
        print(f"\n=== {baslik} ({script}) ===")
        subprocess.run([sys.executable, script], check=True, env=env)
    print("\nTazeleme tamam.")


if __name__ == "__main__":
    main()
