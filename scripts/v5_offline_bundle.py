"""Build and verify a bounded, credential-free V5 presentation fallback.

Read only committed presentation artifacts. LFS payloads must already exist
locally and match their pointer; no download, application or database access.
"""
import argparse
import hashlib
import html
import io
import json
import posixpath
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DECK = '簡報文件/超市AI版_2026-10-18/VibeCart_AI_超市網購與AI系統_2026-10-18_v5'
PPTX_SHA256 = '43374f71c5e42fdc1725f38a8ac69ea0e2ccc696f6238ebb06425e58e00d7203'
PDF_SHA256 = 'c5555c2a54d8a4200fd79fb8073d0fa5af691b40b13a4e031ddf9f8f6dc4535d'
INDEX = '簡報文件/screenshots/S01-S12_取證索引_2026-10-18.json'
RUNBOOK = '簡報文件/離線備援/README.md'
PAGES = '簡報文件/離線備援/投影片/'
CURRENT_PROFILE = 'v5-14-20261022'
CURRENT_FOLDER = '簡報文件/超市AI版_2026-10-22_閱讀與備援/'
CURRENT_PPTX_SHA256 = '4aa9b13286fe98574d3dd648889545ad196d92cea9aebb9a143c794ad392d193'
CURRENT_PDF_SHA256 = '79e4883a70fc38df2cd94cdb0b74685228b1763481753a55584945c4779186f5'
MAX_BYTES = 50 * 1024 * 1024
MAX_FILES = 43
NOTES = {
    '簡報文件/超市AI版_2026-10-18/2026-10-20_SAM模擬_N16素材覆核.md': 'updates/N16-review.md',
    '簡報文件/超市AI版_2026-10-18/2026-10-20_SAM模擬_展示內容更新卡.md': 'updates/current-scope.md',
    '簡報文件/離線備援/SAM模擬_N17_復原與排練_2026-10-20.md': 'updates/N17-rehearsal.md',
}
STAMP = (1980, 1, 1, 0, 0, 0)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)


def committed_bytes(root, commit, path):
    entry = git(root, 'ls-tree', commit, '--', path).decode('utf-8')
    if not entry.startswith(('100644 ', '100755 ')):
        raise ValueError('Artifact must be a committed regular file: ' + path)
    blob = git(root, 'show', commit + ':' + path)
    if blob.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
        match = re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([a-f0-9]{64})\nsize ([0-9]+)\n?', blob)
        if not match:
            raise ValueError('Invalid LFS pointer')
        oid, size = match[1].decode(), int(match[2])
        if size > MAX_BYTES:
            raise ValueError('LFS artifact exceeds offline size bound')
        common = Path(git(root, 'rev-parse', '--git-common-dir').decode().strip())
        if not common.is_absolute():
            common = root / common
        cached = common / 'lfs' / 'objects' / oid[:2] / oid[2:4] / oid
        if not cached.is_file() or cached.is_symlink():
            raise ValueError('LFS payload unavailable; fetch it before going offline')
        blob = cached.read_bytes()
        if len(blob) != size or sha256(blob) != oid:
            raise ValueError('LFS payload integrity failed')
    return blob


def safe_name(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Unsafe archive path')
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Unsafe archive path')
    if any(p.rstrip(' .') != p or p.split('.')[0].upper() in
           {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
           for p in path.parts):
        raise ValueError('Unsafe Windows archive path')
    return name


def encode_json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def note_links(data, source, target, mapping, commit):
    """Keep bundled references local and pin other citations to GitHub."""
    def replace(match):
        url = urlsplit(match[2])
        if url.scheme or url.netloc or not url.path:
            return match[0]
        source_path = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(url.path)))
        if source_path == '..' or source_path.startswith('../'):
            raise ValueError('Note reference escapes source repository')
        if source_path in mapping:
            link = posixpath.relpath(mapping[source_path], posixpath.dirname(target) or '.')
        else:
            link = 'https://github.com/SamWang61/LLM_PJ/blob/' + commit + '/' + quote(source_path, safe='/')
        if url.fragment:
            link += '#' + url.fragment
        return '[' + match[1] + '](' + link + ')'
    text = re.sub(r'\[([^\]\n]+)\]\(([^)\s]+)\)', replace, data.decode('utf-8-sig'))
    return (text.rstrip() + '\n\n離線包內已收錄的文件以相對路徑引用；其餘 GitHub 固定來源連結需連線，不能當離線檔案。\n').encode('utf-8')


