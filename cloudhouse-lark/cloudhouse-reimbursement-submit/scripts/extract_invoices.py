#!/usr/bin/env python3
"""只读提取本地发票文件夹的票面台账（cloudhouse-reimbursement-submit）。

用法：python3 extract_invoices.py <文件夹> [--out PATH]
默认 JSON 输出到 stdout；--out 时写文件并打印摘要。源文件夹严格只读，
zip 解压仅落 tempfile（/tmp）。图片不 OCR，只标 needs_visual 交 agent 目视。
解析失败不猜、不用文件名兜底：缺失字段置 null 并标 needs_visual。
needs_visual 存在时仍 exit 0；仅用法/IO 错误非零。
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

NO_RE = re.compile(r'(?<!\d)\d{20}(?!\d)')
DATE_RE = re.compile(r'开票日期[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日')
TOTAL_RE = re.compile(r'[（(]小写[）)]\s*[¥￥]\s*([0-9]+(?:\.[0-9]+)?)')
ITEM_RE = re.compile(r'\*[^*\n]+\*([^*\n\s]+)')
NAME_SPLIT = re.compile(r'名\s*称[：:]')
CJK_FRAG = re.compile(r'[一-鿿]{1,4}')
AMT_HINT_RE = re.compile(r'\d+\.\d{2}')
IMAGE_EXT = {'.jpg', '.jpeg', '.png'}
MAX_ZIP_DEPTH = 2


def scan_folder(root):
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.name.startswith('.'):
            continue
        yield p


def safe_zip_name(raw):
    try:
        name = raw.encode('cp437').decode('gbk')
    except (UnicodeError, UnicodeDecodeError):
        try:
            name = raw.encode('cp437').decode('utf-8')
        except (UnicodeError, UnicodeDecodeError):
            name = raw
    return name


def extract_zip(path, dest, depth):
    """解压 zip 到 dest，返回 [(解码名, 落地路径)]；拒绝穿越路径，嵌套限深。"""
    out = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = safe_zip_name(info.filename)
            if name.startswith('/') or '..' in Path(name).parts:
                continue
            target = dest / Path(name).name
            target.write_bytes(z.read(info))
            out.append((name, target))
    return out


def pdf_text(path):
    try:
        r = subprocess.run(['pdftotext', '-layout', str(path), '-'],
                           capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode('utf-8', errors='replace')


def parse_invoice(text):
    """best-effort 解析票面；品名可能被排版截断，关键字段以 agent 目视复核为准。"""
    got = {'invoice_no': None, 'date': None, 'seller': None,
           'item': None, 'total': None}
    reasons = []
    nos = sorted(set(NO_RE.findall(text)))
    if len(nos) == 1:
        got['invoice_no'] = nos[0]
    else:
        reasons.append('20位号码缺失或多个(%d)' % len(nos))
    m = DATE_RE.search(text)
    if m:
        got['date'] = '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    else:
        reasons.append('开票日期缺失')
    lines = text.splitlines()
    for line in lines:
        if '名' not in line or '称' not in line:
            continue
        parts = [s.strip() for s in NAME_SPLIT.split(line)[1:]]
        parts = [re.sub(r'\s*\d+\s*$', '', s) for s in parts if s]
        parts = [re.sub(r'[购销方售信]+$', '', s).strip() for s in parts]
        parts = [s for s in parts if s]
        if len(parts) >= 2:
            got['seller'] = parts[-1]
            break
        if len(parts) == 1 and '销' in line:
            got['seller'] = parts[0]
            break
    if not got['seller']:
        reasons.append('销售方缺失')
    m = ITEM_RE.search(text)
    if m:
        item = m.group(1)
        idx = next((i for i, l in enumerate(lines) if m.group(0) in l), None)
        if idx is not None:
            nxt = next((l.strip() for l in lines[idx + 1:] if l.strip()), '')
            if CJK_FRAG.fullmatch(nxt):
                item += nxt
        got['item'] = item
    else:
        reasons.append('品名缺失')
    m = TOTAL_RE.search(text)
    if m:
        try:
            got['total'] = str(Decimal(m.group(1)))
        except InvalidOperation:
            reasons.append('价税合计解析失败')
    else:
        reasons.append('价税合计缺失')
    return got, reasons


def filename_hints(path):
    stem = path.stem
    hints = {'no': None, 'amounts': AMT_HINT_RE.findall(stem), 'item': None}
    m = NO_RE.search(stem)
    if m:
        hints['no'] = m.group(0)
    head = re.split(r'[_\-]', stem)[0]
    if head and re.search(r'[一-鿿]', head):
        hints['item'] = head
    return hints


def mismatches(got, hints):
    out = []
    if hints['no'] and got['invoice_no'] and hints['no'] != got['invoice_no']:
        out.append('文件名号码%s≠票面号码%s' % (hints['no'], got['invoice_no']))
    if hints['amounts'] and got['total'] and got['total'] not in hints['amounts']:
        out.append('文件名金额%s与票面价税合计%s不符(文件名可能为未税或旧值)'
                   % ('/'.join(hints['amounts']), got['total']))
    if hints['item'] and got['item']:
        if hints['item'] not in got['item'] and got['item'] not in hints['item']:
            out.append('文件名品名提示「%s」与票面品名「%s」不符'
                       % (hints['item'], got['item']))
    return out


def entry_for(path, root, kind, source_zip=None, temp_path=None):
    rel = path.relative_to(root) if source_zip is None else None
    e = {
        'path': str(path),
        'project_folder': rel.parts[0] if rel and len(rel.parts) > 1 else '',
        'type': kind,
        'invoice_no': None, 'date': None, 'seller': None,
        'item': None, 'total': None,
        'needs_visual': False, 'visual_reason': [],
        'filename_hints': filename_hints(path), 'mismatch': [],
        'source_zip': source_zip, 'temp_path': temp_path,
    }
    return e


def build_ledger(root):
    entries = []
    tmpdirs = []

    def handle(path, kind, source_zip=None, temp_path=None, depth=0):
        e = entry_for(path, root, kind, source_zip, temp_path)
        if kind == 'zip':
            if depth >= MAX_ZIP_DEPTH:
                e['needs_visual'] = True
                e['visual_reason'].append('嵌套zip超深')
            else:
                dest = Path(tempfile.mkdtemp(prefix='inv-zip-'))
                tmpdirs.append(dest)
                try:
                    for name, target in extract_zip(path, dest, depth):
                        sub = target.suffix.lower()
                        sk = ('pdf' if sub == '.pdf' else
                              'image' if sub in IMAGE_EXT else
                              'zip' if sub == '.zip' else 'other')
                        handle(target, sk, source_zip='%s::%s' % (path, name),
                               temp_path=str(target), depth=depth + 1)
                except (zipfile.BadZipFile, OSError) as ex:
                    e['needs_visual'] = True
                    e['visual_reason'].append('zip解压失败:%s' % ex)
        elif kind == 'pdf':
            text = pdf_text(path)
            if not text or not text.strip():
                e['needs_visual'] = True
                e['visual_reason'].append('PDF无文本层或pdftotext失败')
            else:
                got, reasons = parse_invoice(text)
                e.update(got)
                if reasons:
                    e['needs_visual'] = True
                    e['visual_reason'].extend(reasons)
                e['mismatch'] = mismatches(got, e['filename_hints'])
        elif kind == 'image':
            e['needs_visual'] = True
            e['visual_reason'].append('图片发票需目视')
        else:
            e['needs_visual'] = True
            e['visual_reason'].append('未知类型需人工检查')
        entries.append(e)

    for p in scan_folder(root):
        ext = p.suffix.lower()
        kind = ('pdf' if ext == '.pdf' else
                'image' if ext in IMAGE_EXT else
                'zip' if ext == '.zip' else 'other')
        handle(p, kind)
    summary = {
        'total': len(entries),
        'pdf': sum(e['type'] == 'pdf' for e in entries),
        'image': sum(e['type'] == 'image' for e in entries),
        'zip': sum(e['type'] == 'zip' for e in entries),
        'other': sum(e['type'] == 'other' for e in entries),
        'needs_visual': sum(e['needs_visual'] for e in entries),
        'mismatch': sum(bool(e['mismatch']) for e in entries),
    }
    return {'root': str(root), 'entries': entries, 'summary': summary}, tmpdirs


def main():
    ap = argparse.ArgumentParser(description='只读提取发票票面台账')
    ap.add_argument('folder', type=Path)
    ap.add_argument('--out', type=Path, default=None)
    args = ap.parse_args()
    if not args.folder.is_dir():
        print('folder not found: %s' % args.folder, file=sys.stderr)
        return 2
    ledger, _tmpdirs = build_ledger(args.folder)
    blob = json.dumps(ledger, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(blob + '\n', encoding='utf-8')
        print(json.dumps(ledger['summary'], ensure_ascii=False))
    else:
        print(blob)
    return 0


if __name__ == '__main__':
    sys.exit(main())