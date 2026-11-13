"""Render opcional a WAV/MP3 con FluidSynth (+ ffmpeg o lame) para Windows/Linux/macOS."""
import io
import os
import random
import re
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_fluidsynth():
    cands = [os.environ.get('MIDI_FORGE_FLUIDSYNTH'), shutil.which('fluidsynth'), shutil.which('fluidsynth.exe')]
    for base in (ROOT / 'tools', ROOT / 'tools' / 'fluidsynth' / 'bin', Path('C:/tools/fluidsynth/bin'),
                 Path('C:/Program Files/FluidSynth/bin')):
        for name in ('fluidsynth.exe', 'fluidsynth'):
            cands.append(str(base / name))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def find_soundfont(explicit=None):
    cands = [explicit, os.environ.get('MIDI_FORGE_SF2')]
    for d in (ROOT / 'soundfonts', Path('/usr/share/sounds/sf2'), Path('C:/soundfonts'), Path.home() / 'soundfonts'):
        if d.is_dir():
            cands += [str(p) for p in sorted(d.glob('*.sf2')) + sorted(d.glob('*.sf3'))]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def find_ffmpeg():
    cands = [os.environ.get('MIDI_FORGE_FFMPEG'), shutil.which('ffmpeg'), shutil.which('ffmpeg.exe')]
    for base in (ROOT / 'tools', ROOT / 'tools' / 'ffmpeg' / 'bin', Path('C:/ffmpeg/bin'), Path('C:/tools/ffmpeg/bin')):
        for name in ('ffmpeg.exe', 'ffmpeg'):
            cands.append(str(base / name))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def find_lame():
    cands = [os.environ.get('MIDI_FORGE_LAME'), shutil.which('lame'), shutil.which('lame.exe')]
    for base in (ROOT / 'tools', Path('C:/lame'), Path('C:/tools/lame')):
        for name in ('lame.exe', 'lame'):
            cands.append(str(base / name))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def status():
    fs, sf = find_fluidsynth(), find_soundfont()
    ff, lm = find_ffmpeg(), find_lame()
    return {'available': bool(fs and sf), 'fluidsynth': fs, 'soundfont': sf,
            'mp3': bool(fs and sf and (ff or lm)), 'ffmpeg': ff, 'lame': lm}


def render_wav(midi_bytes, soundfont=None, gain=0.5, rate=44100):
    fs, sf = find_fluidsynth(), find_soundfont(soundfont)
    if not fs:
        raise RuntimeError('FluidSynth no encontrado (instalalo o define MIDI_FORGE_FLUIDSYNTH).')
    if not sf:
        raise RuntimeError('Soundfont .sf2 no encontrado (copialo a la carpeta soundfonts/ o define MIDI_FORGE_SF2).')
    with tempfile.TemporaryDirectory() as td:
        mid, wav = os.path.join(td, 'in.mid'), os.path.join(td, 'out.wav')
        with open(mid, 'wb') as f:
            f.write(midi_bytes)
        cmd = [fs, '-ni', '-g', str(gain), '-F', wav, '-r', str(rate), sf, mid]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if r.returncode != 0 or not os.path.isfile(wav):
            raise RuntimeError('FluidSynth fallo: ' + r.stderr.decode('utf-8', 'replace')[-300:])
        with open(wav, 'rb') as f:
            return f.read()


def _wav_info(wav_bytes):
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return w.getnframes(), w.getframerate(), w.getnchannels()


