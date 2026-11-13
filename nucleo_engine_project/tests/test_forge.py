"""Pruebas de MIDI Forge:  python -m unittest discover -s tests -v   (solo libreria estandar)"""
import copy
import json
import sys
import threading
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from forge import adapter, audio, engine, styles, theory as T, validate, voicing  # noqa: E402
from forge.midiwriter import MidiTrack, build_midi, read_midi  # noqa: E402

NEON = json.loads((ROOT / 'examples' / 'neon_rain_v2_spec.json').read_text(encoding='utf-8'))
SHADOW = json.loads((ROOT / 'examples' / 'shadow_corner.json').read_text(encoding='utf-8'))
HYBRID = json.loads((ROOT / 'examples' / 'shadow_corner_hybrid.json').read_text(encoding='utf-8'))


def build(obj):
    p, rep = adapter.normalize(copy.deepcopy(obj))
    res = engine.generate(p)
    return p, rep, res, validate.validate(res)


class TheoryTests(unittest.TestCase):
    def test_pitch_and_names(self):
        self.assertEqual(T.parse_pitch('C4'), 60)
        self.assertEqual(T.parse_pitch('Bb3'), 58)
        self.assertEqual(T.parse_pitch('F#5'), 78)
        self.assertEqual(T.parse_pitch(64), 64)
        self.assertEqual(T.midi_name(61), 'Db4')
        with self.assertRaises(ValueError):
            T.parse_pitch('ZZ')

    def test_chords(self):
        c = T.parse_chord('Dm9')
        self.assertEqual((c.root, c.deg[3], c.deg[7], c.deg[9]), (2, 3, 10, 2))
        self.assertEqual(T.parse_chord('Bbmaj7').deg[7], 11)
        self.assertEqual(T.parse_chord('C(add9)').deg[9], 2)
        s = T.parse_chord('Csus4')
        self.assertFalse(s.true_third)
        self.assertEqual(s.deg[3], 5)
        self.assertEqual(T.parse_chord('F/A').bass, 9)
        self.assertEqual(T.parse_chord('Edim7').deg[7], 9)
        for sym in ('Am7', 'G7#9', 'Cmaj13', 'Bbsus2', 'A+', 'C5', 'Dm7b5'):
            T.parse_chord(sym)
        with self.assertRaises(ValueError):
            T.parse_chord('Zz9')

    def test_key_and_gm(self):
        self.assertEqual(T.parse_key('D minor (1 bemol)'), (2, 'aeolian'))
        self.assertEqual(T.parse_key('F# dorian'), (6, 'dorian'))
        self.assertEqual(T.key_signature(2, 'aeolian'), (-1, 1))
        self.assertEqual(T.resolve_program('Pad 4 (choir)'), 91)
        self.assertEqual(T.resolve_program('synth-bass-1'), 38)
        self.assertEqual(T.resolve_program(33), 33)


class MidiTests(unittest.TestCase):
    def test_roundtrip(self):
        t = MidiTrack('x')
        t.tempo(0, 92)
        t.timesig(0, 4, 4)
        t.program(0, 0, 88)
        t.bend(10, 0, -1000)
        t.note(0, 480, 0, 60, 90)
        t.note(480, 240, 0, 64, 70)
        m = read_midi(build_midi([t], 480))
        tr = m['tracks'][0]
        self.assertEqual(tr['name'], 'x')
        self.assertEqual([(n[0], n[1], n[3], n[4]) for n in tr['notes']], [(0, 480, 60, 90), (480, 240, 64, 70)])
        self.assertEqual(tr['bends'][0][2], -1000)


class VoicingTests(unittest.TestCase):
    def test_smooth_voice_leading(self):
        ev = [(T.parse_chord(c), voicing.resolve_profile('full'), 48, 76) for c in ['Dm', 'Bb', 'F', 'C'] * 3]
        seq = voicing.voice_sequence(ev)
        for a, b in zip(seq, seq[1:]):
            self.assertLessEqual(max(abs(x - y) for x, y in zip(a, b)), 5)
        for v in seq:
            gaps = [y - x for x, y in zip(v, v[1:])]
            self.assertTrue(all(5 <= g <= 15 for g in gaps), v)

    def test_bare_has_no_third(self):
        ch = T.parse_chord('Dm')
        v = voicing.voice_sequence([(ch, voicing.resolve_profile('bare'), 48, 76)])[0]
        self.assertNotIn(5, {p % 12 for p in v})


