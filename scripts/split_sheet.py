#!/usr/bin/env python3
"""Recorta sheet de células uniformes sem alterar escala ou interpolar pixels."""
import argparse
from pathlib import Path
from PIL import Image


def split_sheet(input_path, cols, rows, out_dir):
    if type(cols) is not int or type(rows) is not int or cols < 1 or rows < 1:
        raise ValueError('columns e rows precisam ser maiores que zero')
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError('Pasta de saída deve estar vazia para não misturar quadros de outros lotes')
    with Image.open(input_path) as original:
        if getattr(original, 'n_frames', 1) != 1:
            raise ValueError('Entrada animada não é uma spritesheet estática')
        if original.width % cols or original.height % rows:
            raise ValueError('Sheet não divisível exatamente pela grade. Corrija gutters/margens primeiro.')
        cell_w, cell_h = original.width // cols, original.height // rows
        if cell_w < 1 or cell_h < 1:
            raise ValueError('Dimensões de célula inválidas')
        digits = max(2, len(str(cols * rows)))
        expected = [out_dir / f'frame_{i + 1:0{digits}d}.png' for i in range(cols * rows)]
        existing = [p for p in expected if p.exists()]
        if existing:
            raise ValueError(f'Recorte cancelado: arquivos já existem ({existing[0]}). Use uma pasta de saída nova.')
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(cols * rows):
            x, y = (i % cols) * cell_w, (i // cols) * cell_h
            frame = original.crop((x, y, x + cell_w, y + cell_h)).convert('RGBA')
            frame.save(expected[i])
        return cols * rows, (cell_w, cell_h)


def main():
    parser = argparse.ArgumentParser(description='Separar grade retangular regular em PNGs')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--columns', type=int, required=True)
    parser.add_argument('--rows', type=int, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        count, size = split_sheet(args.input, args.columns, args.rows, args.out_dir)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f'{count} quadros {size[0]}x{size[1]} gerados em {args.out_dir}')


if __name__ == '__main__':
    main()
