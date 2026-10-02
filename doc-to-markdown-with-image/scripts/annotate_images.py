#!/usr/bin/env python3
"""把群組示意圖的圖內文字繪回抽出圖檔（覆蓋原檔、一律存 PNG）。

用法（由 merge_md_images.py 呼叫，不獨立使用）:
    annotate(path, group) -> 新檔名或 None

座標系：group['pic'] 與每個 box 都是群組座標（EMU）；以底圖寬度換算像素。
近似原則（見 docs/adr/0005）：位置、字級、顏色、對齊、直排盡量還原，
不追求 Word 精確換行。繪製失敗或找不到字型時回 None，由呼叫端保留原檔。

字型：平台常見 CJK 字型偵測（Windows 微軟正黑／雅黑、macOS PingFang、
Linux Noto Sans CJK／文泉驛／Droid 後備）；可用環境變數 DOC2MD_FONT／
DOC2MD_FONT_BOLD 覆寫，值為字型檔路徑，TTC 可加 '#' 加索引（如 'x.ttc#3'）。

依賴 Pillow（本 skill 的必要依賴，見 docs/adr/0005-doc2md-pillow-annotated-images.md）。
"""
import os
import re
import sys
from math import ceil
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    _IMPORT_ERROR = None
except ImportError as exc:  # 缺 Pillow 時由呼叫端給安裝指引，不在 import 期崩潰
    Image = ImageDraw = ImageFont = None
    _IMPORT_ERROR = exc

_EMU_PER_PT = 12700  # 1 pt = 12700 EMU
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’._\-]*|.", re.S)

_specs = None          # {'regular': (Path, index) | None, 'bold': ...}
_fonts = {}            # (bold, size_px) -> ImageFont | None
_warned_no_font = False


def available() -> bool:
    """Pillow 是否可用。"""
    return Image is not None


def annotate(image_path: str, group: dict):
    """把 group 的文字方塊繪到 image_path 上；成功回新檔名（basename），失敗回 None。"""
    if Image is None:
        return None
    _ensure_specs()
    if _specs.get('regular') is None:
        _warn_no_font()
        return None

    try:
        base = Image.open(image_path)
        base.load()
    except Exception as exc:
        print(f'警告: 無法讀取圖檔，跳過標注: {image_path}（{exc}）', file=sys.stderr)
        return None

    pic = group['pic']
    if pic[2] <= 0 or pic[3] <= 0:
        return None
    scale = base.size[0] / pic[2]  # EMU → 像素（等比）
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    drawn = 0
    for box in group['boxes']:
        try:
            placed = _render_box(box, pic, scale)
        except Exception as exc:  # 單一方塊壞掉不拖垮整張圖
            print(f'警告: 文字方塊繪製失敗，已略過: {image_path}（{exc}）',
                  file=sys.stderr)
            continue
        if placed is None:
            continue
        tile, (x, y) = placed
        layer.alpha_composite(tile, dest=(round(x), round(y)))
        drawn += 1
    if not drawn:
        print(f'警告: 沒有可繪製的文字方塊，保留原圖: {image_path}', file=sys.stderr)
        return None

    out = Image.alpha_composite(base.convert('RGBA'), layer)
    out = out.convert('RGBA') if 'A' in base.getbands() else out.convert('RGB')
    target = os.path.splitext(image_path)[0] + '.png'
    tmp = f'{target}.tmp{os.getpid()}'
    try:
        out.save(tmp, format='PNG')
        os.replace(tmp, target)
    except Exception as exc:
        print(f'警告: 標注圖存檔失敗，保留原圖: {image_path}（{exc}）', file=sys.stderr)
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None
    return os.path.basename(target)


# ---------- 繪製 ----------

def _render_box(box, pic, scale):
    """繪製單一文字方塊；回傳 (tile, 貼上座標)。

    方塊是縮放的最小框：內容照 Word 行為溢出可見（noAutofit 不裁切），
    tile 依實際內容擴張，貼上位置可能超出方塊範圍。
    """
    w = max(1, round(box['w'] * scale))
    h = max(1, round(box['h'] * scale))
    ins = tuple(v * scale for v in box['insets'])
    px_per_pt = scale * _EMU_PER_PT
    if box['vert'] == 'eaVert':
        tile = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        _draw_vertical(ImageDraw.Draw(tile), box, w, h, ins, px_per_pt)
        dx, dy = 0.0, 0.0
    else:
        tile, dx, dy = _render_horizontal(box, w, h, ins, px_per_pt)

    cx = (box['x'] - pic[0]) * scale + dx + tile.width / 2
    cy = (box['y'] - pic[1]) * scale + dy + tile.height / 2
    if box['rot']:
        tile = tile.rotate(-box['rot'], expand=True, resample=Image.BICUBIC)
    return tile, (cx - tile.width / 2, cy - tile.height / 2)


