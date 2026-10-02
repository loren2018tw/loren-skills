#!/usr/bin/env python3
"""doc-to-markdown-with-image 共用 docx XML 解析：圖片引用與群組示意圖文字方塊。

只用 Python 標準庫。座標一律以 EMU 表示；群組座標已用
chOff/chExt → off/ext 正規化，可直接與同群組底圖的 off/ext 相減換算像素。
"""
import re
import xml.etree.ElementTree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PIC = 'http://schemas.openxmlformats.org/drawingml/2006/picture'
WPG = 'http://schemas.microsoft.com/office/word/2010/wordprocessingGroup'
WPS = 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape'
MC = 'http://schemas.openxmlformats.org/markup-compatibility/2006'

_DEFAULT_PT = 12.0


def image_refs(xml: str, rmap: dict) -> list:
    """回傳 body 順序的 [(rId, media/xxx)]。

    只掃 mc:Choice 分支、跳過 mc:Fallback（同一張圖在兩個分支各引用一次，
    只算一次）；rmap 之外的 rId（非圖片關聯）忽略。
    """
    pairs = []
    i = 0
    while i < len(xml):
        fb = xml.find('<mc:Fallback>', i)
        seg_end = fb if fb != -1 else len(xml)
        for m in re.finditer(r'(?:r:embed|r:id)="(rId\d+)"', xml[i:seg_end]):
            rid = m.group(1)
            if rid in rmap:
                pairs.append((rid, rmap[rid]))
        if fb == -1:
            break
        end = xml.find('</mc:Fallback>', fb)
        i = end + len('</mc:Fallback>') if end != -1 else len(xml)
    return pairs


def group_text_boxes(xml: str) -> tuple:
    """解析群組示意圖的文字方塊。

    回傳 ({底圖 rId: {'pic': (x, y, w, h), 'boxes': [box, ...]}}, stats)：
      - 只處理 mc:Choice 內、恰好含一張底圖且有文字方塊的 wpg:wgp 群組；
      - box 描述字型、顏色、對齊、直排、旋轉與段落，座標為群組座標（EMU）；
      - stats['skipped'] 為無法標注的文字方塊數（群組無底圖、多底圖、
        旋轉不支援，以及群組外的獨立文字方塊）。
    """
    root = ET.fromstring(xml.encode('utf-8'))
    default_pt = _default_size(root)
    result = {}
    stats = {'skipped': 0}
    for drawing in _iter_drawings(root):
        groups = list(drawing.iter(f'{{{WPG}}}wgp'))
        if not groups:
            stats['skipped'] += len(list(drawing.iter(f'{{{W}}}txbxContent')))
            continue
        for group in groups:
            wsps = [w for w in group.iter(f'{{{WPS}}}wsp')
                    if w.find(f'{{{WPS}}}txbx') is not None]
            if not wsps:
                continue
            pics = list(group.iter(f'{{{PIC}}}pic'))
            grp_xfrm = group.find(f'{{{WPG}}}grpSpPr/{{{A}}}xfrm')
            if len(pics) != 1 or grp_xfrm is None:
                stats['skipped'] += len(wsps)
                continue
            blip = pics[0].find(f'.//{{{A}}}blip')
            rid = blip.get(f'{{{R}}}embed') if blip is not None else None
            norm = _normalizer(grp_xfrm)
            pic_xfrm = pics[0].find(f'{{{PIC}}}spPr/{{{A}}}xfrm')
            if rid is None or norm is None or pic_xfrm is None:
                stats['skipped'] += len(wsps)
                continue
            pic_rect = norm(pic_xfrm)
            boxes = []
            for wsp in wsps:
                box = _parse_box(wsp, norm, default_pt, stats)
                if box is not None:
                    boxes.append(box)
            if boxes:
                result[rid] = {'pic': pic_rect, 'boxes': boxes}
    return result, stats


# ---------- 內部 ----------

def _iter_drawings(elem):
    """走訪 w:drawing，但不進入 mc:Fallback（VML 分支，避免重複計數）。"""
    if elem.tag == f'{{{MC}}}Fallback':
        return
    if elem.tag == f'{{{W}}}drawing':
        yield elem
    for child in elem:
        yield from _iter_drawings(child)


def _normalizer(grp_xfrm):
    """回傳 群組子座標 → 群組座標 的正規化函式；無效時回 None。"""
    off = grp_xfrm.find(f'{{{A}}}off')
    ext = grp_xfrm.find(f'{{{A}}}ext')
    ch_off = grp_xfrm.find(f'{{{A}}}chOff')
    ch_ext = grp_xfrm.find(f'{{{A}}}chExt')
    if None in (off, ext, ch_off, ch_ext):
        return None
    gx, gy = int(off.get('x')), int(off.get('y'))
    gcx, gcy = int(ext.get('cx')), int(ext.get('cy'))
    cx0, cy0 = int(ch_off.get('x')), int(ch_off.get('y'))
    ccx, ccy = int(ch_ext.get('cx')), int(ch_ext.get('cy'))
    if ccx <= 0 or ccy <= 0 or gcx <= 0 or gcy <= 0:
        return None

    def norm(xfrm):
        o = xfrm.find(f'{{{A}}}off')
        e = xfrm.find(f'{{{A}}}ext')
        if o is None or e is None:
            return None
        return (gx + (int(o.get('x')) - cx0) * gcx / ccx,
                gy + (int(o.get('y')) - cy0) * gcy / ccy,
                int(e.get('cx')) * gcx / ccx,
                int(e.get('cy')) * gcy / ccy)

    return norm


def _default_size(root) -> float:
    sz = root.find(f'.//{{{W}}}docDefaults/{{{W}}}rPrDefault/{{{W}}}rPr/{{{W}}}sz')
    if sz is not None and (sz.get(f'{{{W}}}val') or '').isdigit():
        return int(sz.get(f'{{{W}}}val')) / 2
    return _DEFAULT_PT


