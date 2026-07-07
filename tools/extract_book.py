# -*- coding: utf-8 -*-
"""
Full visual reconstruction of Arabic text from whales.pdf.

The PDF stores characters in an unreliable stream order (bidi visual leakage,
decomposed ligatures, scrambled runs on some pages) but glyph geometry is
always correct. So per line we:
  1. pair decomposed ligatures (zero-width letter + full-width letter sharing a box)
  2. glue combining marks to their base (stream-adjacent, same left edge)
  3. sort clusters by x geometry (desc for RTL lines, asc for LTR lines)
  4. reverse embedded opposite-direction runs (with mirrored bracket absorption)
  5. re-insert lost inter-word spaces from gap analysis, collapse duplicates
Then merge justified lines into paragraphs using left-margin reach.
"""
import fitz
import json
import re

DOC = r"C:\Users\musta\tt\whales.pdf"
OUT = r"C:\Users\musta\tt\book_data.json"

COMBINING = set(range(0x0610, 0x061B)) | set(range(0x064B, 0x0660)) | {0x0670} | \
    set(range(0x06D6, 0x06DD)) | set(range(0x06DF, 0x06E9)) | set(range(0x06EA, 0x06EE))

MIRROR_OPEN = {"(": ")", "[": "]", "{": "}", "«": "»", "“": "”", "‘": "’"}
MIRROR_CLOSE = {v: k for k, v in MIRROR_OPEN.items()}


def is_mark(c):
    return ord(c) in COMBINING


def is_arabic_letter(c):
    o = ord(c)
    if o in COMBINING:
        return False
    return 0x0620 <= o <= 0x064A or o in (0x0640, 0x0671, 0x067E, 0x0686, 0x06AF, 0x06A9)


def is_ltr_strong(c):
    return c.isascii() and c.isalnum()


def line_direction(chars):
    ar = sum(1 for ch in chars if is_arabic_letter(ch["c"]))
    lt = sum(1 for ch in chars if is_ltr_strong(ch["c"]))
    return "ltr" if lt > ar else "rtl"


def pair_ligatures(chars, stats):
    """Collapsed multi-letter ligatures (seen with "لا"/"لله"/"الله" and
    friends) show up as a run of zero-width letters glued to ONE full-width
    "anchor" letter that shares their box -- but the anchor can come either
    LAST in the stream (common case: reverse the whole run so the anchor
    leads) or FIRST (mirror case: the trailing zero-width letters are
    already in correct reading order, they just need to be merged onto the
    anchor so the geometric sort below doesn't scatter them). Whichever
    happens, the whole cluster must be emitted as ONE atomic entry at the
    anchor's real box -- emitting members separately lets the later
    sort-by-center step re-shuffle them independently, since only the
    anchor has a genuine x-position.
    """
    out = []
    i = 0
    n = len(chars)
    while i < n:
        ch = chars[i]
        w = ch["x1"] - ch["x0"]

        # anchor-last: zero-width run, then the full-width glyph
        if w < 0.05 and is_arabic_letter(ch["c"]):
            j = i
            while j < n:
                cw = chars[j]["x1"] - chars[j]["x0"]
                if cw < 0.05 and is_arabic_letter(chars[j]["c"]):
                    j += 1
                else:
                    break
            if j < n:
                anchor = chars[j]
                aw = anchor["x1"] - anchor["x0"]
                if aw > 0.5 and is_arabic_letter(anchor["c"]) and abs(anchor["x1"] - ch["x0"]) < 1.5:
                    cluster = chars[i:j + 1]
                    text = "".join(c["c"] for c in reversed(cluster))
                    out.append({"text": text, "x0": anchor["x0"], "x1": anchor["x1"]})
                    stats["lig"] += len(cluster) - 1
                    i = j + 1
                    continue

        # anchor-first: full-width glyph, then a zero-width run glued to its
        # trailing edge (already in correct reading order -- no reversal)
        if w > 0.5 and is_arabic_letter(ch["c"]) and i + 1 < n:
            j = i + 1
            while j < n:
                cw = chars[j]["x1"] - chars[j]["x0"]
                if cw < 0.05 and is_arabic_letter(chars[j]["c"]) and abs(chars[j]["x1"] - ch["x1"]) < 1.5:
                    j += 1
                else:
                    break
            if j > i + 1:
                cluster = chars[i:j]
                text = "".join(c["c"] for c in cluster)
                out.append({"text": text, "x0": ch["x0"], "x1": ch["x1"]})
                stats["lig"] += len(cluster) - 1
                i = j
                continue

        out.append({"text": ch["c"], "x0": ch["x0"], "x1": ch["x1"]})
        i += 1
    return out


