#!/usr/bin/env python3
"""MIDI Forge - servidor local (solo libreria estandar). Uso:
    python app.py                      -> abre la interfaz en http://127.0.0.1:8765
    python app.py --cli in.json -o out.mid [--preset synthwave|triphop] [--seed N]
"""
import argparse
import json
import os
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors='replace')
    except Exception:  # noqa: BLE001
        pass
sys.path.insert(0, str(ROOT))

from forge import __version__, adapter, audio, engine, styles, theory, validate  # noqa: E402

WEB = ROOT / 'web'
EXAMPLES = ROOT / 'examples'
OUTPUT = ROOT / 'output'
MIME = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8',
        '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml'}


def meta():
    return {
        'version': __version__, 'roles': styles.ROLES, 'kinds': styles.KINDS, 'presets': styles.PRESETS,
        'style_schema': styles.STYLE_SCHEMA, 'role_defaults': styles.ROLE_DEFAULTS,
        'drum_presets': styles.DRUM_PRESETS, 'bass_sets': styles.BASS_SETS, 'arp_patterns': styles.ARP_PATTERNS,
        'gm_names': theory.GM_NAMES, 'drum_notes': theory.DRUM_NOTES, 'wav': audio.status(), 'mp3': audio.status()['mp3'],
        'voicing_profiles': sorted(__import__('forge.voicing', fromlist=['PROFILES']).PROFILES),
    }


def run_generate(project, preset=None):
    project, rep = adapter.normalize(project, preset)
    res = engine.generate(project)
    val = validate.validate(res)
    return project, rep, res, val


def section_times(res):
    spb = 60.0 / res.ctx.bpm
    return [(s.kind, s.t0 * spb, s.t1 * spb) for s in res.ctx.secs]


def summary(res, val):
    return {'bars': val['bars'], 'duration_seconds': val['duration_seconds'], 'notes': val['note_counts'],
            'midi_bytes': len(res.midi)}


class Handler(BaseHTTPRequestHandler):
    server_version = 'MidiForge/' + __version__

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype='application/json; charset=utf-8', extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        elif isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(n) if n else b'{}'
        return json.loads(raw.decode('utf-8') or '{}')

    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path == '/api/meta':
                return self._send(200, meta())
            if u.path == '/api/examples':
                items = [{'name': p.stem, 'file': p.name} for p in sorted(EXAMPLES.glob('*.json'))]
                return self._send(200, items)
            if u.path == '/api/example':
                name = os.path.basename(parse_qs(u.query).get('name', [''])[0])
                p = EXAMPLES / name
                if not p.is_file():
                    return self._send(404, {'error': 'ejemplo no encontrado'})
                return self._send(200, p.read_text(encoding='utf-8'))
            path = u.path.lstrip('/') or 'index.html'
            f = (WEB / path).resolve()
            if WEB.resolve() not in f.parents and f != WEB.resolve() or not f.is_file():
                return self._send(404, {'error': 'no encontrado'})
            return self._send(200, f.read_bytes(), MIME.get(f.suffix, 'application/octet-stream'))
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self._send(500, {'error': str(e)})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            data = self._body()
            if u.path == '/api/normalize':
                project, rep = adapter.normalize(data.get('json'), data.get('preset'))
                return self._send(200, {'project': project, 'report': rep})
            if u.path == '/api/generate':
                project, rep, res, val = run_generate(data['project'], data.get('preset'))
                return self._send(200, {'project': project, 'report': rep, 'validation': val,
                                        'events': engine.to_events(res), 'midi_b64': engine.midi_b64(res),
                                        'summary': summary(res, val)})
            if u.path == '/api/events':
                project, rep, res, val = run_generate(data['project'])
                return self._send(200, engine.export_events(res))
            if u.path == '/api/suggest_lead':
                project, _ = adapter.normalize(data['project'])
                ctx = engine.Ctx(project)
                sec = next((s for s in ctx.secs if s.id == data['section_id']), None)
                if sec is None:
                    return self._send(400, {'error': 'seccion desconocida'})
                lead = next((t for t in project['tracks'] if t['role'] == 'lead'), None)
                p = dict(styles.style_defaults('lead', 'generative'), **(data.get('params') or {}))
                rng = ctx.rng('suggest', sec.id, data.get('seed', 0))
                notes = engine.generate_phrase(ctx, sec, 0, sec.bars, p, rng, lead)
                for n in notes:
                    n['bar'] = n['bar']
                    n['pitch'] = theory.midi_name(n['pitch'])
                return self._send(200, {'notes': notes})
            if u.path == '/api/default_block':
                sec = dict(data.get('section') or {}, kind=data.get('kind', 'verse'), bars=data.get('bars', 8))
                return self._send(200, styles.default_block(data.get('preset', 'synthwave'), sec, data['role']))
            if u.path == '/api/apply_preset':
                project, _ = adapter.normalize(data['project'])
                pre = data['preset']
                project['global']['preset'] = pre
                for s in project['sections']:
                    for t in project['tracks']:
                        if data.get('tracks') in (None, 'all') or t['id'] in data['tracks']:
                            s['blocks'][t['id']] = styles.default_block(pre, s, t['role'])
                if data.get('automation', True):
                    project['automation'] = styles.default_automation(pre, project['sections'])
                return self._send(200, {'project': project})
            if u.path == '/api/mp3':
                project, rep, res, val = run_generate(data['project'])
                fx = project.get('render') if data.get('fx', True) else None
                mp3, applied = audio.render_mp3(res.midi, data.get('soundfont'), float(data.get('gain', 0.5)), int(data.get('bitrate', 192)),
                                                fx, section_times(res))
                return self._send(200, mp3, 'audio/mpeg', {'X-Forge-FX': ','.join(applied) or 'ninguno', 'Access-Control-Expose-Headers': 'X-Forge-FX'})
            if u.path == '/api/wav':
                project, rep, res, val = run_generate(data['project'])
                wav = audio.render_wav(res.midi, data.get('soundfont'), float(data.get('gain', 0.5)))
                applied = []
                fx = project.get('render') if data.get('fx', True) else None
                if fx and fx.get('enabled', True) and audio.find_ffmpeg():
                    wav, applied = audio.master(wav, fx, section_times(res), 'wav')
                return self._send(200, wav, 'audio/wav', {'X-Forge-FX': ','.join(applied) or 'ninguno', 'Access-Control-Expose-Headers': 'X-Forge-FX'})
            if u.path == '/api/save':
                project, rep, res, val = run_generate(data['project'])
                OUTPUT.mkdir(exist_ok=True)
                name = theory.slug(data.get('name') or project.get('meta', {}).get('name') or 'proyecto') or 'proyecto'
                (OUTPUT / (name + '.mid')).write_bytes(res.midi)
                (OUTPUT / (name + '.project.json')).write_text(json.dumps(project, ensure_ascii=False, indent=1), encoding='utf-8')
                return self._send(200, {'saved': [str(OUTPUT / (name + '.mid')), str(OUTPUT / (name + '.project.json'))]})
            return self._send(404, {'error': 'ruta desconocida'})
        except ValueError as e:
            return self._send(400, {'error': str(e)})
        except KeyError as e:
            return self._send(400, {'error': 'falta el campo %s' % e})
        except RuntimeError as e:
            return self._send(501, {'error': str(e)})
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self._send(500, {'error': '%s: %s' % (type(e).__name__, e)})


