"""Cuts a recorded take into one clip per line and adds the clips to the Amharic app.

Needs ffmpeg (brew install ffmpeg).

  python3 tools/amharic-audio/split.py 3 ~/Desktop/take-03.m4a      a whole take
  python3 tools/amharic-audio/split.py 3:7 ~/Desktop/redo.m4a       re-record line 7 of take 3 on its own

If the number of parts doesn't match the lines:
  --join 5      part 5 and part 6 are one line with a pause in it (repeat for more)
  --gap 0.8     two lines ran together; split on shorter silences for this take

Clips go to amharic/audio/, and amharic/audio/clips.json is rebuilt so the app knows which lines have a recording.
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, '..', '..', 'amharic', 'audio')
SILENCE_DB = '-35dB'   # quieter than this counts as a gap; raise toward -30dB in a noisy room
MIN_GAP = 1.0          # seconds of silence that separate two lines
PAD = 0.15             # seconds kept before and after each line
MIN_SOUND = 0.08       # anything shorter is a click, not a word


def run(args):
    return subprocess.run(args, capture_output=True, text=True)


def duration(path):
    out = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]).stdout
    return float(out.strip())


def speech_parts(path, gap):
    log = run(['ffmpeg', '-i', path, '-af', f'silencedetect=noise={SILENCE_DB}:d={gap}', '-f', 'null', '-']).stderr
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', log)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]
    total = duration(path)
    parts, pos = [], 0.0
    for i, s in enumerate(starts):
        if s - pos > MIN_SOUND:
            parts.append((pos, s))
        pos = ends[i] if i < len(ends) else total
    if total - pos > MIN_SOUND:
        parts.append((pos, total))
    return parts


def export(src, start, end, dest):
    start, end = max(0.0, start - PAD), end + PAD
    r = run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{start:.3f}', '-to', f'{end:.3f}', '-i', src,
             '-af', 'loudnorm=I=-18:TP=-1.5:LRA=11', '-ac', '1', '-ar', '44100', '-c:a', 'aac', '-b:a', '64k', dest])
    if r.returncode:
        sys.exit(r.stderr)


def rebuild_manifest(takes):
    have = set(os.listdir(AUDIO))
    clips = {l['am']: l['file'] for tk in takes for l in tk if l['file'] in have}
    with open(os.path.join(AUDIO, 'clips.json'), 'w') as f:
        json.dump(clips, f, ensure_ascii=False, indent=0)
    total = sum(len(tk) for tk in takes)
    print(f'{len(clips)} of {total} lines now have a recording.')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('which'); p.add_argument('src')
    p.add_argument('--join', type=int, action='append', default=[])
    p.add_argument('--gap', type=float, default=MIN_GAP)
    a = p.parse_args()
    which, src = a.which, os.path.expanduser(a.src)
    with open(os.path.join(HERE, 'lines.json')) as f:
        takes = json.load(f)
    take_no, _, line_no = which.partition(':')
    if not 1 <= int(take_no) <= len(takes):
        sys.exit(f'There are {len(takes)} takes.')
    lines = takes[int(take_no) - 1]
    if line_no:
        lines = [lines[int(line_no) - 1]]
    os.makedirs(AUDIO, exist_ok=True)

    parts = speech_parts(src, a.gap)
    for n in sorted(a.join, reverse=True):
        if not 1 <= n < len(parts):
            sys.exit(f'--join {n}: there is no part {n + 1} to join it with.')
        parts[n - 1:n + 1] = [(parts[n - 1][0], parts[n][1])]
    if len(lines) == 1 and parts:
        parts = [(parts[0][0], parts[-1][1])]
    if len(parts) != len(lines):
        print(f'Found {len(parts)} spoken parts but take {take_no} has {len(lines)} lines.')
        for i, (s, e) in enumerate(parts, 1):
            print(f'  part {i}: {s:6.1f}s to {e:6.1f}s')
        sys.exit('Nothing was saved. Check for a missed line, an extra word, or a long pause inside a line, '
                 'then record the take again or use --join / --gap (see --help).')

    for l, (s, e) in zip(lines, parts):
        export(src, s, e, os.path.join(AUDIO, l['file']))
        print(f'  saved {l["file"]}  {l["am"]}')
    rebuild_manifest(takes)
    if not line_no:
        review(take_no, lines)


def review(take_no, lines):
    """Joins the new clips with short gaps so the take can be checked by ear, line by line."""
    out = os.path.join(HERE, '..', '..', 'recordings', f'review-take-{int(take_no):02d}.m4a')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    inputs, labels = [], ''
    for i, l in enumerate(lines):
        inputs += ['-i', os.path.join(AUDIO, l['file'])]
        labels += f'[{i}:a]apad=pad_dur=0.8[a{i}];'
    mix = labels + ''.join(f'[a{i}]' for i in range(len(lines))) + f'concat=n={len(lines)}:v=0:a=1'
    r = run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', mix, '-c:a', 'aac', '-b:a', '64k', out])
    if not r.returncode:
        print(f'Listen to check the order: {os.path.relpath(out)}')


main()
