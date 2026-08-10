#!/usr/bin/env python3
"""Rename video_id-named mp3 files to their real ID3 title, in place.

WHY THIS EXISTS
    The middleware only started reading the ID3 title on 680bdbe. Files saved
    to the user's disk BEFORE that commit carry a name derived from
    downloader.py's outtmpl, i.e. '{video_id}.mp3' -- unreadable. The audio
    itself already carries a correct TIT2 tag (written since 7c6d51a), so the
    real title is recoverable from the bytes on disk: nothing needs
    re-downloading.

DEFAULT IS DRY-RUN. Pass --apply to actually rename.

Every way of NOT getting a title returns a DISTINCT reason (see read_id3_title
below, copied verbatim from webbox/src/middleware/queue_manager.py). If they all
collapsed to '' , "tag missing" and "file unreadable" would look identical and
this script could not tell you WHY a file was skipped -- it would just silently
leave it alone, which is exactly what a broken script also does.
"""
import argparse
import os
import re
import struct
import sys
import unicodedata

_ID3_SCAN_LIMIT = 512 * 1024

# --- verbatim from queue_manager.py (single source of truth for the parser) ---


def read_id3_title(path):
    """Return (title_or_None, reason) for an mp3 on disk."""
    try:
        with open(path, 'rb') as f:
            head = f.read(10)
            if len(head) < 10:
                return None, 'TOO_SHORT'
            if head[:3] != b'ID3':
                return None, 'NO_ID3'
            ver = head[3]
            sz = head[6:10]
            if any(b & 0x80 for b in sz):
                return None, 'BAD_SIZE'
            size = (sz[0] << 21) | (sz[1] << 14) | (sz[2] << 7) | sz[3]
            body = f.read(min(size, _ID3_SCAN_LIMIT))
    except OSError as e:
        return None, 'IO_ERROR:%s' % type(e).__name__

    i, n = 0, len(body)
    while i + 10 <= n:
        fid = body[i:i + 4]
        if fid == b'\x00\x00\x00\x00':
            return None, 'NO_TIT2'
        raw = body[i + 4:i + 8]
        if ver >= 4:
            if any(b & 0x80 for b in raw):
                return None, 'BAD_FRAME_SIZE'
            fsize = (raw[0] << 21) | (raw[1] << 14) | (raw[2] << 7) | raw[3]
        else:
            fsize = struct.unpack('>I', raw)[0]
        if fsize <= 0 or i + 10 + fsize > n:
            return None, 'TRUNCATED'
        if fid == b'TIT2':
            data = body[i + 10:i + 10 + fsize]
            if not data:
                return None, 'EMPTY_FRAME'
            enc, payload = data[0], data[1:]
            try:
                if enc == 0:
                    s = payload.decode('latin-1')
                elif enc == 1:
                    s = payload.decode('utf-16')
                elif enc == 2:
                    s = payload.decode('utf-16-be')
                elif enc == 3:
                    s = payload.decode('utf-8')
                else:
                    return None, 'BAD_ENCODING:%d' % enc
            except UnicodeDecodeError:
                return None, 'DECODE_ERROR'
            s = s.split('\x00')[0].strip()
            if not s:
                return None, 'EMPTY_VALUE'
            return s, 'OK'
        i += 10 + fsize
    return None, 'NO_TIT2'


# --- filename sanitising -----------------------------------------------------

# The target is a Windows filesystem reached through WSL's drvfs, so the
# WINDOWS rules bind, not Linux's. Linux forbids exactly one byte ('/'); NTFS
# forbids nine characters, forbids a trailing dot or space, and reserves a list
# of device names. Applying only the Linux rule here would produce names that
# this script reports as written while Explorer cannot open them.
_WIN_FORBIDDEN = r'<>:"/\|?*'
_WIN_RESERVED = {
    'CON', 'PRN', 'AUX', 'NUL',
    *('COM%d' % i for i in range(1, 10)),
    *('LPT%d' % i for i in range(1, 10)),
}

