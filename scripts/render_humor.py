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

def _status_bar(img, d, T, clock):
    fg = T["name"]
    d.text((118, 52), clock, font=F("Inter-SemiBold.otf", 46), fill=fg)
    x = 740
    for i in range(4):  # signal
        h = 14 + i * 9
        d.rounded_rectangle([x + i * 15, 88 - h, x + i * 15 + 9, 88], radius=2, fill=fg if i < 3 else T["sub"])
    d.text((812, 56), "5G", font=F("Inter-SemiBold.otf", 38), fill=fg)
    d.rounded_rectangle([900, 56, 1000, 94], radius=11, fill=fg)  # battery
    d.text((950 - d.textlength("78", font=F("Inter-Bold.otf", 30)) / 2, 58), "78", font=F("Inter-Bold.otf", 30), fill=T["bg"])
    d.rounded_rectangle([1004, 68, 1010, 82], radius=2, fill=T["sub"])

def _tail(d, x0, y0, x1, y1, color, bg, right):
    """iMessage bubble tail at the bottom corner."""
    if right:
        d.ellipse([x1 - 34, y1 - 40, x1 + 10, y1 + 1], fill=color)
        d.ellipse([x1 - 6, y1 - 46, x1 + 40, y1 + 6], fill=bg)
        d.rectangle([x1 - 30, y1 - 22, x1 - 14, y1], fill=color)
    else:
        d.ellipse([x0 - 10, y1 - 40, x0 + 34, y1 + 1], fill=color)
        d.ellipse([x0 - 40, y1 - 46, x0 + 6, y1 + 6], fill=bg)
        d.rectangle([x0 + 14, y1 - 22, x0 + 30, y1], fill=color)

