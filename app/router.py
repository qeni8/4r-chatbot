import re

# 6-haneli atık kodu: 06 01 01 / 060101 / 06.01.01 / 06 01 01*
CODE6 = re.compile(r"(?<!\d)(\d{2})[ .]?(\d{2})[ .]?(\d{2})\*?(?!\d)")
# 2 çift = 4 haneli grup: 06 01 (bitişik "0601" bilinçli olarak hariç — telefon vb. karışmasın)
CODE4 = re.compile(r"(?<!\d)(\d{2})[ .](\d{2})(?!\d)")


def route(mesaj: str) -> str:
    """'atik_kodu' (yapısal tabloya gider) ya da 'rag' (site + model)."""
    if CODE6.search(mesaj):
        return "atik_kodu"
    if CODE4.search(mesaj):
        return "atik_kodu"
    return "rag"