def html_index(commit, rows, notes=()):
    cards = []
    for row in rows:
        title = html.escape(row['file'])
        caption = html.escape('｜'.join(str(row.get(k, '未記錄')) for k in
                                      ('captured_at_taipei', 'role', 'revision', 'note')))
        cards.append(f'<article><h2>{title}</h2><p>{caption}</p>'
                     f'<a href="screenshots/{title}"><img src="screenshots/{title}" alt="{title}" loading="lazy"></a></article>')
    note_nav = ''.join('<li><a href="' + html.escape(name, quote=True) + '">' + html.escape(name) + '</a></li>' for name in notes)
    return ('''<!doctype html><html lang="zh-Hant"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VibeCart V5 離線備援</title><style>
body{font:18px/1.6 system-ui,sans-serif;max-width:1120px;margin:24px auto;padding:0 20px;background:#f7f6ee;color:#153a37}
a{color:#006b50}a:focus-visible{outline:3px solid #a45e00;outline-offset:4px}
nav{display:flex;gap:24px;flex-wrap:wrap}article{border-top:1px solid #abc;padding:20px 0}img{max-width:100%;height:auto}p{overflow-wrap:anywhere}code{word-break:break-all}
</style><h1>VibeCart V5 離線備援</h1>
<p>這是已記錄畫面的離線閱讀包，沒有網站、帳號、資料庫或付款功能。截圖保留各自取證版本；不是目前線上畫面或最終簽收。V5 手動封面、頁尾與封底原樣保留。</p>
<nav><a href="slides.html">13 頁圖片閱讀版</a><a href="presentation.pdf">PDF 閱讀版</a><a href="presentation.pptx">原始 PowerPoint</a><a href="README.md">故障替代流程與排練表</a><a href="manifest.json">檔案核對清冊</a></nav>
<p>內容來源提交：<code>''' + html.escape(commit) + '</code></p>' + ('<h2>10/20 更新說明（Markdown）</h2><p>原投影片與截圖保持歷史版本；最新展示界線請連同閱讀。</p><ul>' + note_nav + '</ul>' if note_nav else '') + ''.join(cards) + '</html>\n').encode('utf-8')