def _render_horizontal(box, w, h, ins, px_per_pt):
    """水平排版；回傳 (tile, dx, dy)，dx/dy 為相對方塊左上角的貼上位移。"""
    avail_w = max(1.0, w - ins[0] - ins[2])
    lines = []
    for para in box['paras']:
        lines.extend(_para_lines(para, avail_w, box['wrap'], px_per_pt))
    heights = [max(1.0, _line_height(line['frags'], line['para'], px_per_pt))
               for line in lines]
    total = sum(heights)
    if box['anchor'] == 'ctr':
        y0 = (h - total) / 2
    elif box['anchor'] == 'b':
        y0 = h - ins[3] - total
    else:
        y0 = ins[1]

    ys, xs = [], []
    top, bottom = min(0.0, y0), max(h, y0 + total)
    left, right = 0.0, float(w)
    for line, line_h in zip(lines, heights):
        frags = line['frags']
        line_w = sum(font.getlength(text) for text, font, _c, _s in frags)
        jc = line['para']['jc']
        if jc == 'center':
            x = (w - line_w) / 2
        elif jc == 'right':
            x = w - ins[2] - line_w
        else:
            x = ins[0]
        xs.append(x)
        ys.append(y0)
        left, right = min(left, x), max(right, x + line_w)
        y0 += line_h
    pad = max(2.0, 0.2 * max((f[3] for line in lines for f in line['frags']),
                             default=px_per_pt * 12))
    left, right = left - pad, right + pad
    top, bottom = top - pad, bottom + pad
    tile = Image.new('RGBA', (max(1, ceil(right - left)), max(1, ceil(bottom - top))),
                     (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    for line, _lh, x, y in zip(lines, heights, xs, ys):
        for text, font, color, _size in line['frags']:
            draw.text((x - left, y - top), text, font=font, fill=color + (255,))
            x += font.getlength(text)
    return tile, left, top


def _para_lines(para, avail_w, wrap, px_per_pt):
    """把段落切成行；回傳 [{'frags': [(text, font, color, size_px)], 'para': para}]。"""
    out = []
    cur = []

    def cur_width():
        return sum(font.getlength(text) for text, font, _c, _s in cur)

    for run in para['runs']:
        if run.get('br'):
            out.append(cur)
            cur = []
            continue
        text = (run.get('text') or '').replace('\t', '    ')
        if not text:
            continue
        size_px = run['size'] * px_per_pt
        font = _font(size_px, run['bold'])
        color = run['color'] or (0, 0, 0)
        for token in _TOKEN.findall(text):
            token_w = font.getlength(token)
            if wrap != 'none' and cur and cur_width() + token_w > avail_w:
                out.append(cur)
                cur = []
            cur.append((token, font, color, size_px))
    out.append(cur)
    return [{'frags': frags, 'para': para} for frags in out]


def _line_height(frags, para, px_per_pt):
    natural = max((size for _t, _f, _c, size in frags), default=12.0 * px_per_pt) * 1.25
    if para.get('line'):
        specified = para['line'] * px_per_pt
        if para.get('line_rule') == 'exact':
            return specified
        return max(natural, specified)
    return natural


def _draw_vertical(draw, box, w, h, ins, px_per_pt):
    """直排（eaVert）：文字由上而下、欄由右而左；字型保持正立。"""
    bottom = h - ins[3]
    x_right = w - ins[2]
    y = ins[1]
    col_w = None
    for para in box['paras']:
        for run in para['runs']:
            if run.get('br'):
                if col_w:
                    x_right -= col_w
                col_w = None
                y = ins[1]
                continue
            text = run.get('text') or ''
            if not text:
                continue
            size_px = run['size'] * px_per_pt
            font = _font(size_px, run['bold'])
            color = run['color'] or (0, 0, 0)
            for char in text:
                if col_w is None:
                    col_w = size_px * 1.25
                if y + size_px > bottom and y > ins[1]:
                    x_right -= col_w
                    col_w = size_px * 1.25
                    y = ins[1]
                char_w = font.getlength(char)
                draw.text((x_right - col_w + (col_w - char_w) / 2, y),
                          char, font=font, fill=color + (255,))
                y += size_px * 1.05


# ---------- 字型 ----------

def _ensure_specs() -> None:
    global _specs
    if _specs is not None:
        return
    _specs = {}
    candidates = _candidate_paths()
    for kind in ('regular', 'bold'):
        env = os.environ.get('DOC2MD_FONT_BOLD' if kind == 'bold' else 'DOC2MD_FONT',
                             '').strip()
        spec = None
        if env:
            path, _, index = env.partition('#')
            spec = _make_spec(path, int(index) if index.isdigit() else None)
        else:
            for path in candidates[kind]:
                spec = _make_spec(path)
                if spec is not None:
                    break
        _specs[kind] = spec


def _make_spec(path, index=None):
    p = Path(path)
    if not p.is_file():
        return None
    if index is None:
        index = _ttc_index(p)
    try:
        ImageFont.truetype(str(p), size=12, index=index)
    except Exception:
        return None
    return (p, index)


def _ttc_index(path: Path) -> int:
    """TTC 內挑繁體（TC／Traditional／正黑）子字型，找不到用 0。"""
    for i in range(10):
        try:
            font = ImageFont.truetype(str(path), size=12, index=i)
        except Exception:
            break
        try:
            name = (font.getname()[0] or '').lower()
        except Exception:
            name = ''
        if any(k in name for k in ('tc', 'traditional', 'jhenghei', '正黑')):
            return i
    return 0


def _candidate_paths() -> dict:
    win = Path(os.environ.get('WINDIR', r'C:\Windows'))
    mac = Path('/System/Library/Fonts')
    linux = Path('/usr/share/fonts')
    regular = [
        win / 'Fonts' / 'msjh.ttc',           # 微軟正黑（繁）
        win / 'Fonts' / 'msyh.ttc',           # 微軟雅黑（簡）
        win / 'Fonts' / 'mingliu.ttc',        # 新細明體（繁）
        mac / 'PingFang.ttc',
        mac / 'STHeiti Light.ttc',
        linux / 'opentype' / 'noto' / 'NotoSansCJK-Regular.ttc',
        linux / 'opentype' / 'noto' / 'NotoSansCJKtc-Regular.otf',
        linux / 'truetype' / 'wqy' / 'wqy-zenhei.ttc',
        linux / 'truetype' / 'droid' / 'DroidSansFallbackFull.ttf',
    ]
    bold = [
        win / 'Fonts' / 'msjhbd.ttc',
        win / 'Fonts' / 'msyhbd.ttc',
        mac / 'STHeiti Medium.ttc',
        linux / 'opentype' / 'noto' / 'NotoSansCJK-Bold.ttc',
        linux / 'opentype' / 'noto' / 'NotoSansCJKtc-Bold.otf',
    ]
    if linux.is_dir():  # 各發行版檔名不一，補一輪 glob
        try:
            regular += sorted(linux.rglob('NotoSansCJK*Regular*.ttc'))
            regular += sorted(linux.rglob('NotoSansCJKtc-*.otf'))
            regular += sorted(linux.rglob('NotoSerifCJK*Regular*.ttc'))
            bold += sorted(linux.rglob('NotoSansCJK*Bold*.ttc'))
        except OSError:
            pass
    return {'regular': _dedupe(regular), 'bold': _dedupe(bold)}


def _dedupe(paths):
    seen, out = set(), []
    for p in paths:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _font(size_px: float, bold: bool):
    _ensure_specs()
    size = max(1, int(round(size_px)))
    key = (bold, size)
    if key in _fonts:
        return _fonts[key]
    spec = _specs.get('bold' if bold else 'regular')
    if spec is None and bold:
        spec = _specs.get('regular')
    font = None
    if spec is not None:
        try:
            font = ImageFont.truetype(str(spec[0]), size=size, index=spec[1])
        except Exception:
            font = None
    _fonts[key] = font
    return font


def _warn_no_font() -> None:
    global _warned_no_font
    if not _warned_no_font:
        _warned_no_font = True
        print('警告: 找不到可用的 CJK 字型（可用 DOC2MD_FONT 指定字型檔），'
              '跳過圖片標注；圖內文字仍保留在 md', file=sys.stderr)


if _IMPORT_ERROR is not None:  # pragma: no cover - 供除錯用
    _ = _IMPORT_ERROR
