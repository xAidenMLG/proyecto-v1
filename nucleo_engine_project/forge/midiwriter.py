"""Escritor MIDI (formato 1) en Python puro, sin dependencias, + lector minimo para verificacion."""
import math
import struct


def vlq(n):
    n = max(0, int(n))
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


# orden dentro del mismo tick: meta, controles, note-off, note-on
_META, _CTRL, _OFF, _ON = 0, 1, 2, 3


class MidiTrack(object):
    def __init__(self, name=None):
        self.ev = []
        if name:
            self.meta(0, 0x03, str(name).encode('utf-8', 'replace'))

    def meta(self, tick, typ, data):
        self.ev.append((int(tick), _META, bytes([0xFF, typ]) + vlq(len(data)) + data))

    def tempo(self, tick, bpm):
        self.meta(tick, 0x51, struct.pack('>I', int(round(60000000.0 / bpm)))[1:])

    def timesig(self, tick, num, den):
        dd = max(0, int(round(math.log(den, 2))))
        self.meta(tick, 0x58, bytes([num, dd, 24, 8]))

    def keysig(self, tick, sf, mi):
        self.meta(tick, 0x59, struct.pack('>bB', sf, mi))

    def marker(self, tick, text):
        self.meta(tick, 0x06, str(text).encode('utf-8', 'replace'))

    def program(self, tick, ch, prog):
        self.ev.append((int(tick), _CTRL, bytes([0xC0 | ch, prog & 0x7F])))

    def cc(self, tick, ch, num, val):
        self.ev.append((int(tick), _CTRL, bytes([0xB0 | ch, num & 0x7F, max(0, min(127, int(val)))])))

    def bend(self, tick, ch, val):
        v = max(0, min(16383, int(val) + 8192))
        self.ev.append((int(tick), _CTRL, bytes([0xE0 | ch, v & 0x7F, (v >> 7) & 0x7F])))

    def note(self, tick, dur, ch, pitch, vel):
        pitch = max(0, min(127, int(pitch)))
        vel = max(1, min(127, int(vel)))
        tick = max(0, int(tick))
        dur = max(1, int(dur))
        self.ev.append((tick, _ON, bytes([0x90 | ch, pitch, vel])))
        self.ev.append((tick + dur, _OFF, bytes([0x80 | ch, pitch, 0])))

    def to_bytes(self):
        evs = sorted(self.ev, key=lambda e: (e[0], e[1]))
        out, last = bytearray(), 0
        for tick, _, data in evs:
            out += vlq(tick - last) + data
            last = tick
        out += vlq(0) + b'\xff\x2f\x00'
        return b'MTrk' + struct.pack('>I', len(out)) + bytes(out)


def build_midi(tracks, ticks_per_beat):
    head = b'MThd' + struct.pack('>IHHH', 6, 1, len(tracks), ticks_per_beat)
    return head + b''.join(t.to_bytes() for t in tracks)


# --------------------------------------------------------------------------
# Lector minimo (para tests y verificacion del archivo generado)
# --------------------------------------------------------------------------
def read_midi(data):
    """-> dict(format, tpb, tracks=[dict(name, notes=[(tick,dur,ch,pitch,vel)], cc=[...], bends=[...], tempo=[...])])"""
    assert data[:4] == b'MThd', 'cabecera MIDI invalida'
    fmt, ntrk, tpb = struct.unpack('>HHH', data[8:14])
    pos, tracks = 14, []
    for _ in range(ntrk):
        assert data[pos:pos + 4] == b'MTrk'
        ln = struct.unpack('>I', data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + ln]
        pos += 8 + ln
        i, tick, run = 0, 0, None
        t = dict(name='', notes=[], cc=[], bends=[], tempo=[], markers=[], programs=[], keysig=None, timesig=None)
        active = {}
        while i < len(body):
            d, sh = 0, 0
            while True:
                b = body[i]
                i += 1
                d = (d << 7) | (b & 0x7F)
                if not b & 0x80:
                    break
            tick += d
            st = body[i]
            if st == 0xFF:
                typ, i = body[i + 1], i + 2
                ln2, sh = 0, 0
                while True:
                    b = body[i]
                    i += 1
                    ln2 = (ln2 << 7) | (b & 0x7F)
                    if not b & 0x80:
                        break
                dat = body[i:i + ln2]
                i += ln2
                if typ == 0x03:
                    t['name'] = dat.decode('utf-8', 'replace')
                elif typ == 0x06:
                    t['markers'].append((tick, dat.decode('utf-8', 'replace')))
                elif typ == 0x51:
                    t['tempo'].append((tick, int.from_bytes(dat, 'big')))
                elif typ == 0x58:
                    t['timesig'] = (dat[0], 2 ** dat[1])
                elif typ == 0x59:
                    t['keysig'] = struct.unpack('>bB', dat)
                continue
            if st & 0x80:
                run = st
                i += 1
            st = run
            kind, ch = st & 0xF0, st & 0x0F
            if kind in (0x80, 0x90):
                p, v = body[i], body[i + 1]
                i += 2
                if kind == 0x90 and v > 0:
                    active.setdefault((ch, p), []).append((tick, v))
                else:
                    lst = active.get((ch, p))
                    if lst:
                        t0, v0 = lst.pop(0)
                        t['notes'].append((t0, tick - t0, ch, p, v0))
            elif kind == 0xB0:
                t['cc'].append((tick, ch, body[i], body[i + 1]))
                i += 2
            elif kind == 0xE0:
                t['bends'].append((tick, ch, (body[i] | (body[i + 1] << 7)) - 8192))
                i += 2
            elif kind == 0xC0:
                t['programs'].append((tick, ch, body[i]))
                i += 1
            elif kind == 0xD0:
                i += 1
            elif kind == 0xA0:
                i += 2
            else:
                raise ValueError('evento MIDI no soportado: %x' % st)
        t['notes'].sort()
        tracks.append(t)
    return dict(format=fmt, tpb=tpb, tracks=tracks)