class AdapterTests(unittest.TestCase):
    def test_neon_spec(self):
        p, rep = adapter.normalize(copy.deepcopy(NEON))
        self.assertEqual(len(p['sections']), 7)
        self.assertEqual([t['role'] for t in p['tracks']], ['pad', 'bass', 'lead', 'strings', 'arp', 'drums'])
        self.assertEqual(p['global']['preset'], 'synthwave')
        self.assertEqual(p['sections'][5]['chords'][0], 'Dm9')       # "Coro final" -> progresion "chorus"
        self.assertEqual(sum(s['bars'] for s in p['sections']), 88)
        outro = p['sections'][6]['blocks']
        self.assertEqual(outro['arp']['to_bar'], 6)
        self.assertTrue(p['ending']['tape_stop']['enabled'])

    def test_shadow_spec(self):
        p, rep = adapter.normalize(copy.deepcopy(SHADOW))
        self.assertEqual(p['global']['preset'], 'triphop')
        self.assertEqual([t['channel'] for t in p['tracks']], [1, 2, 3, 4, 5, 10])
        self.assertEqual(p['tracks'][1]['program'], 33)
        self.assertEqual(p['sections'][1]['chord_bars'], 2.0)
        counts = {k: len(v) for k, v in p['lead']['phrases'].items()}
        self.assertEqual(counts, {'verse_1': 14, 'bridge': 3, 'chorus': 17, 'verse_2': 16, 'final_chorus': 17, 'outro': 3})
        self.assertEqual(p['sections'][1]['blocks']['strings']['params']['modes_by_cycle'], {'0': 'full', '1': 'bare'})
        self.assertEqual(p['sections'][4]['blocks']['strings']['params']['modes'], ['bare', 'full'])
        self.assertAlmostEqual(p['tracks'][5]['drum_humanize']['snare'], 26 / 480.0)

    def test_canonical_is_idempotent(self):
        p, _ = adapter.normalize(copy.deepcopy(NEON))
        p2, _ = adapter.normalize(json.loads(json.dumps(p)))
        self.assertEqual(engine.generate(p).midi, engine.generate(p2).midi)

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            adapter.normalize('{no es json')
        with self.assertRaises(ValueError):
            adapter.normalize([1, 2])
        p, rep = adapter.normalize({})
        self.assertTrue(engine.generate(p).midi)