def serve(port, open_browser=True):
    srv = None
    for p in range(port, port + 10):
        try:
            srv = ThreadingHTTPServer(('127.0.0.1', p), Handler)
            port = p
            break
        except OSError:
            continue
    if srv is None:
        raise SystemExit('No hay puertos libres entre %d y %d.' % (port, port + 9))
    url = 'http://127.0.0.1:%d' % port
    print('MIDI Forge %s  ->  %s   (Ctrl+C para salir)' % (__version__, url))
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nCerrando.')
    finally:
        srv.server_close()


def cli(args):
    obj = json.loads(Path(args.cli).read_text(encoding='utf-8'))
    if args.seed is not None:
        obj.setdefault('global', {})['seed'] = args.seed
    project, rep, res, val = run_generate(obj, args.preset)
    out = Path(args.output or (Path(args.cli).stem + '.mid'))
    out.write_bytes(res.midi)
    if args.project_out:
        Path(args.project_out).write_text(json.dumps(project, ensure_ascii=False, indent=1), encoding='utf-8')
    for r in rep:
        print('[%s] %s' % (r['level'], r['msg']))
    if args.mp3:
        data, applied = audio.render_mp3(res.midi, gain=args.gain, fx=project.get('render'), sections=section_times(res))
        Path(args.mp3).write_bytes(data)
        print('FX aplicados:', ', '.join(applied) or 'ninguno')
        print('MP3 ->', args.mp3)
    print('OK ->', out, '|', val['bars'], 'compases,', val['duration_seconds'], 's | choques:', val['semitone_clashes_unintended'],
          '| notas:', val['note_counts'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='MIDI Forge')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--cli', metavar='JSON', help='generar sin interfaz')
    ap.add_argument('-o', '--output')
    ap.add_argument('--project-out', help='guardar tambien el proyecto normalizado')
    ap.add_argument('--preset', choices=styles.PRESETS)
    ap.add_argument('--seed', type=int)
    ap.add_argument('--gain', type=float, default=0.35, help='ganancia de FluidSynth para --mp3 (0.2-0.6)')
    ap.add_argument('--mp3', metavar='ARCHIVO', help='ademas, renderizar un MP3 (requiere FluidSynth + soundfont + ffmpeg/lame)')
    a = ap.parse_args()
    if a.cli:
        cli(a)
    else:
        serve(a.port, not a.no_browser)
