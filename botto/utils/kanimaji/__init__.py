"""Kanimaji by maurimo

Licensed under MIT/BSD.
Modified by Music#9755 (MusicOnline).

GitHub source: https://github.com/maurimo/kanimaji

This modified version of Kanimaji only retains the GIF creation magic.
It supports both Unix and Windows, well sort of.
Windows was not supported in the original script by maurimo, and the modifications here
have allowed Windows machines to be able to generate some of the GIF files.
Due to a constraint on Windows, you will get 'spawn ENAMETOOLONG' errors, especially
with kanji with complicated stroke diagrams.
"""

import json
import os
import re
import sys
from subprocess import Popen, PIPE
from textwrap import dedent as d

from lxml import etree  # type: ignore
from lxml.builder import E  # type: ignore
from svg.path import parse_path  # type: ignore

from . import bezier_cubic
from .settings import *  # pylint: disable=wildcard-import,unused-wildcard-import

__all__ = ["create_gif"]

# pylint: disable=invalid-name,undefined-variable,no-member

if os.name == "nt":
    QUOTE = '"'
else:
    QUOTE = "'"


def compute_path_len(path):
    return parse_path(path).length(error=1e-8)


def shescape(path):
    return QUOTE + re.sub(r"(?=['\\\\])", "\\\\", path) + QUOTE


# ease, ease-in, etc:
# https://developer.mozilla.org/en-US/docs/Web/CSS/timing-function#ease
pt1 = bezier_cubic.pt(0, 0)
ease_ct1 = bezier_cubic.pt(0.25, 0.1)
ease_ct2 = bezier_cubic.pt(0.25, 1.0)
ease_in_ct1 = bezier_cubic.pt(0.42, 0.0)
ease_in_ct2 = bezier_cubic.pt(1.0, 1.0)
ease_in_out_ct1 = bezier_cubic.pt(0.42, 0.0)
ease_in_out_ct2 = bezier_cubic.pt(0.58, 1.0)
ease_out_ct1 = bezier_cubic.pt(0.0, 0.0)
ease_out_ct2 = bezier_cubic.pt(0.58, 1.0)
pt2 = bezier_cubic.pt(1, 1)


def linear(x):
    return x


def ease(x):
    return bezier_cubic.value(pt1, ease_ct1, ease_ct2, pt2, x)


def ease_in(x):
    return bezier_cubic.value(pt1, ease_in_ct1, ease_in_ct2, pt2, x)


def ease_in_out(x):
    return bezier_cubic.value(pt1, ease_in_out_ct1, ease_in_out_ct2, pt2, x)


def ease_out(x):
    return bezier_cubic.value(pt1, ease_out_ct1, ease_out_ct2, pt2, x)


def _run_terminal(command, cwd=None):
    # with Popen(command, stdout=PIPE, stderr=PIPE, shell=True, cwd=cwd) as proc:
    with Popen(command, shell=True, cwd=cwd) as proc:
        proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError("Error running external command.")


timing_funcs = {
    "linear": linear,
    "ease": ease,
    "ease-in": ease_in,
    "ease-in-out": ease_in_out,
    "ease-out": ease_out,
}