def source_files(root, commit):
    """Historical 13-slide contract; requires a matching historical commit."""
    pptx = committed_bytes(root, commit, DECK + '.pptx')
    if sha256(pptx) != PPTX_SHA256:
        raise ValueError('Manual V5 PPTX changed; review a new explicit version contract')
    with zipfile.ZipFile(io.BytesIO(pptx)) as deck:
        slides = [p for p in deck.namelist() if re.fullmatch(r'ppt/slides/slide[0-9]+\.xml', p)]
        if len(slides) != 13 or deck.testzip():
            raise ValueError('V5 slide integrity failed')
    pdf = committed_bytes(root, commit, DECK + '.pdf')
    if not pdf.startswith(b'%PDF-') or sha256(pdf) != PDF_SHA256:
        raise ValueError('Reviewed V5 PDF payload changed')
    index_bytes = committed_bytes(root, commit, INDEX)
    rows = json.loads(index_bytes)['files']
    if len(rows) != 20 or len({r['file'] for r in rows}) != 20:
        raise ValueError('Expected 20 uniquely named screenshot assets')
    available = {source: target for source, target in NOTES.items() if git(root, 'ls-tree', commit, '--', source)}
    mapping = {**available, RUNBOOK: 'README.md', DECK + '.pptx': 'presentation.pptx',
               DECK + '.pdf': 'presentation.pdf', INDEX: 'screenshot-provenance.json'}
    files = {'presentation.pptx': pptx, 'presentation.pdf': pdf,
             'screenshot-provenance.json': index_bytes,
             'README.md': note_links(committed_bytes(root, commit, RUNBOOK), RUNBOOK, 'README.md', mapping, commit)}
    for source, target in available.items():
        files[target] = note_links(committed_bytes(root, commit, source), source, target, mapping, commit)
    for row in rows:
        name = row['file']
        if not re.fullmatch(r'S(?:0[1-9]|1[0-2])-[A-Za-z0-9_-]+\.png', name):
            raise ValueError('Screenshot name outside explicit allowlist')
        data = committed_bytes(root, commit, '簡報文件/screenshots/' + name)
        if not data.startswith(b'\x89PNG\r\n\x1a\n') or sha256(data) != row['sha256'] or len(data) != row['bytes']:
            raise ValueError('Screenshot provenance integrity failed')
        files['screenshots/' + name] = data
    files['index.html'] = html_index(commit, rows, available.values())
    page_index = committed_bytes(root, commit, PAGES + 'pages.json')
    pages = json.loads(page_index)
    names = [f'page-{i:02d}.png' for i in range(1, 14)]
    if pages.get('source_pdf_sha256') != PDF_SHA256 or [r['file'] for r in pages['files']] != names:
        raise ValueError('Rendered PDF page contract mismatch')
    for row in pages['files']:
        data = committed_bytes(root, commit, PAGES + row['file'])
        if not data.startswith(b'\x89PNG\r\n\x1a\n') or sha256(data) != row['sha256'] or len(data) != row['bytes']:
            raise ValueError('Rendered PDF page integrity failed')
        files['slides/' + row['file']] = data
    files['slides/pages.json'] = page_index
    links = ' '.join(f'<a href="#page-{i}">{i}</a>' for i in range(1, 14))
    slides = ''.join(f'<section id="page-{i}"><h2>第 {i} 頁</h2><img src="slides/page-{i:02d}.png" alt="V5 第 {i} 頁"></section>' for i in range(1, 14))
    files['slides.html'] = ('''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V5 13頁圖片閱讀版</title><style>body{margin:20px;background:#f7f6ee;color:#153a37;font:18px/1.5 system-ui,sans-serif}nav{position:sticky;top:0;background:#f7f6ee;padding:12px}a{color:#006b50;margin-right:12px}img{width:100%;height:auto}section{max-width:1280px;margin:auto}a:focus-visible{outline:3px solid #a45e00}</style><h1>V5 13頁圖片閱讀版</h1><p>由原 PDF 逐頁渲染；不需 PDF 外掛，沒有即時網站操作。</p><nav><a href="index.html">回索引</a>''' + links + '</nav>' + slides + '</html>\n').encode('utf-8')
    return files