class EngineTests(unittest.TestCase):
    def test_neon_quality(self):
        p, rep, res, v = build(NEON)
        self.assertEqual(v['bars'], 88)
        self.assertEqual(v['semitone_clashes_unintended'], 0)
        self.assertEqual(v['empty_sections'], [])
        self.assertLessEqual(v['max_pitched_polyphony']['ignoring_legato_overlap'], 10)
        self.assertLessEqual(v['voice_leading']['strings']['max_movement'], 5)
        m = read_midi(res.midi)
        self.assertEqual(m['tracks'][0]['keysig'], (-1, 1))
        self.assertEqual(len(m['tracks'][0]['markers']), 7)
        used = {n[2] for t in m['tracks'][1:] for n in t['notes']}
        self.assertEqual(used, {0, 1, 2, 3, 4, 9})
        vmax = max(n[4] for t in m['tracks'][1:5] for n in t['notes'])
        self.assertLessEqual(vmax, 110)

    def test_shadow_quality(self):
        p, rep, res, v = build(SHADOW)
        self.assertEqual(v['bars'], 88)
        self.assertEqual(v['semitone_clashes_unintended'], 0)
        self.assertEqual(v['lead_notes_by_section']['verse_1'], 14)
        self.assertEqual(v['lead_notes_by_section']['chorus'], 17)
        self.assertTrue(30 <= v['snare_avg_delay_ms'] <= 45)

    def test_deterministic_and_seed(self):
        a = build(NEON)[2].midi
        b = build(NEON)[2].midi
        self.assertEqual(a, b)
        o = copy.deepcopy(NEON)
        o['global']['seed'] = 7
        self.assertNotEqual(a, build(o)[2].midi)

    def test_block_independence(self):
        p, _, res, _ = build(NEON)
        q = copy.deepcopy(p)
        q['sections'][3]['blocks']['bass']['enabled'] = False
        r2 = engine.generate(q)
        by = lambda r, tid: [(round(n.t, 4), n.p) for b in r.bufs if b.track['id'] == tid for n in b.notes]
        self.assertEqual(by(res, 'lead'), by(r2, 'lead'))          # otras pistas no cambian
        self.assertLess(len(by(r2, 'bass')), len(by(res, 'bass')))

    def test_mute_solo(self):
        p, _, res, _ = build(NEON)
        q = copy.deepcopy(p)
        q['tracks'][5]['mute'] = True
        self.assertNotIn(9, {n[2] for t in read_midi(engine.generate(q).midi)['tracks'][1:] for n in t['notes']})
        q = copy.deepcopy(p)
        q['tracks'][0]['solo'] = True
        self.assertEqual(len(engine.generate(q).bufs), 1)

    def test_time_signatures_and_keys(self):
        for ts in ([3, 4], [6, 8], [5, 4], [12, 8]):
            o = copy.deepcopy(NEON)
            o['global']['time_signature'] = ts
            p, rep, res, v = build(o)
            self.assertEqual(v['bars'], 88)
            self.assertEqual(read_midi(res.midi)['tracks'][0]['timesig'], tuple(ts))
        o = copy.deepcopy(NEON)
        o['global']['key_signature'] = 'F# dorian'
        self.assertEqual(read_midi(build(o)[2].midi)['tracks'][0]['keysig'], (4, 0))

    def test_sus_override(self):
        p, _, res, _ = build(NEON)
        q = copy.deepcopy(p)
        q['sections'][3]['chord_overrides'] = [{'when': {'bar_mod': [4, 3]}, 'split': [[0, 2, 'Csus4'], [2, 4, 'C']]}]
        ctx = engine.Ctx(q)
        syms = [s.sym for s in ctx.secs[3].spans]
        self.assertIn('Csus4', syms)

    def test_events_roundtrip(self):
        p, _, res, _ = build(NEON)
        ev = engine.export_events(res)
        p2, rep = adapter.normalize(json.loads(json.dumps(ev)))
        self.assertTrue(p2['raw'])
        m1, m2 = read_midi(res.midi), read_midi(engine.generate(p2).midi)
        for a, b in zip(m1['tracks'], m2['tracks']):
            self.assertEqual(len(a['notes']), len(b['notes']))
            ga, gb = {}, {}
            for g, tr in ((ga, a), (gb, b)):
                for n in tr['notes']:
                    g.setdefault(n[3], []).append((n[0], n[4]))
            self.assertEqual(set(ga), set(gb))
            for pitch in ga:
                xs, ys = sorted(ga[pitch]), sorted(gb[pitch])
                for x, y in zip(xs, ys):
                    self.assertLessEqual(abs(x[0] - y[0]), 1)
                self.assertEqual(sorted(v for _, v in xs), sorted(v for _, v in ys))

    def test_robustness(self):
        o = copy.deepcopy(NEON)
        o['harmony']['progressions']['verse'] = ['Dm7b5', 'G7#9', 'Cmaj13', 'F/A', 'Bbsus2', 'Zz9']
        o['melody']['lead_phrases_by_section']['Coro'] = [{'beat': 999, 'pitch': 60, 'dur': 1}, {'beat': 1, 'pitch': 'ZZ', 'dur': 1}]
        o['arrangement']['sections'][1]['bars'] = 0
        p, rep, res, v = build(o)
        self.assertTrue(any('no reconocido' in w for w in v['warnings']))
        self.assertTrue(any(r['level'] == 'warn' for r in rep))
        q = copy.deepcopy(p)
        q['sections'][3]['blocks']['drums']['params'] = {'preset': 'no_existe'}
        q['sections'][3]['blocks']['arp']['params'] = {'pattern': 'zzz', 'step': 0.3}
        q['sections'][3]['blocks']['pad']['params'] = {'voicing': {'profile': 'open4', 'range': [40, 50]}}
        q['sections'][3]['chords'] = []
        q['global']['bpm'] = 999
        self.assertTrue(engine.generate(q).midi)

    def test_presets_cover_all_roles_and_kinds(self):
        for preset in styles.PRESETS:
            for kind in styles.KINDS:
                for role in styles.ROLES:
                    b = styles.default_block(preset, {'kind': kind, 'bars': 8}, role)
                    self.assertIn(b['style'], styles.STYLE_SCHEMA[role])