# NTFS caps a path COMPONENT at 255 UTF-16 code units. That is a different
# quantity from both len(str) and len(bytes): a CJK character is 1 char, 3 UTF-8
# bytes and 1 UTF-16 unit, while an emoji is 1 char, 4 UTF-8 bytes and 2 UTF-16
# units. Measuring the wrong one is how a name that is "well under the limit"
# still fails to create.
_NAME_MAX_UTF16 = 255


def _utf16_len(s):
    return len(s.encode('utf-16-le')) // 2


def sanitize_for_windows(title, ext, reserve=0):
    """Turn an ID3 title into a filename that NTFS will actually accept.

    Returns (name, notes) where notes lists every transformation applied, so a
    dry-run can show WHY a name differs from the raw tag instead of just
    presenting a result. `reserve` leaves room for a ' (2)' style suffix.
    """
    notes = []
    s = unicodedata.normalize('NFC', title)
    if s != title:
        notes.append('nfc-normalised')

    # Control characters would be accepted by some APIs and rejected by others.
    stripped = ''.join(ch for ch in s if unicodedata.category(ch) != 'Cc')
    if stripped != s:
        notes.append('control-chars-removed')
        s = stripped

    replaced = ''.join('_' if ch in _WIN_FORBIDDEN else ch for ch in s)
    if replaced != s:
        notes.append('forbidden-chars-replaced')
        s = replaced

    # Collapse runs of whitespace; a tag often carries newlines or double spaces.
    collapsed = re.sub(r'\s+', ' ', s).strip()
    if collapsed != s:
        notes.append('whitespace-collapsed')
        s = collapsed

    # A trailing dot or space is silently dropped by Windows, which would make
    # the name this script prints differ from the name on disk.
    trimmed = s.rstrip('. ')
    if trimmed != s:
        notes.append('trailing-dot-space-trimmed')
        s = trimmed

    if s.upper() in _WIN_RESERVED or s.upper().split('.')[0] in _WIN_RESERVED:
        s = '_' + s
        notes.append('reserved-name-prefixed')

    budget = _NAME_MAX_UTF16 - _utf16_len(ext) - reserve
    if _utf16_len(s) > budget:
        # Truncate by UTF-16 units, never by bytes, and never mid-surrogate.
        out = []
        used = 0
        for ch in s:
            w = _utf16_len(ch)
            if used + w > budget:
                break
            out.append(ch)
            used += w
        s = ''.join(out).rstrip('. ')
        notes.append('truncated-to-%d-utf16-units' % budget)

    if not s:
        return None, notes + ['EMPTY_AFTER_SANITISE']
    return s + ext, notes


# --- main --------------------------------------------------------------------

# Only files whose CURRENT name still looks machine-generated are candidates.
# A file the user already renamed by hand must not be touched: the tag is not
# more authoritative than a human's deliberate choice.
_VIDEO_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')

MEDIA_EXTS = ('.mp3', '.m4a', '.opus', '.aac', '.flac', '.mp4', '.webm', '.mkv')