def create_gif(filename, output=None):
    if TIMING_FUNCTION not in timing_funcs:
        raise RuntimeError(f'Invalid timing function "{TIMING_FUNCTION}".')
    my_timing_func = timing_funcs[TIMING_FUNCTION]

    # We will need this to deal with SVG.
    namespaces = {"n": "http://www.w3.org/2000/svg"}
    etree.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    parser = etree.XMLParser(remove_blank_text=True)

    basename = os.path.basename(filename)
    basename_noext = ".".join(basename.split(".")[:-1])
    dirname = os.path.dirname(filename) or os.getcwd()
    baseid = basename_noext

    # Load XML
    doc = etree.parse(filename, parser)

    # For xlink namespace introduction
    doc.getroot().set("{http://www.w3.org/1999/xlink}used", "")

    # Clear all extra elements this program may have previously added
    for el in doc.xpath("/n:svg/n:style", namespaces=namespaces):
        if re.match(r"-Kanimaji$", el.get("id")):
            doc.getroot().remove(el)
    for g in doc.xpath("/n:svg/n:g", namespaces=namespaces):
        if re.match(r"-Kanimaji$", g.get("id")):
            doc.getroot().remove(g)

    # create groups with a copies (references actually) of the paths
    bg_g = E.g(
        id=f"kvg:{baseid}-bg-Kanimaji",
        style=(
            f"fill:none;stroke:{STOKE_UNFILLED_COLOR};"
            f"stroke-width:{STOKE_UNFILLED_WIDTH};"
            f"stroke-linecap:round;stroke-linejoin:round;"
        ),
    )
    anim_g = E.g(
        id=f"kvg:{baseid}-anim-Kanimaji",
        style=(
            f"fill:none;stroke:{STOKE_FILLED_COLOR};"
            f"stroke-width:{STOKE_FILLED_WIDTH};"
            f"stroke-linecap:round;stroke-linejoin:round;"
        ),
    )
    if SHOW_BRUSH:
        brush_g = E.g(
            id=f"kvg:{baseid}-brush-Kanimaji",
            style=(
                f"fill:none;stroke:{BRUSH_COLOR};stroke-width:{BRUSH_WIDTH};"
                f"stroke-linecap:round;stroke-linejoin:round;"
            ),
        )
        brush_brd_g = E.g(
            id=f"kvg:{baseid}-brush-brd-Kanimaji",
            style=(
                f"fill:none;stroke:{BRUSH_BORDER_COLOR};"
                f"stroke-width:{BRUSH_BORDER_WIDTH};"
                f"stroke-linecap:round;stroke-linejoin:round;"
            ),
        )

    # compute total length and time, at first
    totlen = 0
    tottime = 0

    for g in doc.xpath("/n:svg/n:g", namespaces=namespaces):
        if re.match(r"^kvg:StrokeNumbers_", g.get("id")):
            continue
        for p in g.xpath(".//n:path", namespaces=namespaces):
            pathlen = compute_path_len(p.get("d"))
            duration = stroke_length_to_duration(pathlen)
            totlen += pathlen
            tottime += duration

    animation_time = time_rescale(tottime)  # math.pow(3 * tottime, 2.0/3)
    tottime += WAIT_AFTER * tottime / animation_time
    actual_animation_time = animation_time
    animation_time += WAIT_AFTER

    css_header = d(
        """
        /* CSS automatically generated by kanimaji.py, do not edit! */
        """
    )
    static_css = {}
    last_frame_index = int(actual_animation_time / GIF_FRAME_DURATION) + 1
    for i in range(0, last_frame_index + 1):
        static_css[i] = css_header
    last_frame_delay = animation_time - last_frame_index * GIF_FRAME_DURATION
    elapsedlen = 0
    elapsedtime = 0

    # add css elements for all strokes
    for g in doc.xpath("/n:svg/n:g", namespaces=namespaces):
        groupid = g.get("id")
        if re.match(r"^kvg:StrokeNumbers_", groupid):
            rule = d(
                """
                #{} {{
                    display: none;
                }}
                """.format(
                    re.sub(r":", "\\\\3a ", groupid)
                )
            )
            for k in static_css:
                static_css[k] += rule
            continue

        gidcss = re.sub(r":", "\\\\3a ", groupid)
        rule = d(
            f"""
            #{gidcss} {{
                stroke-width: {STOKE_BORDER_WIDTH:.1f}px !important;
                stroke:       {STOKE_BORDER_COLOR} !important;
            }}
            """
        )
        for k in static_css:
            static_css[k] += rule

        for p in g.xpath(".//n:path", namespaces=namespaces):
            pathid = p.get("id")
            pathidcss = re.sub(r":", "\\\\3a ", pathid)

            bg_pathid = pathid + "-bg"
            bg_pathidcss = pathidcss + "-bg"
            ref = E.use(id=bg_pathid)
            ref.set("{http://www.w3.org/1999/xlink}href", "#" + pathid)
            bg_g.append(ref)

            anim_pathid = pathid + "-anim"
            anim_pathidcss = pathidcss + "-anim"
            ref = E.use(id=anim_pathid)
            ref.set("{http://www.w3.org/1999/xlink}href", "#" + pathid)
            anim_g.append(ref)

            if SHOW_BRUSH:
                brush_pathid = pathid + "-brush"
                brush_pathidcss = pathidcss + "-brush"
                ref = E.use(id=brush_pathid)
                ref.set("{http://www.w3.org/1999/xlink}href", "#" + pathid)
                brush_g.append(ref)

                brush_brd_pathid = pathid + "-brush-brd"
                brush_brd_pathidcss = pathidcss + "-brush-brd"
                ref = E.use(id=brush_brd_pathid)
                ref.set("{http://www.w3.org/1999/xlink}href", "#" + pathid)
                brush_brd_g.append(ref)

            pathlen = compute_path_len(p.get("d"))
            duration = stroke_length_to_duration(pathlen)
            newelapsedlen = elapsedlen + pathlen
            newelapsedtime = elapsedtime + duration

            for k in static_css:
                time = k * GIF_FRAME_DURATION
                reltime = time * tottime / animation_time  # unscaled time

                static_css[k] += d(
                    f"""
                    /* stroke {pathid} */
                    """
                )

                # animation
                if reltime < elapsedtime:  # just hide everything
                    rule = "#" + str(anim_pathidcss)
                    if SHOW_BRUSH:
                        rule += f", #{brush_pathidcss}, #{brush_brd_pathidcss}"
                    static_css[k] += d(
                        f"""
                        {rule} {{
                            visibility: hidden;
                        }}
                        """
                    )
                elif reltime > newelapsedtime:  # just hide the brush, and bg
                    rule = "#" + str(bg_pathidcss)
                    if SHOW_BRUSH:
                        rule += f", #{brush_pathidcss}, #{brush_brd_pathidcss}"
                    static_css[k] += d(
                        f"""
                        {rule} {{
                            visibility: hidden;
                        }}
                        """
                    )
                else:
                    intervalprop = (reltime - elapsedtime) / (
                        newelapsedtime - elapsedtime
                    )
                    progression = my_timing_func(intervalprop)
                    stroke_dashoffset = pathlen * (1 - progression) + 0.0015
                    static_css[k] += d(
                        f"""
                        #{anim_pathidcss} {{
                            stroke-dasharray: {pathlen:.3f} {pathlen + 0.002:.3f};
                            stroke-dashoffset: {stroke_dashoffset:.4f};
                            stroke: {STOKE_FILLING_COLOR};
                        }}
                        """
                    )
                    if SHOW_BRUSH:
                        static_css[k] += d(
                            f"""
                            #{brush_pathidcss}, #{brush_brd_pathidcss} {{
                                stroke-dasharray: 0.001 {pathlen + 0.002:.3f};
                                stroke-dashoffset: {stroke_dashoffset:.4f};
                            }}
                            """
                        )

            elapsedlen = newelapsedlen
            elapsedtime = newelapsedtime

    # insert groups
    if SHOW_BRUSH and not SHOW_BRUSH_FRONT_BORDER:
        doc.getroot().append(brush_brd_g)
    doc.getroot().append(bg_g)
    if SHOW_BRUSH and SHOW_BRUSH_FRONT_BORDER:
        doc.getroot().append(brush_brd_g)
    doc.getroot().append(anim_g)
    if SHOW_BRUSH:
        doc.getroot().append(brush_g)

    svgframefiles = []
    pngframefiles = []
    svgexport_data = []
    for k in static_css:
        svgframefile = os.path.join(dirname, f"{basename_noext}_frame{k:04}.svg")
        pngframefile = os.path.join(dirname, f"{basename_noext}_frame{k:04}.png")
        svgframefiles.append(svgframefile)
        pngframefiles.append(pngframefile)
        svgexport_data.append(
            {
                "input": [os.path.abspath(svgframefile)],
                "output": [[os.path.abspath(pngframefile), f"{GIF_SIZE}:{GIF_SIZE}"]],
            }
        )

        style = E.style(static_css[k], id="style-Kanimaji")
        doc.getroot().insert(0, style)
        doc.write(svgframefile, pretty_print=True)
        doc.getroot().remove(style)

    # create json file
    svgexport_datafile = os.path.join(dirname, basename_noext + "_export_data.json")
    with open(svgexport_datafile, "w") as f:
        f.write(json.dumps(svgexport_data))

    # run svgexport
    cmdline = f"svgexport {shescape(os.path.basename(svgexport_datafile))}"
    _run_terminal(cmdline, cwd=dirname)

    if DELETE_TEMPORARY_FILES:
        os.remove(svgexport_datafile)
        for f in svgframefiles:
            os.remove(f)

    # generate GIF
    giffile_tmp1 = basename_noext + "_anim_tmp1.gif"
    giffile_tmp2 = basename_noext + "_anim_tmp2.gif"
    giffile = basename_noext + "_anim.gif"
    escpngframefiles = " ".join(os.path.basename(f) for f in pngframefiles[0:-1])

    if GIF_BACKGROUND_COLOR == "transparent":
        bgopts = "-dispose previous"
    else:
        bgopts = f"-background {shescape(GIF_BACKGROUND_COLOR)} -alpha remove"
    cmdline = ("convert -delay {} {} -delay {} {} {} -layers OptimizePlus {}").format(
        int(GIF_FRAME_DURATION * 100),
        escpngframefiles,
        int(last_frame_delay * 100),
        os.path.basename(pngframefiles[-1]),
        bgopts,
        giffile_tmp1,
    )
    _run_terminal(cmdline, cwd=dirname)

    if DELETE_TEMPORARY_FILES:
        for f in pngframefiles:
            os.remove(f)

    # Do not escape parentheses on Windows.
    if os.name == "nt":
        escape = ""
    else:
        escape = "\\"

    cmdline = (
        f"convert {giffile_tmp1} {escape}( -clone 0--1 -background none "
        f"+append -quantize transparent -colors 63 "
        f"-unique-colors -write mpr:cmap +delete {escape}) "
        f"-map mpr:cmap {giffile_tmp2}"
    )
    _run_terminal(cmdline, cwd=dirname)
    if DELETE_TEMPORARY_FILES:
        os.remove(os.path.join(dirname, giffile_tmp1))

    cmdline = f"gifsicle -O3 {giffile_tmp2} -o {giffile}"
    _run_terminal(cmdline, cwd=dirname)
    if DELETE_TEMPORARY_FILES:
        os.remove(os.path.join(dirname, giffile_tmp2))

    if output is not None:
        os.rename(os.path.join(dirname, giffile), output)