def current_source_files(root, commit):
    """Reviewed 14-slide master and native PDF, with no application secrets."""
    pptx = committed_bytes(root, commit, DECK + '.pptx')
    if sha256(pptx) != CURRENT_PPTX_SHA256:
        raise ValueError('Current PPTX changed; review a new explicit version contract')
    with zipfile.ZipFile(io.BytesIO(pptx)) as deck:
        slides = [n for n in deck.namelist() if re.fullmatch(r'ppt/slides/slide[0-9]+\.xml', n)]
        if len(slides) != 14 or deck.testzip():
            raise ValueError('Current 14-slide integrity failed')
    pdf_path = CURRENT_FOLDER + 'VibeCart_AI_14頁閱讀版_2026-10-22.pdf'
    pdf = committed_bytes(root, commit, pdf_path)
    if not pdf.startswith(b'%PDF-') or sha256(pdf) != CURRENT_PDF_SHA256:
        raise ValueError('Reviewed current PDF payload changed')
    page_index_path = CURRENT_FOLDER + '投影片/pages.json'
    page_index = committed_bytes(root, commit, page_index_path)
    pages = json.loads(page_index)
    names = [f'page-{i:02d}.png' for i in range(1, 15)]
    if (pages.get('profile') != CURRENT_PROFILE or pages.get('page_count') != 14
            or pages.get('source_pptx_sha256') != CURRENT_PPTX_SHA256
            or pages.get('source_pdf_sha256') != CURRENT_PDF_SHA256
            or [r['file'] for r in pages['files']] != names):
        raise ValueError('Current rendered page contract mismatch')
    sources = {
        DECK + '.pptx': 'presentation.pptx', pdf_path: 'presentation.pdf',
        page_index_path: 'slides/pages.json', CURRENT_FOLDER + 'README.md': 'README.md',
        'docs/CURRENT_CONTEXT.md': 'updates/current-context.md',
        CURRENT_FOLDER + '展示內容更新卡.md': 'updates/current-scope.md',
    }
    files = {'presentation.pptx': pptx, 'presentation.pdf': pdf, 'slides/pages.json': page_index}
    for source, target in sources.items():
        if source.endswith('.md'):
            files[target] = note_links(committed_bytes(root, commit, source), source, target, sources, commit)
    for row in pages['files']:
        data = committed_bytes(root, commit, CURRENT_FOLDER + '投影片/' + row['file'])
        if (not data.startswith(b'\x89PNG\r\n\x1a\n') or sha256(data) != row['sha256']
                or len(data) != row['bytes']):
            raise ValueError('Current rendered page integrity failed')
        files['slides/' + row['file']] = data
    style = ('<style>body{font:18px/1.6 system-ui,sans-serif;max-width:1600px;margin:24px auto;'
             'padding:0 20px;background:#f7f6ee;color:#153a37}a{color:#006b50;margin-right:18px}'
             'a:focus-visible{outline:3px solid #a45e00}img{width:100%;height:auto}'
             'nav{position:sticky;top:0;background:#f7f6ee;padding:12px}code{overflow-wrap:anywhere}</style>')
    start = ('<!doctype html><html lang="zh-Hant"><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1">')
    files['index.html'] = (start + '<title>VibeCart 14頁離線備援</title>' + style
        + '<h1>VibeCart 14頁離線備援 / Offline presentation</h1>'
          '<p>本包只提供使用者指定原稿的14頁閱讀版。請先讀展示內容更新卡，再講解歷史畫面；沒有網站、帳號或資料庫功能。</p>'
          '<p>原稿第12、13頁內容相同，頁尾同標12，均原樣保留。頁數以實際順序1至14為準。</p>'
          '<nav><a href="slides.html">14頁圖片閱讀版</a><a href="presentation.pdf">PDF</a>'
          '<a href="presentation.pptx">原始PowerPoint</a><a href="README.md">備援流程</a>'
          '<a href="updates/current-scope.md">展示內容更新卡</a><a href="updates/current-context.md">專案上下文</a>'
          '<a href="manifest.json">雜湊清冊</a></nav><p>來源提交：<code>' + html.escape(commit)
          + '</code></p><p>Static recorded material only; no live application or acceptance claim.</p></html>\n').encode('utf-8')
    nav = ''.join(f'<a href="#page-{i}">{i}</a>' for i in range(1, 15))
    slides_html = ''.join(f'<section id="page-{i}"><h2>第{i}頁</h2><img src="slides/page-{i:02d}.png" '
                          f'alt="原稿第{i}頁" loading="lazy"></section>' for i in range(1, 15))
    files['slides.html'] = (start + '<title>VibeCart 14頁圖片閱讀版</title>' + style
        + '<h1>VibeCart 14頁圖片閱讀版</h1><p>原稿的畫面與日期保留；現況先讀展示內容更新卡。</p>'
          '<nav><a href="index.html">回索引</a>' + nav + '</nav>' + slides_html + '</html>\n').encode('utf-8')
    return files


