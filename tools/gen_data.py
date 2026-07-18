import json
import os
import sys

src = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\musta\tt\book_data2.json"
outdir = r"C:\Users\musta\tt\whale-book"
os.makedirs(outdir, exist_ok=True)

d = json.load(open(src, encoding="utf-8"))

quotes = ('"', '“', '”', '«', '»')


def is_title(t):
    t = t.strip()
    return 3 < len(t) < 45 and t.startswith(quotes) and t.endswith(quotes)


toc = []
for p in d:
    for x in p["paras"]:
        if is_title(x):
            toc.append({"page": p["page"], "title": x.strip().strip('"“”«»').strip()})

book = {
    "title": "عندما تطير الحيتان",
    "author": "أسامة ياسر لافي",
    "pages": [p["paras"] for p in d],
    "toc": toc,
}

with open(os.path.join(outdir, "book-data.js"), "w", encoding="utf-8") as f:
    f.write("window.BOOK_DATA = ")
    json.dump(book, f, ensure_ascii=False)
    f.write(";\n")

print("written:", os.path.join(outdir, "book-data.js"),
      os.path.getsize(os.path.join(outdir, "book-data.js")) // 1024, "KB")
print("toc entries:", len(toc))
