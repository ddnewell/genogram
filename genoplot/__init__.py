# Copyright (c) 2017 by Welded Anvil Technologies (David D. Newell). All Rights Reserved.
# This software is the confidential and proprietary information of
# Welded Anvil Technologies (David D. Newell) ("Confidential Information").
# You shall not disclose such Confidential Information and shall use it
# only in accordance with the terms of the license agreement you entered
# into with Welded Anvil Technologies (David D. Newell).
# @author david@newell.at

__version__ = "0.0.1"

__copyright__ = """
    Copyright (c) 2017 by Welded Anvil Technologies (David D. Newell). All Rights Reserved.
    This software is the confidential and proprietary information of
    Welded Anvil Technologies (David D. Newell) ("Confidential Information").
    You shall not disclose such Confidential Information and shall use it
    only in accordance with the terms of the license agreement you entered
    into with Welded Anvil Technologies (David D. Newell).
    @author david@newell.at
"""

__author__ = "David D. Newell <david@newell.at>"

import logging, time
import networkx as nx
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("genoplot")
import coloredlogs
coloredlogs.install(level="INFO")

from .genoplot import GenoPlot

def main():
    pstart = time.time()
    # p = GenoPlot("sample", "sample.ged")
    # p.create_graph()
    # g = p.create_grandalf()
    p.draw()

    logger.info("Total time to build GenoPlot: %.2fs", time.time() - pstart)
    logger.info("Total time to process: %.2fs", time.time() - pstart)

    return p



# Test code

# import genoplot; import networkx as nx; p = genoplot.main()