class Mp3Tests(unittest.TestCase):
    def test_status_has_mp3_flags(self):
        st = audio.status()
        self.assertIn('mp3', st)

    @unittest.skipUnless(audio.status()['mp3'], 'requiere FluidSynth + soundfont + ffmpeg/lame')
    def test_server_mp3(self):
        p, _, res, _ = build(NEON)
        data, applied = audio.render_mp3(res.midi, gain=0.3, bitrate=128)
        self.assertEqual(applied, [])
        self.assertTrue(data[:3] == b'ID3' or data[0] == 0xFF)
        self.assertGreater(len(data), 100000)

    def test_web_assets_present(self):
        html = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('id="btnMp3"', html)
        self.assertIn('lame.min.js', html)
        self.assertTrue((ROOT / 'web' / 'lame.min.js').stat().st_size > 100000)


class HybridSpecTests(unittest.TestCase):
    """Capacidades añadidas para Shadow_Corner_TRIPHOP_DREAMPOP_DARKJAZZ_HYBRID.json"""

    @classmethod
    def setUpClass(cls):
        cls.p, cls.rep, cls.res, cls.v = build(HYBRID)

    def test_roles_and_channels(self):
        self.assertEqual([t['role'] for t in self.p['tracks']], ['pad', 'bass', 'lead', 'keys', 'mallet', 'drums'])
        self.assertEqual([t['channel'] for t in self.p['tracks']], [1, 2, 3, 4, 5, 10])
        self.assertEqual([t['program'] for t in self.p['tracks'][:5]], [91, 38, 66, 4, 11])
        self.assertEqual(self.p['tracks'][0]['detune'], 0)          # no inventa desafinacion

    def test_english_rhythm_and_beat_base(self):
        self.assertTrue(all(s['chord_bars'] == 2.0 for s in self.p['sections']))
        first = self.p['lead']['phrases']['verse_1'][0]
        self.assertEqual((first['bar'], first['beat']), (1, 0.0))   # beat 5.0 (base 1) = inicio del compas 2

    def test_modifiers(self):
        b = lambda sec, tid: next(s for s in self.p['sections'] if s['id'] == sec)['blocks'][tid]
        self.assertEqual(b('chorus', 'pad')['params']['voicing']['profile'], 'wide')
        self.assertEqual(b('outro', 'keys')['style'], 'tail')
        self.assertEqual(b('outro', 'mallet')['style'], 'pings')
        self.assertLess(b('final_chorus', 'mallet')['params']['prob'], b('verse_1', 'mallet')['params']['prob'])
        self.assertFalse(b('intro', 'drums')['enabled'])
        self.assertEqual(b('bridge', 'bass')['params']['patterns'][1], [])   # una nota larga cada 2 compases

    def test_bends_probability_and_caps(self):
        sc = self.p['sections'][1]['blocks']['lead']['params']['bends']['scoop']
        self.assertAlmostEqual(sc['semitones'], 0.2)
        self.assertEqual(sc['prob'], 0.5)
        self.assertEqual(self.p['global']['velocity_cap'], 90)
        self.assertLessEqual(max(n.v for b in self.res.bufs for n in b.notes), 90)

    def test_render_fx_parsed(self):
        fx = self.p['render']
        self.assertEqual((fx['lowpass_hz'], fx['loudness_lufs'], fx['fade_out_seconds']), (8500, -18.0, 20.0))
        self.assertIn('hiss', fx['noise'])
        self.assertIn('crackle', fx['noise'])
        self.assertTrue(any('LUFS' in u for u in self.p['meta']['unsupported']))

    def test_compliance_all_requested_pass(self):
        comp = {c['id']: c for c in self.v['compliance']}
        for cid in ('tempo_ts_bars', 'tracks_programs', 'dedicated_channels', 'lead_mono_range', 'mallet_sparse',
                    'lead_mallet_overlap', 'bass_kick', 'four_on_floor', 'section_bounds', 'motif_repeat'):
            self.assertEqual(comp[cid]['status'], 'pass', comp[cid])
        self.assertEqual(self.v['semitone_clashes_unintended'], 0)
        self.assertEqual(self.v['bars'], 88)

    def test_mallet_answers_in_gaps(self):
        lead = next(b for b in self.res.bufs if b.role == 'lead')
        mal = next(b for b in self.res.bufs if b.role == 'mallet')
        self.assertTrue(10 <= len(mal.notes) <= 60)
        for n in mal.notes:
            for m in lead.notes:
                if min(n.t + n.d, m.t + m.d) - max(n.t, m.t) > 0.25:
                    self.assertGreaterEqual(abs(n.p - m.p), 5)

    def test_keys_stay_in_range(self):
        keys = next(b for b in self.res.bufs if b.role == 'keys')
        lo, hi = keys.track['range']
        self.assertTrue(all(lo - 1 <= n.p <= hi + 1 for n in keys.notes))

    def test_hat_humanization(self):
        hz = self.p['tracks'][5]['drum_humanize']
        self.assertEqual(hz['hat']['grid'], 0.25)
        self.assertEqual(hz['hat']['omit'], [0.25, 0.35])
        self.assertAlmostEqual(hz['hat']['jitter'], 10 / 480.0)

    def test_deterministic(self):
        self.assertEqual(self.res.midi, build(HYBRID)[2].midi)


