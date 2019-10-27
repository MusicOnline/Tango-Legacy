"""kanjivg-gif by Yorwba

Licensed under GPL-3.0.
Modified by Music#9755 (MusicOnline).

GitHub source: https://github.com/Yorwba/kanjivg-gif
"""

import math
import subprocess

import lxml.etree  # type: ignore
import svg.path  # type: ignore
from PIL import Image, ImageDraw  # type: ignore

STROKE_WIDTH = 4
STROKE_SPEED = 20
FRAME_RATE = 20


def _complex_to_tuple(cmplx):
    return (cmplx.real, cmplx.imag)


def _create_frames(path_data, frame_size):
    path = svg.path.parse_path(path_data)
    length = path.length()
    duration = math.sqrt(length) / STROKE_SPEED
    num_frames = int(math.ceil(duration * FRAME_RATE))
    frames = []
    previous_point = _complex_to_tuple(path.point(0))

    for frame in range(1, num_frames + 1):
        next_point = _complex_to_tuple(path.point(frame / num_frames))
        image = Image.new("P", frame_size)
        image.putpalette([0] * (3 * 256))
        ImageDraw.Draw(image).line(
            previous_point + next_point, fill=1, width=STROKE_WIDTH
        )
        image.info["transparency"] = 0
        image.info["loop"] = 0
        image.info["duration"] = int(duration / num_frames * 1000)

        frames.append(image)
        previous_point = next_point

    return frames


def create_gif(svg_filepath, output_filepath=None):
    assert svg_filepath.endswith(".svg")
    assert output_filepath.endswith(".gif") if output_filepath is not None else True

    doc = lxml.etree.parse(svg_filepath)
    root = doc.getroot()
    frame_size = (int(root.get("width")), int(root.get("height")))
    frames = []
    for path in doc.iterfind(".//{http://www.w3.org/2000/svg}path"):
        frames.extend(_create_frames(path.get("d"), frame_size))

    if output_filepath is None:
        gif_filepath = svg_filepath[:-4] + ".gif"
    else:
        gif_filepath = output_filepath
    frames[0].save(gif_filepath, save_all=True, optimize=True, append_images=frames[1:])

    try:
        subprocess.Popen(["gifsicle", "--batch", "--optimize=3", gif_filepath])
    except OSError:
        pass  # optimization is optional


if __name__ == "__main__":
    import sys

    for svg in sys.argv[1:]:
        create_gif(svg)
