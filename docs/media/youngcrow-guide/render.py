"""Render this presentation locally. No YoungCrow commands or client calls run here.

Requires Python, Playwright, Chromium, FFmpeg and NumPy for the original score.
The HTTP server and browser belong to this process and close in finally blocks.
"""
import argparse
import base64
import functools
import hashlib
import http.server
import json
from pathlib import Path
import subprocess
import threading
import time
import wave

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def score(path, duration, chapters):
    """Original quiet pads and bell notes, with no external music samples."""
    import numpy as np
    sr = 44100
    count = round(duration * sr)
    sound = np.zeros((count, 2), dtype=np.float64)
    chords = [(146.832, 174.614, 220.0), (116.541, 146.832, 174.614),
              (130.813, 174.614, 220.0), (130.813, 164.814, 195.998)]
    for bar, start in enumerate(range(0, int(duration), 8)):
        length = min(10, duration - start)
        t = np.arange(round(length * sr)) / sr
        envelope = np.minimum(1, t / 2.0) * np.minimum(1, (length - t) / 3.0)
        for voice, hz in enumerate(chords[bar % len(chords)]):
            tone = (np.sin(t * hz * 2 * np.pi) * .6
                    + np.sin(t * hz * 4 * np.pi) * .19
                    + np.sin(t * hz * 6 * np.pi) * .07)
            tone *= envelope * .032 * (1 + .06 * np.sin(t * 2 * np.pi * .18))
            a = start * sr
            sound[a:a + len(t), 0] += tone * (.85 if voice == 0 else .65)
            sound[a:a + len(t), 1] += tone * (.65 if voice == 0 else .85)
    for i, start in enumerate(chapters):
        t = np.arange(round(min(5, duration - start) * sr)) / sr
        hz = [587.33, 698.46, 880.0, 523.25][i % 4]
        bell = (np.sin(2 * np.pi * hz * t) + .24 * np.sin(2 * np.pi * hz * 2.01 * t))
        bell *= (1 - np.exp(-t * 80)) * np.exp(-t * 1.5) * .035
        a = round(start * sr)
        sound[a:a + len(t), 0] += bell * .8
        sound[a:a + len(t), 1] += bell * .9
    edge = np.minimum(1, np.arange(count) / (sr * 3))
    edge *= np.minimum(1, (count - np.arange(count)) / (sr * 4))
    sound *= edge[:, None]
    pcm = np.round(np.clip(sound, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as wav:
        wav.setparams((2, 2, sr, 0, 'NONE', 'not compressed'))
        wav.writeframes(pcm.tobytes())


def standalone(out):
    html = (HERE / 'index.html').read_text()
    fonts = {}
    for name in ['cinzel-latin.woff2', 'manrope-latin.woff2', 'manrope-bold.woff2']:
        fonts[name] = 'data:font/woff2;base64,' + base64.b64encode((HERE / 'vendor' / name).read_bytes()).decode()
    art = 'data:image/png;base64,' + base64.b64encode((ROOT / 'assets/vitral.png').read_bytes()).decode()
    config = '<script>window.FILM_ART=' + json.dumps(art) + ';window.FILM_FONTS=' + json.dumps(fonts) + ';</script>'
    three = (HERE / 'vendor/three.min.js').read_text()
    html = html.replace('<script src="vendor/three.min.js"></script>', config + '<script>' + three + '</script>')
    html = html.replace('<script src="demo.js"></script>', '<script>' + (HERE / 'demo.js').read_text() + '</script>')
    html = html.replace('<script src="film.js"></script>', '<script>' + (HERE / 'film.js').read_text() + '</script>')
    licenses = '\n\n'.join((HERE / 'vendor' / name).read_text()
        for name in ['THREE-LICENSE.txt', 'CINZEL-OFL.txt', 'MANROPE-OFL.txt'])
    html = html.replace('</html>', '<script type="text/plain" id="third-party-licenses">' + licenses + '</script>\n</html>')
    (out / 'YoungCrow-apresentacao.html').write_text(html)


class QuietServer(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--format', choices=['landscape', 'portrait', 'both'], default='both')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--chapter', choices=['all', 'intro', 'demo'], default='all')
    parser.add_argument('--fps', type=int, default=24)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    standalone(out)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietServer, directory=str(ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/docs/media/youngcrow-guide/index.html?export=1'
    formats = ['landscape', 'portrait'] if args.format == 'both' else [args.format]
    results = []
    browser = None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
                args=['--no-sandbox', '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--disable-dev-shm-usage'])
            try:
                for fmt in formats:
                    width, height = (1920, 1080) if fmt == 'landscape' else (1080, 1920)
                    page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1)
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    try:
                        page.goto(url + '&format=' + fmt)
                        page.evaluate('window.filmReady')
                        scenes = page.evaluate('window.filmScenes')
                        if args.chapter == 'intro':
                            scenes = scenes[:11]
                        elif args.chapter == 'demo':
                            scenes = scenes[11:]
                        offset = scenes[0]['start']
                        duration = scenes[-1]['start'] + scenes[-1]['seconds'] - offset
                        metrics = []
                        for i, scene in enumerate(scenes):
                            moment = scene['start'] + (scene['seconds'] - 1.5 if scene.get('demo') else 3)
                            data = page.evaluate("t=>{const m=seekFilm(t);return {m,png:document.querySelector('#film').toDataURL('image/png').split(',')[1]}}", moment)
                            (out / f'{fmt}-{i:02}.png').write_bytes(base64.b64decode(data['png']))
                            metrics.append(data['m'])
                        if errors or any(m['overflow'] for m in metrics):
                            raise RuntimeError(json.dumps({'errors': errors, 'layout': metrics}))
                        if args.preview:
                            print(json.dumps({'format': fmt, 'duration': duration, 'layout': metrics, 'errors': errors}), flush=True)
                            continue
                        audio = out / 'YoungCrow-trilha-original.wav'
                        if not audio.exists():
                            score(audio, duration, [s['start'] - offset for s in scenes])
                        video = out / ('YoungCrow-9x16.mp4' if fmt == 'portrait' else 'YoungCrow-16x9.mp4')
                        log_path = out / f'ffmpeg-{fmt}.log'
                        started = time.monotonic()
                        with log_path.open('wb') as log:
                            encoder = subprocess.Popen(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning',
                                '-f', 'image2pipe', '-vcodec', 'mjpeg', '-framerate', str(args.fps), '-i', 'pipe:0',
                                '-i', str(audio), '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
                                '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', str(video)],
                                stdin=subprocess.PIPE, stderr=log)
                            try:
                                for frame in range(round(duration * args.fps)):
                                    data = page.evaluate("t=>{seekFilm(t);return document.querySelector('#film').toDataURL('image/jpeg',.94).split(',')[1]}", offset + frame / args.fps)
                                    encoder.stdin.write(base64.b64decode(data))
                                    if frame % (args.fps * 10) == 0:
                                        print(json.dumps({'format': fmt, 'seconds_rendered': frame / args.fps,
                                            'elapsed': round(time.monotonic() - started, 1)}), flush=True)
                                encoder.stdin.close()
                                if encoder.wait(timeout=120):
                                    raise RuntimeError(log_path.read_text())
                            finally:
                                if encoder.poll() is None:
                                    encoder.kill()
                                    encoder.wait()
                        if errors:
                            raise RuntimeError(errors)
                        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)]))
                        result = {'file': video.name, 'chapter':args.chapter, 'timeline_offset':offset, 'scene_count':len(scenes), 'sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
                                  'layout': metrics, 'errors': errors, 'probe': probe, 'render_seconds': round(time.monotonic() - started, 1)}
                        results.append(result)
                        print(json.dumps({'completed': video.name, 'bytes': video.stat().st_size}), flush=True)
                    finally:
                        page.close()
            finally:
                browser.close()
                browser = None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        # Also measure cleanup when a layout or rendering check fails.
        p = subprocess.run(['pgrep', '-af', 'chromium.*playwright_chromiumdev_profile'], capture_output=True, text=True)
        print(json.dumps({'browser_processes_after_close': p.stdout.splitlines()}), flush=True)
    if results:
        (out / 'render-evidence.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