def wav_to_mp3(wav_bytes, bitrate=192):
    """WAV -> MP3 con ffmpeg (libmp3lame) o lame. Lanza RuntimeError si no hay codificador."""
    ff, lm = find_ffmpeg(), find_lame()
    if not (ff or lm):
        raise RuntimeError('No hay codificador MP3 en el servidor (ffmpeg o lame). Se usara el del navegador.')
    with tempfile.TemporaryDirectory() as td:
        wav, mp3 = os.path.join(td, 'in.wav'), os.path.join(td, 'out.mp3')
        with open(wav, 'wb') as f:
            f.write(wav_bytes)
        if ff:
            cmd = [ff, '-y', '-loglevel', 'error', '-i', wav, '-codec:a', 'libmp3lame', '-b:a', '%dk' % bitrate, mp3]
        else:
            cmd = [lm, '--silent', '-b', str(bitrate), wav, mp3]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        if r.returncode != 0 or not os.path.isfile(mp3):
            raise RuntimeError('La codificacion MP3 fallo: ' + r.stderr.decode('utf-8', 'replace')[-300:])
        with open(mp3, 'rb') as f:
            return f.read()


def render_mp3(midi_bytes, soundfont=None, gain=0.5, bitrate=192, fx=None, sections=None):
    """MIDI -> MP3. Con `fx` (proyecto.render) aplica lowpass, ruido (hiss/crackle), loudnorm y fade usando ffmpeg.
    Devuelve (bytes, lista_de_efectos_aplicados)."""
    wav = render_wav(midi_bytes, soundfont, gain)
    if fx and fx.get('enabled', True) and find_ffmpeg():
        return master(wav, fx, sections or [], 'mp3', bitrate)
    return wav_to_mp3(wav, bitrate), ([] if not fx else ['omitido: FX requieren ffmpeg'])


def _profile_gain(profile, kind):
    profile = profile or {}
    return float(profile.get(kind, profile.get('default', 1.0)))


def _gain_expr(sections, profile, base):
    """Expresion de ffmpeg (volume, eval=frame) con una ganancia por seccion segun su tipo."""
    segs = []
    for kind, t0, t1 in sections:
        g = base * _profile_gain(profile, kind)
        if segs and abs(segs[-1][2] - g) < 1e-9 and abs(segs[-1][1] - t0) < 1e-6:
            segs[-1][1] = t1
        else:
            segs.append([t0, t1, g])
    expr = '%.6f' % (base * _profile_gain(profile, 'default'))
    for t0, t1, g in reversed(segs):
        expr = 'if(between(t,%.3f,%.3f),%.6f,%s)' % (t0, t1, g, expr)
    return expr


def _write_hiss(path, secs, rate):
    n = int(secs * rate)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
        chunk = 1 << 20
        left = n * 4
        while left > 0:
            k = min(chunk, left)
            w.writeframes(os.urandom(k))
            left -= k


def _write_crackle(path, secs, rate, per_second, level, sections, profile, seed=1):
    rng = random.Random(seed)
    n = int(secs * rate)
    buf = bytearray(n * 4)
    clicks = int(secs * per_second)
    for _ in range(clicks):
        t = rng.uniform(0, secs - 0.2)
        kind = next((k for k, a, b in sections if a <= t < b), 'default')
        amp = level * _profile_gain(profile, kind) * rng.uniform(0.25, 1.0) * 32767
        pos = int(t * rate)
        sign = rng.choice((-1, 1))
        for i in range(rng.randint(14, 48)):
            v = int(amp * sign * (0.82 ** i) * (1 if i % 2 == 0 else -0.6))
            o = (pos + i) * 4
            if o + 4 <= len(buf):
                struct.pack_into('<hh', buf, o, v, int(v * rng.uniform(0.6, 1.0)))
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(bytes(buf))


def _run_ffmpeg(cmd, script, graph_text, dst_args, timeout=900):
    with open(script, 'w', encoding='utf-8') as f:
        f.write(graph_text)
    r = subprocess.run(cmd + ['-filter_complex_script', script, '-map', '[out]'] + dst_args, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout)
    return r


def _loudnorm_measure(stderr_text):
    """Extrae el bloque JSON que imprime loudnorm (print_format=json)."""
    import json as _json
    m = None
    for m in re.finditer(r'\{[^{}]*"input_i"[^{}]*\}', stderr_text, re.S):
        pass
    return _json.loads(m.group(0)) if m else None