def glue_marks(clusters):
    """Combining marks glue to previous stream cluster when sitting on its box; else stay orphan."""
    out = []
    for cl in clusters:
        c0 = cl["text"][0]
        if out and is_mark(c0) and len(cl["text"]) == len(cl["text"]):
            prev = out[-1]
            if not is_mark(prev["text"][0]) and prev["x0"] - 1.0 <= cl["x0"] <= prev["x1"] + 1.0:
                prev["text"] += cl["text"]
                continue
        out.append(cl)
    return out


def center(cl):
    return (cl["x0"] + cl["x1"]) / 2.0


def strong_class(cl):
    c = cl["text"][0]
    if is_arabic_letter(c) or is_mark(c):
        return "R"
    if is_ltr_strong(c):
        return "L"
    return "N"


def reverse_embedded_runs(clusters, line_dir):
    """After visual sort, embedded opposite-direction runs read reversed; restore them."""
    opp = "L" if line_dir == "rtl" else "R"
    n = len(clusters)
    out = list(clusters)
    i = 0
    while i < n:
        if strong_class(out[i]) == opp:
            j = i
            k = i
            # extend over opp-strong and neutrals sandwiched between opp-strongs
            while k + 1 < n:
                nc = strong_class(out[k + 1])
                if nc == opp:
                    k += 1
                elif nc == "N":
                    m = k + 1
                    while m < n and strong_class(out[m]) == "N" and not out[m]["text"].isspace():
                        m += 1
                    if m < n and strong_class(out[m]) == opp:
                        k = m
                    else:
                        break
                else:
                    break
            # absorb mirrored bracket pair hugging the run
            if j > 0 and k + 1 < n:
                a, b = out[j - 1]["text"], out[k + 1]["text"]
                if line_dir == "rtl" and b in MIRROR_OPEN and MIRROR_OPEN[b] == a:
                    j -= 1
                    k += 1
            out[j:k + 1] = out[j:k + 1][::-1]
            i = k + 1
        else:
            i += 1
    return out


def row_text(chars, stats):
    """chars: stream-ordered char dicts of ONE visual row."""
    if not chars:
        return "", None
    fonts = {ch["font"] for ch in chars if not ch["c"].isspace()}
    if fonts and fonts <= {"Wingdings"}:
        return "", "sep"

    direction = line_direction(chars)
    clusters = pair_ligatures(chars, stats)
    clusters = glue_marks(clusters)

    spaces = [cl for cl in clusters if cl["text"].isspace()]
    solid = [cl for cl in clusters if not cl["text"].isspace()]
    solid.sort(key=center, reverse=(direction == "rtl"))

    # merge orphan marks into the cluster before them (post-sort)
    merged = []
    for cl in solid:
        if merged and is_mark(cl["text"][0]):
            merged[-1]["text"] += cl["text"]
        else:
            merged.append(cl)
    solid = merged

    solid = reverse_embedded_runs(solid, direction)

    # rebuild with spaces from gap analysis between consecutive solids
    parts = []
    for idx, cl in enumerate(solid):
        parts.append(cl["text"])
        if idx + 1 < len(solid):
            nxt = solid[idx + 1]
            if direction == "rtl":
                gap_lo, gap_hi = nxt["x1"], cl["x0"]
            else:
                gap_lo, gap_hi = cl["x1"], nxt["x0"]
            gap = gap_hi - gap_lo
            if gap > 1.8:
                parts.append(" ")
            elif gap > 0:
                # An explicit space char only belongs in THIS gap if its own
                # box actually fits inside it. Justified lines sometimes place
                # a stray space glyph so its box overlaps into the gap between
                # two letters of the SAME word (e.g. inside "كانت") even
                # though it visually/semantically belongs to a different,
                # larger gap elsewhere on the line; matching by center alone
                # (as before) wrongly split those words. Containment with a
                # small tolerance avoids that misattribution.
                tol = 0.6
                if any(sp["x0"] >= gap_lo - tol and sp["x1"] <= gap_hi + tol for sp in spaces):
                    parts.append(" ")
    txt = "".join(parts)
    txt = " ".join(txt.split())
    txt = txt.replace("هللا", "الله").replace("اهلل", "الله").replace("ش يء", "شيء")
    txt = clean(txt)
    return txt, None


ALEF_FORMS = "اأإآ"