def plan(directory, exts, all_names=False):
    """Build the rename plan. Returns (rows, taken) without touching anything."""
    try:
        entries = sorted(os.scandir(directory), key=lambda e: e.name)
    except OSError as e:
        print('CANNOT READ DIRECTORY: %s: %s' % (type(e).__name__, e))
        return None, None

    # Every existing name is a collision target, including files this script
    # will not otherwise consider.
    taken = {e.name.lower() for e in entries if e.is_file()}
    rows = []

    for e in entries:
        if not e.is_file():
            continue
        stem, ext = os.path.splitext(e.name)
        if ext.lower() not in exts:
            continue
        if not all_names and not _VIDEO_ID_RE.match(stem):
            rows.append((e.name, None, 'SKIP_NOT_VIDEO_ID', []))
            continue

        title, reason = read_id3_title(e.path)
        if title is None:
            rows.append((e.name, None, reason, []))
            continue
        if title == stem:
            rows.append((e.name, None, 'ALREADY_CORRECT', []))
            continue

        new, notes = sanitize_for_windows(title, ext)
        if new is None:
            rows.append((e.name, None, 'EMPTY_AFTER_SANITISE', notes))
            continue

        if new.lower() == e.name.lower():
            rows.append((e.name, None, 'ALREADY_CORRECT', notes))
            continue

        # Two videos can legitimately share a title. Suffix rather than
        # overwrite: silently clobbering a file is the one outcome that cannot
        # be undone.
        if new.lower() in taken:
            base, bext = os.path.splitext(new)
            for k in range(2, 100):
                suffix = ' (%d)' % k
                cand_base, _ = sanitize_for_windows(
                    title, bext, reserve=_utf16_len(suffix))
                if cand_base is None:
                    break
                cand = os.path.splitext(cand_base)[0] + suffix + bext
                if cand.lower() not in taken:
                    new = cand
                    notes = notes + ['collision-suffixed']
                    break
            else:
                rows.append((e.name, None, 'COLLISION_UNRESOLVED', notes))
                continue
            if new.lower() in taken:
                rows.append((e.name, None, 'COLLISION_UNRESOLVED', notes))
                continue

        taken.add(new.lower())
        rows.append((e.name, new, 'OK', notes))

    return rows, taken


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('directory', help='folder holding the saved files')
    ap.add_argument('--apply', action='store_true',
                    help='actually rename (default is dry-run)')
    ap.add_argument('--all-names', action='store_true',
                    help='also consider files whose name is not an 11-char video id')
    ap.add_argument('--ext', default=','.join(MEDIA_EXTS),
                    help='comma-separated extensions to consider')
    args = ap.parse_args()

    exts = tuple(x if x.startswith('.') else '.' + x
                 for x in (e.strip().lower() for e in args.ext.split(',')) if x)

    rows, _ = plan(args.directory, exts, args.all_names)
    if rows is None:
        return 2

    todo = [r for r in rows if r[1] is not None]
    skipped = [r for r in rows if r[1] is None]

    print('DIRECTORY  %s' % args.directory)
    print('MODE       %s' % ('APPLY' if args.apply else 'DRY-RUN (nothing will change)'))
    print('CONSIDERED %d file(s) matching %s' % (len(rows), ','.join(exts)))
    print('')

    if todo:
        print('--- WILL RENAME (%d) ---' % len(todo))
        for old, new, _, notes in todo:
            print('  %s' % old)
            print('    -> %s' % new)
            if notes:
                print('       [%s]' % ', '.join(notes))
    else:
        print('--- WILL RENAME (0) ---')

    if skipped:
        # Group by reason so a directory of 60 files does not print 60 lines,
        # while still naming every file: a summary count alone could not
        # distinguish "skipped for a good reason" from "the parser broke".
        print('')
        print('--- SKIPPED (%d) ---' % len(skipped))
        by_reason = {}
        for old, _, reason, _ in skipped:
            by_reason.setdefault(reason, []).append(old)
        for reason in sorted(by_reason):
            names = by_reason[reason]
            print('  %-24s %d' % (reason, len(names)))
            for nm in names[:5]:
                print('      %s' % nm)
            if len(names) > 5:
                print('      ... and %d more' % (len(names) - 5))

    if not args.apply:
        print('')
        print('Dry-run only. Re-run with --apply to perform the %d rename(s).' % len(todo))
        return 0

    print('')
    print('--- APPLYING ---')
    done = failed = 0
    for old, new, _, _ in todo:
        src = os.path.join(args.directory, old)
        dst = os.path.join(args.directory, new)
        # A last-moment existence check: the plan was built earlier and the
        # directory is shared with a live browser. os.rename would overwrite
        # silently on POSIX.
        if os.path.exists(dst):
            print('  SKIP (appeared since plan): %s' % new)
            failed += 1
            continue
        try:
            os.rename(src, dst)
            done += 1
        except OSError as e:
            print('  FAIL %s: %s: %s' % (old, type(e).__name__, e))
            failed += 1
    print('')
    print('RENAMED %d   FAILED %d   SKIPPED %d' % (done, failed, len(skipped)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