def pack(files, commit):
    if len(files) > MAX_FILES or sum(map(len, files.values())) > MAX_BYTES:
        raise ValueError('Offline package exceeds bounds')
    names = [safe_name(n) for n in files]
    if 'manifest.json' in files or len({n.casefold() for n in names}) != len(names):
        raise ValueError('Duplicate or reserved artifact name')
    manifest = {'version': 1, 'source_commit': commit,
                'scope': 'V5 presentation and dated screenshots only; no credentials or live application',
                'files': [{'path': n, 'bytes': len(files[n]), 'sha256': sha256(files[n])} for n in sorted(files)]}
    all_files = {**files, 'manifest.json': encode_json(manifest)}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(all_files):
            info = zipfile.ZipInfo(name, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, all_files[name])
    return buffer.getvalue(), manifest


def verified_payload(archive_bytes):
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        entries = archive.infolist()
        names = [safe_name(i.filename) for i in entries]
        if (len(entries) > MAX_FILES + 1 or len({n.casefold() for n in names}) != len(names)
                or sum(i.file_size for i in entries) > MAX_BYTES + 100_000
                or any(i.file_size > MAX_BYTES or (i.external_attr >> 16) & 0o170000 == 0o120000 for i in entries)):
            raise ValueError('Unsafe or oversized archive')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('version') != 1 or not isinstance(manifest.get('files'), list):
            raise ValueError('Unsupported manifest')
        expected = [safe_name(r['path']) for r in manifest['files']]
        if len(set(n.casefold() for n in expected)) != len(expected) or 'manifest.json' in expected:
            raise ValueError('Duplicate manifest path')
        if set(names) != set(expected) | {'manifest.json'}:
            raise ValueError('Archive file set differs from manifest')
        payload = {}
        for row in manifest['files']:
            data = archive.read(row['path'])
            if len(data) != row['bytes'] or sha256(data) != row['sha256']:
                raise ValueError('Restored artifact integrity failed')
            payload[row['path']] = data
        payload['manifest.json'] = archive.read('manifest.json')
    return payload, manifest


def restore(archive_bytes, destination):
    payload, manifest = verified_payload(archive_bytes)
    destination = Path(destination)
    # Require a fresh directory; never replace existing files or follow links.
    destination.mkdir(parents=False, exist_ok=False)
    base = destination.resolve()
    for name, data in payload.items():
        target = base / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
        if sha256(target.read_bytes()) != sha256(data):
            raise ValueError('Restored disk readback failed')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    build = sub.add_parser('build');build.add_argument('--commit', required=True);build.add_argument('--output', type=Path, required=True)
    build.add_argument('--profile', choices=(CURRENT_PROFILE, 'legacy-13'), default=CURRENT_PROFILE,
                       help='Current reviewed 14-slide deck by default; legacy requires a historical matching commit')
    check = sub.add_parser('restore');check.add_argument('--archive', type=Path, required=True);check.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'build':
        commit = git(ROOT, 'rev-parse', '--verify', args.commit + '^{commit}').decode().strip()
        files = (source_files if args.profile == 'legacy-13' else current_source_files)(ROOT, commit)
        content, manifest = pack(files, commit)
        verified_payload(content)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('xb') as stream:
            stream.write(content)
        print(json.dumps({'source_commit': commit, 'payload_files': len(manifest['files']), 'archive_bytes': len(content), 'archive_sha256': sha256(content)}))
    else:
        content = args.archive.read_bytes()
        manifest = restore(content, args.destination)
        print(json.dumps({'source_commit': manifest['source_commit'], 'payload_files_verified': len(manifest['files']), 'fresh_restore': True}))


if __name__ == '__main__':
    main()