def clean(txt):
    # space before a combining mark is always an artifact of stretched justification
    txt = re.sub(r" +(?=[ً-ْٰ])", "", txt)
    # a mark stranded after punctuation belongs on the letter before it
    txt = re.sub(r"([!؟.،؛…]+)([ً-ْٰ]+)", r"\2\1", txt)
    # standalone alef-form joins the following word (never a valid standalone word)
    txt = re.sub(rf"(^| )([{ALEF_FORMS}]) (?=\S)", r"\1\2", txt)
    # standalone waw is the conjunction, always written attached to the next word
    txt = re.sub(r"(^| )و (?=\S)", r"\1و", txt)
    # a lone possessive ya joins the word before it (justification gap artifact)
    txt = re.sub(r"(?<=\S) ي(?![ء-ٰ])", "ي", txt)
    # alef maksura / final hamza-ya are final-only forms with generous side
    # bearings in this font; justification sometimes stretches a real space
    # glyph right before them even though they belong to the previous word
    # (e.g. "مرض ى" -> "مرضى", "مش ى" -> "مشى") -- never valid standalone words
    txt = re.sub(r"(?<=\S) ([ىئ])(?=\s|$|[.,!؟،؛:])", r"\1", txt)
    # same justification artifact, word-specific: "سيء" (bad) repeatedly
    # splits as a lone "س" + stretched space + "يء"
    txt = re.sub(r"(?<=\S) س يء(?=\s|$|[.,!؟،؛:])", r" سيء", txt)
    # one-off upstream PDF defect (page 22): the tha glyph in "متلبثًا" is
    # physically mis-positioned two slots later than it belongs, geometry
    # alone can't distinguish this from a real word boundary
    txt = txt.replace("م لبتث", "متلبثًا")
    return txt


def main():
    doc = fitz.open(DOC)
    stats = {"lig": 0}
    pages = []

    raw_pages = []
    for pno, page in enumerate(doc):
        d = page.get_text("rawdict")
        # collect every char on the page in stream order
        allchars = []
        for block in d["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    prev = None
                    for ch in span["chars"]:
                        rec = {"c": ch["c"], "x0": ch["bbox"][0], "x1": ch["bbox"][2],
                               "y0": ch["bbox"][1], "y1": ch["bbox"][3],
                               "font": span["font"], "row": None}
                        # marks inherit the row of their in-stream base
                        if (is_mark(ch["c"]) and prev is not None
                                and prev["x0"] - 1.0 <= rec["x0"] <= prev["x1"] + 1.0):
                            rec["inherit"] = prev
                        allchars.append(rec)
                        prev = rec

        # cluster baselines of solid chars into rows
        base_ys = sorted(ch["y1"] for ch in allchars
                         if not ch["c"].isspace() and not is_mark(ch["c"]))
        rows = []
        for y in base_ys:
            if rows and y - rows[-1][-1] <= 5.0:
                rows[-1].append(y)
            else:
                rows.append([y])
        centers = [sum(r) / len(r) for r in rows]

        def nearest_row(y):
            return min(range(len(centers)), key=lambda i: abs(centers[i] - y)) if centers else 0

        buckets = [[] for _ in centers] or [[]]
        for ch in allchars:
            if "inherit" in ch:
                ch["row"] = ch["inherit"]["row"]
            else:
                ri = nearest_row(ch["y1"])
                # spaces from empty spacer lines have no real row: drop them
                if ch["c"].isspace() and centers and abs(centers[ri] - ch["y1"]) > 10:
                    continue
                ch["row"] = ri
            buckets[ch["row"]].append(ch)

        lines = []
        for ri, bucket in enumerate(buckets):
            t, kind = row_text(bucket, stats)
            solids = [c for c in bucket if not c["c"].isspace()]
            if not solids:
                continue
            x0 = min(c["x0"] for c in solids)
            y = centers[ri] if centers else 0
            if kind == "sep":
                lines.append({"y": y, "x0": x0, "text": "", "sep": True})
            elif t and not t.strip().isdigit():
                lines.append({"y": y, "x0": x0, "text": t, "sep": False})
        lines.sort(key=lambda v: v["y"])
        raw_pages.append(lines)

    for pno, lines in enumerate(raw_pages):
        margins = [ln["x0"] for ln in lines if not ln["sep"]]
        left = min(margins) if margins else 85.0
        paras = []
        buf = ""
        for ln in lines:
            if ln["sep"]:
                if buf:
                    paras.append(clean(buf))
                    buf = ""
                paras.append("---")
                continue
            buf = (buf + " " + ln["text"]).strip() if buf else ln["text"]
            reaches_left = ln["x0"] <= left + 18
            # an orphan alef at line end always continues into the next line
            ends_orphan = re.search(rf"(^| )[{ALEF_FORMS}]$", buf)
            if not reaches_left and not ends_orphan:
                paras.append(clean(buf))
                buf = ""
        if buf:
            paras.append(clean(buf))
        pages.append({"page": pno + 1, "paras": paras})

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=1)

    print("pages:", len(pages))
    print("ligature pairs:", stats["lig"])
    total = sum(len(p["paras"]) for p in pages)
    print("total paragraphs:", total)


if __name__ == "__main__":
    main()
