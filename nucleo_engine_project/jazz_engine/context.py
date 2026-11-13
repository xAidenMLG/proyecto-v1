"""Context Analyzer — FASE 5.

Construye el contexto armónico/dramático por sección a partir de un proyecto
``midi-forge/1`` YA COMPILADO por dark_director. Reutiliza ``forge.theory``
(parse_chord/parse_key) — no duplica teoría musical.

Independencia: jazz_engine NO importa dark_director. Los datos dramáticos
(energy/tension/focus) se leen de ``meta.director.original`` (el compilador
embebe el documento original) con fallback a los defaults del perfil.
"""
import copy

from forge import theory as T


class BarHarmony(object):
    """Estado armónico de un compás de una sección."""
    __slots__ = ('index', 'symbol', 'chord', 't0', 't1')

    def __init__(self, index, symbol, chord, t0, t1):
        self.index, self.symbol, self.chord = index, symbol, chord
        self.t0, self.t1 = t0, t1

    def pc_of(self, deg):
        return self.chord.tone(deg) if deg else None

    @property
    def chord_tone_pcs(self):
        """PCs de los tonos del acorde disponibles (raíz, 3ª/sus, 5ª, 7ª, 9ª...)."""
        out = []
        for d in (1, 3, 5, 7, 9, 13):
            pc = self.chord.tone(d, color=True)
            if pc is not None and pc not in out:
                out.append(pc)
        return out

    @property
    def guide_pcs(self):
        """Guías de jazz: 3ª y 7ª (o 4ª sus / 6ª si no hay séptima)."""
        out = []
        t3 = self.chord.tone(3)
        if t3 is not None:
            out.append(t3)
        t7 = self.chord.tone(7)
        if t7 is not None:
            out.append(t7)
        elif self.chord.tone(6) is not None:
            out.append(self.chord.tone(6))
        elif t3 is not None:                       # sus/acorde sin séptima
            out.append((self.chord.tone(1) + 7) % 12)
        return out

    @property
    def tension_pcs(self):
        """Tensiones disponibles (9, 11, 13) — color, nunca objetivo de resolución."""
        out = []
        for d in (9, 11, 13):
            pc = self.chord.tone(d, color=True)
            if pc is not None and pc not in self.chord_tone_pcs:
                out.append(pc)
        return out


class SectionContext(object):
    """Contexto completo de una sección para los motores de improvisación."""

    def __init__(self, sec_dict, index, start_bar, bb, original_entry, profile, key):
        self.d = sec_dict
        self.index = index
        self.id = sec_dict['id']
        self.kind = sec_dict.get('kind', 'verse')
        self.type = (original_entry or {}).get('type', self.kind if self.kind != 'pre' else 'pre_chorus')
        self.bars = int(sec_dict['bars'])
        self.start_bar = start_bar
        self.bb = bb
        self.t0 = start_bar * bb
        self.t1 = self.t0 + self.bars * bb
        self.key = key
        self.scale_pcs = T.scale_pcs(*key)

        # --- armonía por compás (reutiliza parse_chord; sin duplicación)
        cb = float(sec_dict.get('chord_bars', 1) or 1)
        chords = sec_dict.get('chords') or ['C']
        self.bar_harmony = []
        t = 0.0
        i = 0
        for k in range(self.bars):
            seg_start = k * bb
            sym = None
            # el acorde que suena al inicio del compás (ciclo de la progresión)
            while t <= seg_start + 1e-6:
                sym = chords[i % len(chords)]
                sym = sym.split(':')[0] if isinstance(sym, str) else str(sym.get('chord', 'C'))
                t += max(0.25, cb * bb)
                i += 1
            sym = sym.split(':')[0] if isinstance(sym, str) and ':' in sym else sym
            ch, _err = T.safe_chord(sym, key[0])
            self.bar_harmony.append(BarHarmony(k, sym, ch, seg_start, seg_start + bb))
        # acorde del compás SIGUIENTE al final de la sección (para resoluciones)
        nxt_sym = chords[i % len(chords)] if chords else 'C'
        nxt_sym = nxt_sym.split(':')[0] if isinstance(nxt_sym, str) and ':' in nxt_sym else nxt_sym
        self.next_chord_out = T.safe_chord(nxt_sym, key[0])[0]

        # --- datos dramáticos: entrada original del compositor con fallback al perfil
        oe = original_entry or {}
        self.energy = float(oe.get('energy', profile.ENERGY_BASE.get(self.type, 0.5)))
        self.tension = float(oe.get('tension', profile.TENSION_BASE.get(self.type, 0.4)))
        self.focus = list(oe.get('focus') or profile.FOCUS_DEFAULT.get(self.type, []))
        self.occurrence = int(oe.get('occurrence', 0)) if oe.get('occurrence') is not None else 0
        self.final = bool(sec_dict.get('final'))

    # ------------------------------------------------------------------
    def harmony_at_bar(self, k):
        return self.bar_harmony[max(0, min(self.bars - 1, k))]

    def next_harmony(self, k):
        """Acorde del compás k+1 (o el primero de la sección siguiente)."""
        if k + 1 < self.bars:
            return self.bar_harmony[k + 1]
        return BarHarmony(self.bars, self.next_chord_out.symbol, self.next_chord_out,
                          self.bars * self.bb, (self.bars + 1) * self.bb)

    def snap_to_scale(self, pitch, lo, hi):
        """Pitch más cercano dentro de la escala en [lo, hi]."""
        best, bd = None, 999
        for p in range(lo, hi + 1):
            if p % 12 in self.scale_pcs:
                d = abs(p - pitch)
                if d < bd:
                    best, bd = p, d
        return best if best is not None else max(lo, min(hi, pitch))

    def snap_to_chord_tone(self, pitch, bh, lo, hi):
        pcs = bh.chord_tone_pcs
        best, bd = None, 999
        for p in range(lo, hi + 1):
            if p % 12 in pcs:
                d = abs(p - pitch)
                if d < bd:
                    best, bd = p, d
        return best

    def nearest_pitch_with_pc(self, pc, near, lo, hi):
        cands = [p for p in range(lo, hi + 1) if p % 12 == pc]
        if not cands:
            return None
        return min(cands, key=lambda p: abs(p - near))


def build_contexts(project, profile):
    """Contextos por sección de un proyecto compilado (determinista, sin estado)."""
    g = project.get('global') or {}
    ts = g.get('time_signature') or [4, 4]
    bb = int(ts[0]) * 4.0 / int(ts[1])
    key = T.parse_key(g.get('key') or 'C major')
    original = ((project.get('meta') or {}).get('director') or {}).get('original') or {}
    orig_by_id = {}
    orig_by_type = {}
    for s in original.get('structure') or []:
        orig_by_id[s.get('id')] = s
        orig_by_type.setdefault(s.get('type'), s)
    out = []
    bar = 0
    for idx, sec in enumerate(project.get('sections') or []):
        oe = orig_by_id.get(sec['id'], orig_by_type.get(sec.get('kind')))
        out.append(SectionContext(sec, idx, bar, bb, oe, profile, key))
        bar += int(sec['bars'])
    return out
