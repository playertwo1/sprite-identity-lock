#!/usr/bin/env python3
"""Audita consistência pixel-a-pixel contra sprite mestre; não modifica fontes."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgba_pixels(im):
    data = im.tobytes()
    return (data[i:i + 4] for i in range(0, len(data), 4))


def visible_colors(im):
    return {tuple(px[:3]) for px in rgba_pixels(im) if px[3] > 0}


def normalized_px(px):
    return px if px[3] else (0, 0, 0, 0)


def pixel_diffs(a, b, region=None):
    if region is None:
        region = (0, 0, a.width, a.height)
    x, y, w, h = region
    if w < 1 or h < 1 or x < 0 or y < 0 or x + w > a.width or y + h > a.height:
        raise ValueError(f"Região fora do canvas: {list(region)}")
    pa, pb = a.load(), b.load()
    return sum(normalized_px(pa[i, j]) != normalized_px(pb[i, j])
               for j in range(y, y + h) for i in range(x, x + w))


def alpha_bbox(im):
    return im.getchannel('A').getbbox()


def anchor(im):
    bb = alpha_bbox(im)
    return ((bb[0] + bb[2]) / 2.0, bb[3]) if bb else None


def parse_palette(colors):
    out = set()
    for h in colors:
        if not isinstance(h, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', h):
            raise ValueError(f"Cor inválida: {h!r}; use #RRGGBB")
        out.add(tuple(bytes.fromhex(h[1:])))
    return out


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError('Manifesto deve ser um objeto JSON')
    allowed_fields = {'character_id', 'master_sprite', 'master_sha256', 'canvas', 'identity_notes',
                      'allowed_changes', 'palette', 'palette_policy', 'lock_first_frame',
                      'fixed_regions', 'region_exceptions', 'tolerances'}
    if set(config) - allowed_fields:
        raise ValueError(f'Campos desconhecidos no manifesto: {sorted(set(config) - allowed_fields)}')
    if not isinstance(config.get('master_sprite'), str) or not config['master_sprite'].strip():
        raise ValueError('master_sprite deve ser um caminho não vazio')
    canvas = config.get('canvas')
    if not isinstance(canvas, dict) or any(type(canvas.get(k)) is not int or canvas[k] < 1 for k in ('width', 'height')):
        raise ValueError('canvas deve conter width e height inteiros positivos')
    if type(config.get('lock_first_frame', False)) is not bool:
        raise ValueError('lock_first_frame deve ser true ou false JSON')
    digest = config.get('master_sha256', '')
    if not isinstance(digest, str) or (digest and not re.fullmatch(r'[0-9a-fA-F]{64}', digest)):
        raise ValueError('master_sha256 deve ser vazio ou ter 64 dígitos hexadecimais')
    if not isinstance(config.get('palette', []), list):
        raise ValueError('palette deve ser uma lista de cores #RRGGBB')
    parse_palette(config.get('palette', []))
    if config.get('palette_policy', 'strict') not in ('strict', 'review'):
        raise ValueError('palette_policy deve ser strict ou review')
    regions = config.get('fixed_regions', [])
    if not isinstance(regions, list):
        raise ValueError('fixed_regions deve ser uma lista')
    for region in regions:
        if not isinstance(region, dict) or not isinstance(region.get('name'), str) or not region['name'].strip():
            raise ValueError('Cada região deve ter um nome não vazio')
        rect = region.get('rect')
        if not isinstance(rect, list) or len(rect) != 4 or any(type(v) is not int for v in rect):
            raise ValueError('rect deve conter quatro inteiros [x,y,w,h]')
    if not isinstance(config.get('region_exceptions', {}), dict):
        raise ValueError('region_exceptions deve ser um objeto JSON')
    tolerances = config.get('tolerances', {})
    allowed = {'max_anchor_dx_px', 'max_anchor_dy_px', 'max_bbox_width_delta_pct',
               'max_bbox_height_delta_pct', 'max_changed_pixel_ratio_warning',
               'max_semitransparent_ratio_warning'}
    if not isinstance(tolerances, dict) or set(tolerances) - allowed:
        raise ValueError('tolerances deve ser um objeto com nomes de campos conhecidos')
    for key, value in tolerances.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'Tolerância inválida: {key}')
        if key.endswith('_ratio_warning') and value > 1:
            raise ValueError(f'{key} deve ficar entre 0 e 1')


def build_background(w, h, block=8):
    im = Image.new('RGB', (w, h), (232, 232, 232))
    d = ImageDraw.Draw(im)
    for y in range(0, h, block):
        for x in range(0, w, block):
            if (x // block + y // block) % 2:
                d.rectangle((x, y, min(w - 1, x + block - 1),
                             min(h - 1, y + block - 1)), fill=(196, 196, 196))
    return im


def composite_preview(im, scale):
    scaled = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    bg = build_background(*scaled.size, block=max(8, 8 * scale))
    bg.paste(scaled, (0, 0), scaled)
    return bg


def create_previews(frames, out_dir, fps):
    frame_w, frame_h = frames[0][1].size
    scale = min(6, max(1, 384 // max(frame_w, frame_h)))
    gif_frames = [composite_preview(im, scale) for _, im in frames]
    gif_frames[0].save(out_dir / 'preview.gif', save_all=True,
                       append_images=gif_frames[1:], duration=round(1000 / fps),
                       loop=0, disposal=2, optimize=False)
    cols = min(4, len(frames))
    rows = math.ceil(len(frames) / cols)
    fw, fh = gif_frames[0].size
    gap, label_h = 12, 24
    sheet = Image.new('RGB', (cols * (fw + gap) + gap,
                              rows * (fh + gap + label_h) + gap), (35, 39, 45))
    draw = ImageDraw.Draw(sheet)
    for ix, ((name, _), tile) in enumerate(zip(frames, gif_frames)):
        x, y = gap + (ix % cols) * (fw + gap), gap + (ix // cols) * (fh + gap + label_h)
        sheet.paste(tile, (x, y))
        draw.text((x, y + fh + 5), name, fill=(255, 255, 255))
    sheet.save(out_dir / 'contact_sheet.png')


def inspect(manifest_path, frames_dir, out_dir, fps):
    if type(fps) is not int or not 1 <= fps <= 60:
        raise ValueError('fps deve ficar entre 1 e 60')
    config = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    validate_config(config)
    outputs = [out_dir / name for name in ('report.json', 'contact_sheet.png', 'preview.gif')]
    protected = [manifest_path.resolve(), (manifest_path.parent / config['master_sprite']).resolve()]
    if any(p.exists() or p.resolve() in protected for p in outputs):
        raise ValueError('Saída já existe ou conflita com fonte; use uma pasta nova')
    master_path = (manifest_path.parent / config['master_sprite']).resolve()
    if not master_path.is_file():
        raise ValueError(f"Master sprite não encontrado: {master_path}")
    frame_files = sorted(p for p in frames_dir.iterdir()
                         if p.is_file() and p.suffix.lower() == '.png')
    if not frame_files:
        raise ValueError(f"Nenhum PNG encontrado em {frames_dir}")
    if out_dir.resolve() == frames_dir.resolve() or frames_dir.resolve() in out_dir.resolve().parents:
        raise ValueError('--out-dir não pode ser --frames-dir nem subpasta dela')

    with Image.open(master_path) as temp:
        if temp.format != 'PNG' or getattr(temp, 'n_frames', 1) != 1:
            raise ValueError('Sprite mestre deve ser um PNG estático')
        master = temp.convert('RGBA')
    cw, ch = config['canvas']['width'], config['canvas']['height']
    if cw < 1 or ch < 1 or master.size != (cw, ch):
        raise ValueError(f"Canvas {cw}x{ch} incompatível com master {master.size}")

    palette = parse_palette(config.get('palette', [])) or visible_colors(master)
    policy = config.get('palette_policy', 'strict')
    if policy not in ('strict', 'review'):
        raise ValueError('palette_policy deve ser strict ou review')
    tolerances = config.get('tolerances', {})
    regions = config.get('fixed_regions', [])
    exception_map = config.get('region_exceptions', {})
    names = [r['name'] for r in regions]
    if len(names) != len(set(names)):
        raise ValueError('Nomes de regiões devem ser únicos')
    for region in regions:
        pixel_diffs(master, master, region['rect'])
        permitted = region.get('max_changed_pixels', 0)
        if type(permitted) is not int or permitted < 0:
            raise ValueError('max_changed_pixels deve ser inteiro não negativo')
    filenames = {f.name for f in frame_files}
    for filename, exceptions in exception_map.items():
        if filename not in filenames or not isinstance(exceptions, list) or any(n not in names for n in exceptions):
            raise ValueError('region_exceptions contém frame ou região desconhecida')
    master_anchor, master_bbox = anchor(master), alpha_bbox(master)
    if master_bbox is None:
        raise ValueError('Sprite mestre completamente transparente')
    master_digest = sha256(master_path)
    root_errors = []
    if config.get('master_sha256') and config['master_sha256'].lower() != master_digest.lower():
        root_errors.append('SHA256 do master difere do valor aprovado')
    report = {
        'skill': 'sprite-identity-lock',
        'character_id': config.get('character_id', ''),
        'master_sprite': str(master_path),
        'master_sha256': master_digest,
        'palette_size': len(palette),
        'reference_canvas': [cw, ch],
        'root_errors': root_errors,
        'frames': [],
        'status': 'PASS',
        'human_identity_review_required': True,
    }
    previews = []
    seen_images = {}

    for index, f in enumerate(frame_files):
        errors, warnings = [], []
        item = {'file': f.name, 'sha256': sha256(f), 'errors': errors, 'warnings': warnings}
        report['frames'].append(item)
        try:
            with Image.open(f) as raw:
                if raw.format != 'PNG' or getattr(raw, 'n_frames', 1) != 1:
                    raise ValueError('Cada quadro deve ser um PNG estático, não APNG ou outro formato')
                mode, info = raw.mode, dict(raw.info)
                im = raw.convert('RGBA')
        except (OSError, ValueError) as exc:
            errors.append(f'PNG inválido: {exc}')
            continue
        item.update(original_mode=mode, size=list(im.size))
        if im.size != (cw, ch):
            errors.append(f'Dimensão {im.size}, esperado {(cw, ch)}')
            continue
        if mode not in ('RGBA', 'LA') and not (mode == 'P' and 'transparency' in info):
            warnings.append('PNG de origem não contém canal alpha; verificar transparência')
        if alpha_bbox(im) is None:
            errors.append('Quadro completamente transparente')
            continue
        if min(px[3] for px in rgba_pixels(im)) > 0:
            warnings.append('Nenhum pixel transparente; verificar fundo')
        semi = sum(0 < px[3] < 255 for px in rgba_pixels(im))
        semi_ratio = semi / (cw * ch)
        item['semitransparent_ratio'] = round(semi_ratio, 5)
        if semi_ratio > float(tolerances.get('max_semitransparent_ratio_warning', 0.0)):
            warnings.append(f'{semi} pixels semitransparentes; inspecionar antialiasing')

        extra = visible_colors(im) - palette
        item['out_of_palette_colors'] = [f'#{r:02X}{g:02X}{b:02X}' for r, g, b in sorted(extra)]
        if extra:
            message = f'{len(extra)} cores ausentes da paleta aprovada'
            (errors if policy == 'strict' else warnings).append(message)
        if index == 0 and config.get('lock_first_frame', False) and pixel_diffs(im, master) > 0:
            errors.append('Quadro inicial obrigatório difere do sprite mestre')

        diffs = pixel_diffs(im, master)
        visible_union = sum(a[3] > 0 or b[3] > 0 for a, b in zip(rgba_pixels(im), rgba_pixels(master)))
        change_ratio = diffs / visible_union
        item['changed_pixel_ratio'] = round(change_ratio, 5)
        if change_ratio > float(tolerances.get('max_changed_pixel_ratio_warning', 0.80)):
            warnings.append('Mudanças excessivas em relação ao sprite mestre; revisar visualmente')

        bbox = alpha_bbox(im)
        if master_bbox and bbox:
            seedw, seedh = master_bbox[2] - master_bbox[0], master_bbox[3] - master_bbox[1]
            fw, fh = bbox[2] - bbox[0], bbox[3] - bbox[1]
            item['bbox'] = list(bbox)
            wdelta, hdelta = abs(fw - seedw) / max(1, seedw), abs(fh - seedh) / max(1, seedh)
            if wdelta > float(tolerances.get('max_bbox_width_delta_pct', 0.30)):
                warnings.append(f'Largura ocupada mudou {wdelta:.0%} em relação ao master')
            if hdelta > float(tolerances.get('max_bbox_height_delta_pct', 0.30)):
                warnings.append(f'Altura ocupada mudou {hdelta:.0%} em relação ao master')
            fx, fy = anchor(im)
            dx, dy = abs(fx - master_anchor[0]), abs(fy - master_anchor[1])
            item['anchor_delta_px'] = [round(dx, 2), round(dy, 2)]
            if dx > float(tolerances.get('max_anchor_dx_px', 3)):
                warnings.append(f'Âncora horizontal deslocou {dx:.1f}px')
            if dy > float(tolerances.get('max_anchor_dy_px', 3)):
                warnings.append(f'Âncora vertical deslocou {dy:.1f}px')

        skipped_regions = set(exception_map.get(f.name, []))
        for region in regions:
            name = region['name']
            if name in skipped_regions:
                continue
            rect = region['rect']
            changed = pixel_diffs(im, master, rect)
            permitted = int(region.get('max_changed_pixels', 0))
            if changed > permitted:
                errors.append(f'Região fixa "{name}" alterada em {changed} pixels (máx {permitted})')

        checksum = hashlib.sha256(b''.join(bytes(normalized_px(px)) for px in rgba_pixels(im))).hexdigest()
        if checksum in seen_images:
            warnings.append(f'Frame visualmente idêntico a {seen_images[checksum]} (pode ser pausa intencional)')
        else:
            seen_images[checksum] = f.name
        previews.append((f.name, im))

    if any(row['errors'] for row in report['frames']) or report['root_errors']:
        report['status'] = 'FAIL'
    elif any(row['warnings'] for row in report['frames']):
        report['status'] = 'REVIEW'
    report['preview_frames'] = [name for name, _ in previews]
    report['fps'] = fps
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if previews:
        create_previews(previews, out_dir, fps)
    return report


def main():
    parser = argparse.ArgumentParser(description='Auditar identidade visual e exportar previews sem alterar PNGs')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--frames-dir', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--fps', type=int, default=6)
    args = parser.parse_args()
    if not (1 <= args.fps <= 60):
        parser.error('--fps deve ficar entre 1 e 60')
    try:
        report = inspect(args.manifest, args.frames_dir, args.out_dir, args.fps)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(f"STATUS: {report['status']} — {len(report['frames'])} frames")
    print(f"Relatório e previews: {args.out_dir}")
    print('Aprovação visual da identidade continua obrigatória.')
    return 2 if report['status'] == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