def _parse_box(wsp, norm, default_pt, stats):
    """解析單一 wps:wsp 文字方塊；不支援（旋轉、直排以外）時記入 stats 並回 None。"""
    sp_pr = wsp.find(f'{{{WPS}}}spPr')
    xfrm = sp_pr.find(f'{{{A}}}xfrm') if sp_pr is not None else None
    if xfrm is None:
        stats['skipped'] += 1
        return None
    rot = xfrm.get('rot')
    rot_deg = int(rot) / 60000.0 if rot else 0.0
    if rot_deg % 90 != 0:
        stats['skipped'] += 1
        return None
    rect = norm(xfrm)
    if rect is None:
        stats['skipped'] += 1
        return None

    body_pr = wsp.find(f'{{{WPS}}}bodyPr')
    vert = body_pr.get('vert') if body_pr is not None else None
    if vert not in (None, 'eaVert'):
        stats['skipped'] += 1
        return None
    insets = (91440, 45720, 91440, 45720)  # Word 預設 l/t/r/b insets（EMU）
    anchor, wrap = 't', 'square'
    if body_pr is not None:
        try:
            insets = tuple(int(body_pr.get(k, d)) for k, d in
                           zip(('lIns', 'tIns', 'rIns', 'bIns'), insets))
        except ValueError:
            pass
        anchor = body_pr.get('anchor', 't')
        wrap = body_pr.get('wrap', 'square')

    tx = wsp.find(f'{{{WPS}}}txbx/{{{W}}}txbxContent')
    if tx is None:
        stats['skipped'] += 1
        return None
    paras = _parse_paras(tx, default_pt)
    if not any(r.get('text') for p in paras for r in p['runs']):
        return None  # 空文字方塊，無事可做
    return {
        'x': rect[0], 'y': rect[1], 'w': rect[2], 'h': rect[3],
        'rot': rot_deg, 'vert': vert, 'anchor': anchor, 'wrap': wrap,
        'insets': insets, 'paras': paras,
    }


def _parse_paras(tx, default_pt) -> list:
    paras = []
    for p in tx.findall(f'{{{W}}}p'):
        jc, line, line_rule, para_rpr = 'left', None, None, None
        pr = p.find(f'{{{W}}}pPr')
        if pr is not None:
            j = pr.find(f'{{{W}}}jc')
            if j is not None:
                jc = {'center': 'center', 'right': 'right', 'end': 'right',
                      'both': 'both', 'distribute': 'both'}.get(
                          j.get(f'{{{W}}}val', 'left'), 'left')
            sp = pr.find(f'{{{W}}}spacing')
            if sp is not None and (sp.get(f'{{{W}}}line') or '').isdigit():
                line = int(sp.get(f'{{{W}}}line')) / 20.0  # 1/20 pt
                line_rule = sp.get(f'{{{W}}}lineRule', 'auto')
            para_rpr = pr.find(f'{{{W}}}rPr')
        runs = []
        _collect_runs(p, para_rpr, default_pt, runs)
        paras.append({'jc': jc, 'line': line, 'line_rule': line_rule, 'runs': runs})
    return paras


def _collect_runs(elem, para_rpr, default_pt, out) -> None:
    for child in elem:
        if child.tag == f'{{{W}}}r':
            _emit_run(child, child.find(f'{{{W}}}rPr'), para_rpr, default_pt, out)
        elif child.tag in (f'{{{W}}}hyperlink', f'{{{W}}}smartTag'):
            _collect_runs(child, para_rpr, default_pt, out)


def _emit_run(run, rpr, para_rpr, default_pt, out) -> None:
    size = _first_sz(rpr, para_rpr, default_pt)
    bold = _first_flag(rpr, para_rpr, 'b')
    color = _first_color(rpr, para_rpr)
    pieces = []
    for child in run:
        if child.tag == f'{{{W}}}t':
            pieces.append(child.text or '')
        elif child.tag == f'{{{W}}}tab':
            pieces.append('\t')
        elif child.tag == f'{{{W}}}br':
            if pieces:
                out.append(_text_run(''.join(pieces), size, bold, color))
                pieces = []
            out.append({'br': True, 'text': None, 'size': size, 'bold': bold,
                        'color': color})
    if pieces:
        out.append(_text_run(''.join(pieces), size, bold, color))


def _text_run(text, size, bold, color):
    return {'text': text, 'br': False, 'size': size, 'bold': bold, 'color': color}


def _first_sz(rpr, para_rpr, default_pt) -> float:
    for holder in (rpr, para_rpr):
        if holder is None:
            continue
        sz = holder.find(f'{{{W}}}sz')
        if sz is not None and (sz.get(f'{{{W}}}val') or '').isdigit():
            return int(sz.get(f'{{{W}}}val')) / 2
    return default_pt


def _first_flag(rpr, para_rpr, tag) -> bool:
    value = None
    for holder in (rpr, para_rpr):
        if holder is None:
            continue
        el = holder.find(f'{{{W}}}{tag}')
        if el is not None:
            val = el.get(f'{{{W}}}val')
            value = val not in ('0', 'false', 'off')
    return bool(value)


def _first_color(rpr, para_rpr):
    for holder in (rpr, para_rpr):
        if holder is None:
            continue
        el = holder.find(f'{{{W}}}color')
        if el is not None:
            val = el.get(f'{{{W}}}val', '')
            if re.fullmatch(r'[0-9A-Fa-f]{6}', val):
                return tuple(int(val[i:i + 2], 16) for i in (0, 2, 4))
            return None  # auto/其他 → 預設黑
    return None