class RenderFxTests(unittest.TestCase):
    @unittest.skipUnless(audio.status()['mp3'], 'requiere FluidSynth + soundfont + ffmpeg')
    def test_master_chain(self):
        o = copy.deepcopy(HYBRID)
        o['arrangement']['sections'] = o['arrangement']['sections'][:1]
        o['mp3_render']['extras'] = ['hiss', 'vinyl crackle', 'low-pass 8500 Hz', '-18 LUFS', '4-6 second exponential fade']
        p, rep = adapter.normalize(o)
        res = engine.generate(p)
        data, applied = audio.render_mp3(res.midi, gain=0.4, fx=p['render'],
                                         sections=[(s.kind, s.t0 * 60.0 / res.ctx.bpm, s.t1 * 60.0 / res.ctx.bpm) for s in res.ctx.secs])
        self.assertGreater(len(data), 50000)
        self.assertTrue(any('loudnorm' in a for a in applied) and 'hiss' in applied and 'crackle' in applied)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        from http.server import ThreadingHTTPServer
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def call(self, path, body=None):
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), data=None if body is None else json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode('utf-8'))

    def test_endpoints(self):
        meta = self.call('/api/meta')
        self.assertIn('style_schema', meta)
        self.assertIn('mp3', meta)
        g = self.call('/api/generate', {'project': NEON})
        self.assertEqual(g['summary']['bars'], 88)
        self.assertTrue(g['midi_b64'])
        self.assertEqual(self.call('/api/suggest_lead', {'project': g['project'], 'section_id': 'coro', 'seed': 1})['notes'][0]['bar'] >= 0, True)
        self.assertEqual(self.call('/api/events', {'project': g['project']})['tracks'][0]['role'], 'pad')

    def test_errors_are_json(self):
        req = urllib.request.Request('http://127.0.0.1:%d/api/normalize' % self.port, data=b'{"json": "{x"}', headers={'Content-Type': 'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 400)
        self.assertIn('error', json.loads(cm.exception.read().decode('utf-8')))


if __name__ == '__main__':
    unittest.main()
