"""ShortbusShawties templates: fake tweet card + group chat screenshot (1080x1350)."""
import os, re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
def F(name, size): return ImageFont.truetype(os.path.join(FONTS, name), size)
EMOJI = os.path.join(FONTS, "NotoColorEmoji.ttf")
EMOJI_RE = re.compile("([\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]+)")

CAST = {  # recurring group chat cast: avatar color
    "Dre": (231, 76, 60), "Nate": (52, 152, 219), "Marco": (46, 174, 96),
    "Benny": (241, 160, 40), "Luis": (155, 89, 182),
}
_ecache = {}
def emoji_img(ch, size):
    key = (ch, size)
    if key not in _ecache:
        f = ImageFont.truetype(EMOJI, 109)
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
        bb = im.getbbox() or (0, 0, 1, 1)
        im = im.crop(bb)
        s = size / max(im.size)
        _ecache[key] = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return _ecache[key]

def tokens(text):
    out = []
    for part in EMOJI_RE.split(text):
        if not part: continue
        if EMOJI_RE.fullmatch(part):
            for ch in re.findall("[\U0001F000-\U0001FAFF☀-➿⬀-⯿](?:️)?", part):
                out.append(("e", ch))
        else:
            out.append(("t", part))
    return out

def run_width(d, text, f):
    w = 0
    for kind, s in tokens(text):
        w += f.size * 1.1 if kind == "e" else d.textlength(s, font=f)
    return w

def draw_run(img, d, xy, text, f, fill):
    x, y = xy
    for kind, s in tokens(text):
        if kind == "e":
            e = emoji_img(s, int(f.size * 1.0))
            img.paste(e, (int(x + f.size * 0.05), int(y + f.size * 0.12)), e)
            x += f.size * 1.1
        else:
            d.text((x, y), s, font=f, fill=fill); x += d.textlength(s, font=f)

def wrap(d, text, f, maxw):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split(" "):
            t = (cur + " " + w).strip()
            if run_width(d, t, f) <= maxw: cur = t
            else:
                if cur: lines.append(cur)
                cur = w
        lines.append(cur)
    return lines

# ---------------- tweet card ----------------
def tweet(text, name, handle, dark=True):
    bg, fg, sub = ((0, 0, 0), (231, 233, 234), (113, 118, 123)) if dark else ((255, 255, 255), (15, 20, 25), (83, 100, 113))
    img = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(img)
    size = 66
    while True:
        f = F("Inter-Regular.otf", size); lines = wrap(d, text, f, W - 160)
        th = len(lines) * size * 1.35
        if th <= 760 or size <= 36: break
        size -= 2
    block = 130 + 40 + th + 80
    y0 = (H - block) / 2
    d.ellipse([80, y0, 200, y0 + 120], fill=(255, 196, 0))
    bus = bus_icon(86); img.paste(bus, (int(140 - bus.width / 2), int(y0 + 60 - bus.height / 2)), bus)
    d.text((225, y0 + 18), name, font=F("Inter-Bold.otf", 42), fill=fg)
    d.text((225, y0 + 70), handle, font=F("Inter-Regular.otf", 36), fill=sub)
    y = y0 + 170
    for ln in lines:
        draw_run(img, d, (80, y), ln, f, fg); y += size * 1.35
    stamp = datetime.now().strftime("%-I:%M %p · %b %-d, %Y")
    d.text((80, y + 30), stamp, font=F("Inter-Regular.otf", 32), fill=sub)
    return img

# ---------------- group chat ----------------
ROOT = os.path.dirname(FONTS)

def bus_icon(size):
    """Hand-drawn yellow school bus (Unicode has no school-bus emoji, only a city bus)."""
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    blk, yel = (30, 30, 30, 255), (255, 196, 0, 255)
    d.rounded_rectangle([S*0.05, S*0.24, S*0.95, S*0.74], radius=S*0.08, fill=yel)
    for i in range(4):
        x0 = S*(0.11 + i*0.17)
        d.rounded_rectangle([x0, S*0.31, x0 + S*0.13, S*0.49], radius=S*0.02, fill=(70, 80, 92, 255))
    d.rounded_rectangle([S*0.79, S*0.31, S*0.90, S*0.49], radius=S*0.02, fill=(70, 80, 92, 255))
    d.rectangle([S*0.05, S*0.56, S*0.95, S*0.60], fill=blk)
    d.rectangle([S*0.90, S*0.64, S*0.95, S*0.70], fill=(255, 250, 200, 255))
    for cx in (0.27, 0.74):
        d.ellipse([S*(cx-0.10), S*0.62, S*(cx+0.10), S*0.82], fill=blk)
        d.ellipse([S*(cx-0.045), S*0.675, S*(cx+0.045), S*0.765], fill=(150, 150, 155, 255))
    return im.resize((size, size), Image.LANCZOS)

