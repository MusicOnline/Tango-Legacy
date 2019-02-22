from typing import BinaryIO, Dict, Generator, List, Tuple, Union

from lxml import etree  # type: ignore

from tango.core.models.jmdict import (
    Entry,
    WritingElement,
    ReadingElement,
    Sense,
    Gloss,
    LSource,
    ReadingWriting,
    ReadingSense,
    WritingSense,
)

XMLNS: str = "{http://www.w3.org/XML/1998/namespace}"


def _get_child(node: etree._Element, tag: str) -> etree._Element:
    return next(node.iter(tag))


def _has_child(node: etree._Element, tag: str) -> bool:
    try:
        _get_child(node, tag)
    except StopIteration:
        return False
    return True


def _parse_node(entry_node: etree._Element) -> Tuple[Entry, dict]:
    entry_id: int = int(_get_child(entry_node, "ent_seq").text)

    # ALl model instances
    entry: Entry = Entry(id=entry_id)
    writing_elements: List[WritingElement] = []
    reading_elements: List[ReadingElement] = []
    reading_writings_mapping: Dict[ReadingElement, List[WritingElement]] = {}
    readings_writings: List[ReadingWriting] = []
    senses: List[Sense] = []
    lsources: List[LSource] = []
    glosses: List[Gloss] = []
    writings_senses: List[WritingSense] = []
    readings_senses: List[ReadingSense] = []

    # Creating WritingElement instances from <entry><k_ele> tags.
    for k_ele in entry_node.iter("k_ele"):
        writing_elements.append(
            WritingElement(
                entry_id=entry_id,
                literal=_get_child(k_ele, "keb").text,
                priority=[ke_pri.text for ke_pri in k_ele.iter("ke_pri")],
                info=[ke_inf.text for ke_inf in k_ele.iter("ke_inf")],
            )
        )

    # Creating ReadingElement instances from <entry><r_ele> tags.
    # Also, registering relationships between ReadingElement instances and
    # WritingElement literals from <entry><r_ele><re_restr> tags or <re_nokanji/>.
    for r_ele in entry_node.iter("r_ele"):
        reading_elem = ReadingElement(
            entry_id=entry_id,
            literal=_get_child(r_ele, "reb").text,
            priority=[re_pri.text for re_pri in r_ele.iter("re_pri")],
            info=[re_inf.text for re_inf in r_ele.iter("re_inf")],
        )

        if _has_child(r_ele, "re_nokanji"):
            # This reading does not match any of the writing elemnts.
            reading_writings_mapping[reading_elem] = []
        elif _has_child(r_ele, "re_restr"):
            # This reading is restricted to some writing elements only.
            reading_writings_mapping[reading_elem] = [
                re_restr.text for re_restr in r_ele.iter("re_restr")
            ]
        else:
            # This reading matches all writing elements.
            reading_writings_mapping[reading_elem] = [
                w.literal for w in writing_elements
            ]

    reading_elements.extend(reading_writings_mapping)

    # Creating ReadingWriting relational instances.
    for reading_elem, writing_literals in reading_writings_mapping.items():
        reading_writing = [
            ReadingWriting(
                entry_id=entry_id,
                reading_literal=reading_elem.literal,
                writing_literal=w,
            )
            for w in writing_literals
        ]
        readings_writings.extend(reading_writing)

    last_parts_of_speech = None
    last_misc = None

    # Creating Sense-related instances from <entry><sense> tags.
    for sense_index, sense_node in enumerate(entry_node.iter("sense"), 1):
        new_parts_of_speech = [pos.text for pos in sense_node.iter("pos")]
        new_misc = [m.text for m in sense_node.iter("misc")]

        # If there are multiple senses, subsequent senses inherit <pos> and <misc> from
        # the previous sense UNLESS the sense has defined its own <pos> or <misc> tags.

        if last_parts_of_speech is None or new_parts_of_speech:
            parts_of_speech = new_parts_of_speech
        else:
            parts_of_speech = last_parts_of_speech

        if last_misc is None or new_misc:
            misc = new_misc
        else:
            misc = last_misc

        senses.append(
            Sense(
                entry_id=entry_id,
                index=sense_index,
                references=[xref.text for xref in sense_node.iter("xref")],
                antonyms=[ant.text for ant in sense_node.iter("ant")],
                parts_of_speech=parts_of_speech,
                fields=[field.text for field in sense_node.iter("field")],
                misc=misc,
                dialects=[dial.text for dial in sense_node.iter("dial")],
                info=[s_inf.text for s_inf in sense_node.iter("s_inf")],
            )
        )

        # Creating LSource instances from <sense><lsource>.
        for lsource_node in sense_node.iter("lsource"):
            lsources.append(
                LSource(
                    entry_id=entry_id,
                    sense_index=sense_index,
                    text=lsource_node.text,
                    lang=lsource_node.get(XMLNS + "lang", "eng"),
                    type=lsource_node.get("ls_type", "full"),
                    wasei=lsource_node.get("ls_wasei"),
                )
            )

        # Creating Gloss instances from <sense><gloss>.
        for gloss_node in sense_node.iter("gloss"):
            glosses.append(
                Gloss(
                    entry_id=entry_id,
                    sense_index=sense_index,
                    text=gloss_node.text,
                    lang=gloss_node.get(XMLNS + "lang", "eng"),
                    gender=gloss_node.get("g_gend"),
                    type=gloss_node.get("g_type"),
                )
            )

        if _has_child(sense_node, "stagk"):
            related_writings = [k.text for k in sense_node.iter("stagk")]
        else:
            related_writings = [w.literal for w in writing_elements]

        if _has_child(sense_node, "stagr"):
            related_readings = [r.text for r in sense_node.iter("stagr")]
        else:
            related_readings = [r.literal for r in reading_elements]

        for writing_literal in related_writings:
            writings_senses.append(
                WritingSense(
                    entry_id=entry_id,
                    writing_literal=writing_literal,
                    sense_index=sense_index,
                )
            )

        for reading_literal in related_readings:
            readings_senses.append(
                ReadingSense(
                    entry_id=entry_id,
                    reading_literal=reading_literal,
                    sense_index=sense_index,
                )
            )

    return (
        entry,
        {
            "writing_elements": writing_elements,
            "reading_elements": reading_elements,
            "readings_writings": readings_writings,
            "senses": senses,
            "lsources": lsources,
            "glosses": glosses,
            "writings_senses": writings_senses,
            "readings_senses": readings_senses,
        },
    )


def parse(filepath: Union[BinaryIO, str]) -> Generator[Tuple[Entry, dict], None, None]:
    tree = etree.parse(filepath)
    for node in tree.getroot().iter("entry"):
        yield _parse_node(node)
