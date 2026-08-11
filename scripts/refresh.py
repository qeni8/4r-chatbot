"""Site içeriğini tazeler (çek + temizle → data/site/*.md).

Parçalama/embedding adımı yok: korpus küçük olduğu için tamamı doğrudan modele veriliyor
(bkz. app/knowledge.py). Site içeriği değiştiğinde çalıştırılır.

Kullanım:
    python scripts/refresh.py
"""

import os
import subprocess
import sys


def main() -> None:
    env = {**os.environ, "PYTHONPATH": "."}
    subprocess.run([sys.executable, "scripts/fetch_site.py"], check=True, env=env)
    print("\nTazeleme tamam. Uygulamayı yeniden başlatın (içerik açılışta belleğe alınır).")


if __name__ == "__main__":
    main()