def chat(title, messages, handle, pov=None, theme="dark", stamp=None, H=1920, unread=None):
    """Full-phone iMessage screenshot (default 1080x1920, 9:16). H=1350 gives the 4:5 fallback."""
    T = THEMES[theme]
    speakers = [m["from"] for m in messages if "from" in m]
    pov = pov or max(set(speakers), key=speakers.count)
    img = Image.new("RGB", (W, H), T["bg"]); d = ImageDraw.Draw(img)
    line_c = (60, 60, 64) if theme == "dark" else (210, 210, 214)
    pill = (44, 44, 46) if theme == "dark" else (232, 232, 235)
    HEAD_B, INPUT_T = (370 if H > 1500 else 330), H - (210 if H > 1500 else 175)
    gap_grp = 30 if H > 1500 else 14
    size = 58 if H > 1500 else 50
    for _ in range(40):
        fm = F("Inter-Regular.otf", size); fn = F("Inter-Regular.otf", int(size * 0.5))
        items, total = [], 0
        if stamp:
            items.append(["stamp", stamp, None]); total += size * 2.0
        prev = None
        for i, m in enumerate(messages):
            if "system" in m:
                items.append(["sys", m["system"], None]); total += size * 1.6; prev = None; continue
            mine = m["from"] == pov
            lines = wrap(d, m["text"], fm, 800 if mine else 740)
            bw = max(run_width(d, l, fm) for l in lines) + 56
            bh = len(lines) * size * 1.18 + 30
            first = m["from"] != prev
            nxt = messages[i + 1] if i + 1 < len(messages) else None
            last = not (nxt and "from" in nxt and nxt["from"] == m["from"])
            show_name = first and not mine
            items.append(["msg", m, (lines, bw, bh, show_name, mine, last)])
            total += bh + (size * 0.6 if show_name else 0) + (gap_grp if last else 6)
            prev = m["from"]
        total += 56  # Delivered
        if total <= INPUT_T - HEAD_B - 30: break
        size -= 2
    y = INPUT_T - 24 - total
    last_mine_bottom = None; prev = None
    for kind, m, geo in items:
        if kind == "stamp":
            parts = m.split(" ", 1)
            fb, fr = F("Inter-SemiBold.otf", int(size * 0.5)), F("Inter-Regular.otf", int(size * 0.5))
            if len(parts) == 2:
                w = d.textlength(parts[0] + " ", font=fb) + d.textlength(parts[1], font=fr)
                x = (W - w) / 2
                d.text((x, y + 4), parts[0] + " ", font=fb, fill=T["sub"])
                d.text((x + d.textlength(parts[0] + " ", font=fb), y + 4), parts[1], font=fr, fill=T["sub"])
            else:
                d.text(((W - d.textlength(m, font=fr)) / 2, y + 4), m, font=fr, fill=T["sub"])
            y += size * 2.0; continue
        if kind == "sys":
            fs = F("Inter-Medium.otf", int(size * 0.5))
            d.text(((W - d.textlength(m, font=fs)) / 2, y + 6), m, font=fs, fill=T["sub"]); y += size * 1.6; prev = None; continue
        lines, bw, bh, show_name, mine, last = geo
        if show_name:
            d.text((150, y), m["from"], font=fn, fill=T["sub"]); y += size * 0.6
        if mine:
            x0 = W - 40 - bw; color, tcol = SENT, (255, 255, 255)
        else:
            x0 = 136; color, tcol = T["recv"], T["rtxt"]
        d.rounded_rectangle([x0, y, x0 + bw, y + bh], radius=min(46, bh / 2), fill=color)
        if last:
            _tail(d, x0, y, x0 + bw, y + bh, color, T["bg"], mine)
            if not mine:
                ay = y + bh - 72
                d.ellipse([34, ay, 106, ay + 72], fill=CAST.get(m["from"], (100, 100, 100)))
                fi = F("Inter-SemiBold.otf", 32); t = m["from"][0]
                d.text((70 - d.textlength(t, font=fi) / 2, ay + 14), t, font=fi, fill=(255, 255, 255))
        ty = y + 13
        for ln in lines:
            draw_run(img, d, (x0 + 28, ty), ln, fm, tcol); ty += size * 1.18
        y += bh + (gap_grp if last else 6)
        if mine: last_mine_bottom = y
        prev = m["from"]
    if last_mine_bottom and messages and "from" in messages[-1] and messages[-1]["from"] == pov:
        fd_ = F("Inter-Medium.otf", int(size * 0.46)); t = "Delivered"
        d.text((W - 48 - d.textlength(t, font=fd_), last_mine_bottom - gap_grp + 2), t, font=fd_, fill=T["sub"])
    # ---- header: iOS-style floating pills over a solid fade ----
    d.rectangle([0, 0, W, HEAD_B], fill=T["bg"])
    m_ = re.search(r"\d{1,2}:\d{2}\s?[AP]M", stamp or "")
    clock = (m_.group(0).replace(" ", "")[:-2]) if m_ else "9:41"
    _status_bar(img, d, T, clock)
    cy = 190
    d.rounded_rectangle([44, cy - 50, 252, cy + 50], radius=50, fill=pill)
    d.text((72, cy - 62), "‹", font=F("Inter-Regular.otf", 100), fill=T["name"])
    badge = str(unread if unread else 12)
    d.rounded_rectangle([140, cy - 30, 232, cy + 30], radius=30, fill=(255, 255, 255) if theme == "dark" else (255, 255, 255), outline=line_c if theme != "dark" else None)
    fbk = F("Inter-SemiBold.otf", 36)
    d.text((186 - d.textlength(badge, font=fbk) / 2, cy - 22), badge, font=fbk, fill=(0, 0, 0))
    d.ellipse([934, cy - 50, 1036, cy + 52], fill=pill)  # video button
    d.rounded_rectangle([956, cy - 18, 1000, cy + 18], radius=8, outline=T["name"], width=5)
    d.polygon([(1002, cy - 8), (1018, cy - 18), (1018, cy + 18), (1002, cy + 8)], fill=T["name"])
    gp = group_photo(140); img.paste(gp, (int(W / 2 - 70), 118), gp)
    ft = F("Inter-SemiBold.otf", 42)
    parts = title.split("{bus}"); label = parts[0].strip()
    tw = run_width(d, label, ft) + (58 if len(parts) > 1 else 0) + 40
    px0 = W / 2 - tw / 2 - 28
    d.rounded_rectangle([px0, 276, px0 + tw + 56, 346], radius=35, fill=pill)
    x = px0 + 28
    d.text((x, 284), label, font=ft, fill=T["name"]); x += run_width(d, label, ft) + 10
    if len(parts) > 1:
        ic = bus_icon(50); img.paste(ic, (int(x), 288), ic); x += 58
    d.text((x, 280), "›", font=F("Inter-Regular.otf", 44), fill=T["sub"])
    # ---- input bar ----
    d.rectangle([0, INPUT_T, W, H], fill=T["bg"])
    d.ellipse([28, INPUT_T + 20, 118, INPUT_T + 110], fill=pill)
    d.rectangle([52, INPUT_T + 62, 94, INPUT_T + 68], fill=T["name"]); d.rectangle([70, INPUT_T + 44, 76, INPUT_T + 86], fill=T["name"])
    d.rounded_rectangle([138, INPUT_T + 20, W - 28, INPUT_T + 110], radius=45, outline=line_c, width=3)
    d.text((176, INPUT_T + 38), "iMessage", font=F("Inter-Regular.otf", 44), fill=T["handle"])
    mx = W - 100  # mic
    d.rounded_rectangle([mx, INPUT_T + 38, mx + 24, INPUT_T + 72], radius=12, fill=T["sub"])
    d.arc([mx - 10, INPUT_T + 52, mx + 34, INPUT_T + 90], 0, 180, fill=T["sub"], width=4)
    d.line([mx + 12, INPUT_T + 90, mx + 12, INPUT_T + 98], fill=T["sub"], width=4)
    fh = F("Inter-Medium.otf", 22)
    d.text(((W - d.textlength(handle, font=fh)) / 2, H - 66), handle, font=fh, fill=T["handle"])
    d.rounded_rectangle([W / 2 - 150, H - 30, W / 2 + 150, H - 22], radius=4, fill=T["name"])
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
        h = int(item.get("height") or os.environ.get("CHAT_H") or 1920)
        return [save(chat(item.get("title", "Short Bus Shawties {bus}"), item["messages"], handle,
                          item.get("pov"), theme, item.get("time"), H=h), os.path.join(outdir, "post.jpg"))]
    if fmt == "carousel":  # each slide is its own tweet or chat item
        return [render_post(s, handle, os.path.join(outdir, f"s{i + 1:02d}"), name)[0] for i, s in enumerate(item["slides"])]
    raise ValueError(f"unknown format {fmt}")