def master(wav_bytes, fx, sections, out='mp3', bitrate=192):
    """Cadena de masterizacion con ffmpeg: [ruido] -> lowpass -> loudnorm (2 pasadas) -> fade. -> (bytes, efectos)"""
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError('Los Render FX necesitan ffmpeg (PATH, tools\\ o MIDI_FORGE_FFMPEG).')
    nfr, rate, ch = _wav_info(wav_bytes)
    secs = nfr / float(rate)
    applied, labels = [], ['[m]']
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, 'music.wav')
        with open(src, 'wb') as f:
            f.write(wav_bytes)
        cmd = [ff, '-y', '-loglevel', 'info', '-nostats', '-i', src]
        graph = ['[0:a]anull[m]']
        noise = fx.get('noise') or {}
        idx = 1
        if noise.get('hiss'):
            hp = os.path.join(td, 'hiss.wav')
            _write_hiss(hp, secs, rate)
            cmd += ['-i', hp]
            graph.append("[%d:a]volume='%s':eval=frame[h]" % (idx, _gain_expr(sections, noise['hiss'].get('profile'), float(noise['hiss'].get('level', 0.0012)))))
            labels.append('[h]')
            idx += 1
            applied.append('hiss')
        if noise.get('crackle'):
            cp = os.path.join(td, 'crackle.wav')
            c = noise['crackle']
            _write_crackle(cp, secs, rate, float(c.get('per_second', 3)), float(c.get('level', 0.03)), sections, c.get('profile'))
            cmd += ['-i', cp]
            graph.append('[%d:a]anull[c]' % idx)
            labels.append('[c]')
            idx += 1
            applied.append('crackle')
        pre = []
        if len(labels) > 1:
            pre.append('%samix=inputs=%d:duration=first:dropout_transition=0,volume=%d' % (''.join(labels), len(labels), len(labels)))
        else:
            pre.append('[m]anull')
        if fx.get('lowpass_hz'):
            pre.append('lowpass=f=%d' % int(fx['lowpass_hz']))
            applied.append('lowpass %d Hz' % int(fx['lowpass_hz']))
        script = os.path.join(td, 'graph.txt')
        dst = os.path.join(td, 'out.' + ('mp3' if out == 'mp3' else 'wav'))
        codec = ['-codec:a', 'libmp3lame', '-b:a', '%dk' % bitrate] if out == 'mp3' else ['-c:a', 'pcm_s16le']
        post = []
        target = fx.get('loudness_lufs')
        if target is not None:
            target = float(target)
            ln = 'loudnorm=I=%g:TP=-1.5:LRA=11' % target
            meas = None
            try:      # pasada 1: medir
                r1 = _run_ffmpeg(cmd, script, ';\n'.join(graph + [','.join(pre + [ln + ':print_format=json']) + '[out]']), ['-f', 'null', os.devnull])
                meas = _loudnorm_measure(r1.stderr.decode('utf-8', 'replace'))
            except Exception:  # noqa: BLE001
                meas = None
            if meas:
                ln += ':measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true' % (
                    meas['input_i'], meas['input_tp'], meas['input_lra'], meas['input_thresh'], meas['target_offset'])
                applied.append('loudnorm %g LUFS (2 pasadas)' % target)
            else:
                applied.append('loudnorm %g LUFS (1 pasada)' % target)
            post.append(ln + ',aresample=%d' % rate)
        fade = float(fx.get('fade_out_seconds') or 0)
        if fade > 0 and secs > fade:
            post.append('afade=t=out:st=%.2f:d=%.2f:curve=%s' % (secs - fade, fade, 'exp' if fx.get('fade_curve') == 'exp' else 'tri'))
            applied.append('fade %.0f s' % fade)
        r = _run_ffmpeg(cmd, script, ';\n'.join(graph + [','.join(pre + post) + '[out]']), codec + [dst])
        if r.returncode != 0 or not os.path.isfile(dst):
            raise RuntimeError('ffmpeg fallo al aplicar los Render FX: ' + r.stderr.decode('utf-8', 'replace')[-400:])
        with open(dst, 'rb') as f:
            return f.read(), applied
