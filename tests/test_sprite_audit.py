"""Testes de regressão rápidos; executar python -m unittest discover -s tests."""
import json
import tempfile
import unittest
from pathlib import Path
from sys import path
from PIL import Image, ImageDraw

path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sprite_audit import inspect
from split_sheet import split_sheet


class SpriteAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.frames = self.base / 'frames'
        self.frames.mkdir()
        self.master = self.base / 'master.png'
        im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.rectangle([4, 3, 11, 13], fill=(100, 70, 50, 255))
        dr.point((6, 6), fill=(255, 255, 255, 255))
        dr.point((9, 6), fill=(255, 255, 255, 255))
        dr.rectangle([1, 11, 3, 12], fill=(100, 70, 50, 255))
        im.save(self.master)
        self.config = {
            'character_id': 'test', 'master_sprite': 'master.png',
            'canvas': {'width': 16, 'height': 16},
            'palette': [], 'palette_policy': 'strict', 'lock_first_frame': True,
            'fixed_regions': [{'name': 'face', 'rect': [5, 4, 6, 5]}],
            'region_exceptions': {},
            'tolerances': {'max_anchor_dx_px': 3, 'max_anchor_dy_px': 3,
                           'max_bbox_width_delta_pct': 0.30,
                           'max_bbox_height_delta_pct': 0.30,
                           'max_changed_pixel_ratio_warning': 0.8,
                           'max_semitransparent_ratio_warning': 0.0},
        }
        self.manifest = self.base / 'lock.json'
        self.manifest.write_text(json.dumps(self.config))
        im.save(self.frames / 'frame_01.png')
        for n in range(2, 5):
            copy = im.copy()
            p = copy.load()
            p[1 + n % 3, 11] = (0, 0, 0, 0)
            p[1 + n % 3, 10] = (100, 70, 50, 255)
            copy.save(self.frames / f'frame_{n:02d}.png')

    def tearDown(self):
        self.tmp.cleanup()

    def test_pass_with_locked_face(self):
        result = inspect(self.manifest, self.frames, self.base / 'audit', fps=6)
        self.assertEqual('PASS', result['status'])
        self.assertTrue((self.base / 'audit' / 'preview.gif').exists())
        self.assertTrue((self.base / 'audit' / 'report.json').exists())
        self.assertTrue((self.base / 'audit' / 'contact_sheet.png').exists())

    def test_face_drift_fails(self):
        f = self.frames / 'frame_03.png'
        with Image.open(f) as img:
            copy = img.convert('RGBA')
        copy.putpixel((6, 6), (100, 70, 50, 255))
        copy.save(f)
        result = inspect(self.manifest, self.frames, self.base / 'audit', fps=6)
        self.assertEqual('FAIL', result['status'])
        self.assertTrue(any('face' in e for e in result['frames'][2]['errors']))

    def test_new_palette_color_fails(self):
        f = self.frames / 'frame_02.png'
        with Image.open(f) as img:
            copy = img.convert('RGBA')
        copy.putpixel((10, 12), (12, 34, 56, 255))
        copy.save(f)
        result = inspect(self.manifest, self.frames, self.base / 'audit', fps=6)
        self.assertEqual('FAIL', result['status'])
        self.assertIn('#0C2238', result['frames'][1]['out_of_palette_colors'])

    def test_wrong_dimensions_fails(self):
        Image.new('RGBA', (8, 8), (255, 0, 0, 255)).save(self.frames / 'frame_04.png')
        result = inspect(self.manifest, self.frames, self.base / 'audit', fps=6)
        self.assertEqual('FAIL', result['status'])
        self.assertTrue(any('Dimensão' in e for e in result['frames'][3]['errors']))

    def test_existing_output_is_preserved(self):
        out = self.base / 'audit'
        out.mkdir()
        report = out / 'report.json'
        report.write_text('preserve')
        with self.assertRaises(ValueError):
            inspect(self.manifest, self.frames, out, fps=6)
        self.assertEqual('preserve', report.read_text())

    def test_unknown_exception_rejected(self):
        self.config['region_exceptions'] = {'frame_02.png': ['typo']}
        self.manifest.write_text(json.dumps(self.config))
        with self.assertRaises(ValueError):
            inspect(self.manifest, self.frames, self.base / 'audit', fps=6)

    def test_change_ratio_ignores_empty_canvas(self):
        result = inspect(self.manifest, self.frames, self.base / 'audit', fps=6)
        self.assertGreater(result['frames'][1]['changed_pixel_ratio'], 2 / 256)

    def test_long_sheet_order(self):
        sheet = self.base / 'long.png'
        Image.new('RGBA', (101, 1), (1, 2, 3, 255)).save(sheet)
        out = self.base / 'long'
        split_sheet(sheet, 101, 1, out)
        names = sorted(p.name for p in out.iterdir())
        self.assertEqual('frame_001.png', names[0])
        self.assertEqual('frame_101.png', names[-1])

    def test_invalid_manifest_rejected_before_output(self):
        cases = [
            ('canvas', {'width': 16.9, 'height': 16}),
            ('canvas', {'width': True, 'height': 16}),
            ('lock_first_frame', 'false'),
            ('fixed_regons', []),
            ('tolerances', {'max_anchor_dxx_px': 100}),
            ('tolerances', {'max_changed_pixel_ratio_warning': 2}),
            ('fixed_regions', [{'name': 'face', 'rect': [5.5, 4, 6, 5]}]),
            ('fixed_regions', {}),
            ('palette', ['#FF  FF']),
            ('master_sha256', 'invalid'),
        ]
        for index, (key, value) in enumerate(cases):
            with self.subTest(key=key, value=value):
                config = dict(self.config, **{key: value})
                self.manifest.write_text(json.dumps(config))
                out = self.base / f'invalid_{index}'
                with self.assertRaises(ValueError):
                    inspect(self.manifest, self.frames, out, fps=6)
                self.assertFalse(out.exists())

    def test_corrupt_frame_produces_fail_report(self):
        (self.frames / 'frame_02.png').write_bytes(b'broken png')
        result = inspect(self.manifest, self.frames, self.base / 'audit', fps=6)
        self.assertEqual('FAIL', result['status'])
        self.assertTrue(result['frames'][1]['errors'])
        self.assertNotIn('frame_02.png', result['preview_frames'])
        self.assertEqual(4, len(result['frames']))

    def test_non_object_manifest_rejected(self):
        self.manifest.write_text('[]')
        with self.assertRaises(ValueError):
            inspect(self.manifest, self.frames, self.base / 'audit', fps=6)

    def test_disguised_jpeg_rejected(self):
        Image.new('RGB', (16, 16)).save(self.frames / 'frame_02.png', format='JPEG')
        result = inspect(self.manifest, self.frames, self.base / 'audit', fps=6)
        self.assertEqual('FAIL', result['status'])
        self.assertTrue(result['frames'][1]['errors'])

    def test_animated_png_rejected(self):
        first = Image.new('RGBA', (16, 16), (10, 20, 30, 255))
        second = Image.new('RGBA', (16, 16), (30, 20, 10, 255))
        animated = self.frames / 'frame_02.png'
        first.save(animated, save_all=True, append_images=[second], duration=100)
        result = inspect(self.manifest, self.frames, self.base / 'audit', fps=6)
        self.assertEqual('FAIL', result['status'])
        self.assertTrue(result['frames'][1]['errors'])
        with self.assertRaises(ValueError):
            split_sheet(animated, 1, 1, self.base / 'split')

    def test_hidden_rgb_does_not_hide_duplicate(self):
        with Image.open(self.master) as im:
            frame = im.convert('RGBA')
        frame.putpixel((0, 0), (23, 42, 99, 0))
        frame.save(self.frames / 'frame_02.png')
        result = inspect(self.manifest, self.frames, self.base / 'audit', fps=6)
        self.assertTrue(any('idêntico' in w for w in result['frames'][1]['warnings']))

    def test_split_rejects_contaminated_folder(self):
        out = self.base / 'split'
        out.mkdir()
        stale = out / 'frame_99.png'
        stale.write_bytes(b'preserve')
        with self.assertRaises(ValueError):
            split_sheet(self.master, 2, 1, out)
        self.assertEqual([stale], list(out.iterdir()))

    def test_split(self):
        sheet = Image.new('RGBA', (32, 16), (0, 0, 0, 0))
        sheet.paste((100, 70, 50, 255), (0, 0, 16, 16))
        sheet.paste((255, 255, 255, 255), (16, 0, 32, 16))
        path = self.base / 'sheet.png'
        sheet.save(path)
        count, size = split_sheet(path, 2, 1, self.base / 'split')
        self.assertEqual((2, (16, 16)), (count, size))
        self.assertEqual((100, 70, 50, 255), Image.open(self.base / 'split' / 'frame_01.png').getpixel((1, 1)))
        self.assertEqual((255, 255, 255, 255), Image.open(self.base / 'split' / 'frame_02.png').getpixel((1, 1)))


if __name__ == '__main__':
    unittest.main()