def circle_crop(im, size):
    im = im.convert("RGBA"); w, h = im.size; m = min(w, h)
    im = im.crop(((w-m)//2, (h-m)//2, (w-m)//2+m, (h-m)//2+m)).resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size*4, size*4), 0); ImageDraw.Draw(mask).ellipse([0, 0, size*4-1, size*4-1], fill=255)
    im.putalpha(mask.resize((size, size), Image.LANCZOS)); return im

def group_photo(size):
    """Uses assets/group_photo.(png|jpg|jpeg|webp) if present; otherwise a yellow bus placeholder."""
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = os.path.join(ROOT, "assets", "group_photo." + ext)
        if os.path.exists(p):
            return circle_crop(Image.open(p), size)
    bg = Image.new("RGBA", (size, size), (255, 196, 0, 255))
    ic = bus_icon(int(size * 0.8)); bg.paste(ic, (int(size*0.1), int(size*0.1)), ic)
    return circle_crop(bg, size)

THEMES = {
    "dark":  dict(bg=(0, 0, 0), head=(22, 22, 24), name=(255, 255, 255), recv=(38, 38, 41), rtxt=(255, 255, 255), sub=(142, 142, 147), handle=(90, 90, 95)),
    "light": dict(bg=(255, 255, 255), head=(247, 247, 247), name=(0, 0, 0), recv=(233, 233, 235), rtxt=(0, 0, 0), sub=(142, 142, 147), handle=(170, 170, 175)),
}
SENT = (10, 132, 255)

def chat(title, messages, handle, pov=None, theme="dark", stamp=None):
    T = THEMES[theme]
    speakers = [m["from"] for m in messages if "from" in m]
    pov = pov or max(set(speakers), key=speakers.count)
    img = Image.new("RGB", (W, H), T["bg"]); d = ImageDraw.Draw(img)
    # header
    d.rectangle([0, 0, W, 250], fill=T["head"]); d.line([0, 250, W, 250], fill=(60, 60, 64) if theme == "dark" else (210, 210, 214), width=2)
    gp = group_photo(110); img.paste(gp, (int(W/2 - 55), 28), gp)
    ft = F("Inter-SemiBold.otf", 34)
    parts = title.split("{bus}"); label = parts[0].strip()
    tw = run_width(d, label, ft) + (52 if len(parts) > 1 else 0) + 26
    x = (W - tw) / 2
    d.text((x, 154), label, font=ft, fill=T["name"]); x += run_width(d, label, ft) + 10
    if len(parts) > 1:
        ic = bus_icon(44); img.paste(ic, (int(x), 158), ic); x += 52
    d.text((x, 156), "›", font=F("Inter-Regular.otf", 32), fill=T["sub"])
    d.text((36, 96), "‹", font=F("Inter-Regular.otf", 84), fill=SENT)
    # layout
    size = 60
    for _ in range(24):
        fm = F("Inter-Regular.otf", size); fn = F("Inter-Regular.otf", int(size * 0.58))
        items, total, prev = [], 0, None
        if stamp:
            items.append(("sys", stamp, None)); total += size * 1.5
        for m in messages:
            if "system" in m:
                items.append(("sys", m["system"], None)); total += size * 1.5; prev = None; continue
            mine = m["from"] == pov
            maxw = 780 if mine else 720
            lines = wrap(d, m["text"], fm, maxw)
            bw = max(run_width(d, l, fm) for l in lines) + 56
            bh = len(lines) * size * 1.2 + 28
            show_name = (not mine) and m["from"] != prev
            items.append(("msg", m, (lines, bw, bh, show_name, mine)))
            total += bh + (size * 0.62 if show_name else 0) + 9
            prev = m["from"]
        if total <= H - 340: break
        size -= 3
    y = 280 + max(0, (H - 360 - total)) * 0.25
    for kind, m, geo in items:
        if kind == "sys":
            fs = F("Inter-Medium.otf", int(size * 0.55))
            d.text(((W - d.textlength(m, font=fs)) / 2, y + size * 0.2), m, font=fs, fill=T["sub"]); y += size * 1.5; continue
        lines, bw, bh, show_name, mine = geo
        if show_name:
            d.text((150, y), m["from"], font=fn, fill=T["sub"]); y += size * 0.62
        if mine:
            x0 = W - 44 - bw; color, tcol = SENT, (255, 255, 255)
        else:
            x0 = 136; color, tcol = T["recv"], T["rtxt"]
            ay = y + bh - 72
            d.ellipse([40, ay, 112, ay + 72], fill=CAST.get(m["from"], (100, 100, 100)))
            fi = F("Inter-SemiBold.otf", 32); t = m["from"][0]
            d.text((76 - d.textlength(t, font=fi) / 2, ay + 14), t, font=fi, fill=(255, 255, 255))
        d.rounded_rectangle([x0, y, x0 + bw, y + bh], radius=min(46, bh / 2), fill=color)
        ty = y + 14
        for ln in lines:
            draw_run(img, d, (x0 + 28, ty), ln, fm, tcol); ty += size * 1.2
        y += bh + 9
    fh = F("Inter-Medium.otf", 28)
    d.text(((W - d.textlength(handle, font=fh)) / 2, H - 70), handle, font=fh, fill=T["handle"])
    chat.last_size = size
    return img

def save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.convert("RGB").save(path, "JPEG", quality=92); return path

def render_post(item, handle, outdir, name="ShortbusShawties"):
    fmt = item.get("format")
    if fmt == "tweet":
        return [save(tweet(item["text"], name, handle, item.get("dark", True)), os.path.join(outdir, "post.jpg"))]
    if fmt == "chat":
        theme = item.get("theme") or ("light" if datetime.now().toordinal() % 2 else "dark")
        return [save(chat(item.get("title", "Short Bus Shawties {bus}"), item["messages"], handle,
                          item.get("pov"), theme, item.get("time")), os.path.join(outdir, "post.jpg"))]
    if fmt == "carousel":  # each slide is its own tweet or chat item
        return [render_post(s, handle, os.path.join(outdir, f"s{i + 1:02d}"), name)[0] for i, s in enumerate(item["slides"])]
    raise ValueError(f"unknown format {fmt}")
