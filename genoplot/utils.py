# Copyright (c) 2016 by Welded Anvil Technologies (David D. Newell). All Rights Reserved.
# This software is the confidential and proprietary information of
# Welded Anvil Technologies (David D. Newell) ("Confidential Information").
# You shall not disclose such Confidential Information and shall use it
# only in accordance with the terms of the license agreement you entered
# into with Welded Anvil Technologies (David D. Newell).
# @author david@newell.at

import logging
logger = logging.getLogger("genoplot")


def calculate_text_size(text, font_size):
    """Returns width and height of specified text at specified font size
    :param text: Text for which size is to be calculated
    :type text: str
    :param font_size: Font size
    :type: font_size: int
    """
    if type(text) is str:
        text = [text]

    BASE_FONT_WIDTH = 0.52
    font_width = font_size*BASE_FONT_WIDTH

    width = []
    height = []

    for t in text:
        t_width = len(t)*font_width
        if t_width > 1.8:
            t_width += 0.2

        t_height = font_size*1.2

        width.append(t_width)
        height.append(t_height)

    return max(width, default=0), sum(height)


def stripName(name):
    if not type(name) is str:
        return name
    invalid = "'\"(),."
    return "".join(c for c in name.replace("\t", " ").replace(",", " ") if c not in invalid)

