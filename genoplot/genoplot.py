# Copyright (c) 2016 by Welded Anvil Technologies (David D. Newell). All Rights Reserved.
# This software is the confidential and proprietary information of
# Welded Anvil Technologies (David D. Newell) ("Confidential Information").
# You shall not disclose such Confidential Information and shall use it
# only in accordance with the terms of the license agreement you entered
# into with Welded Anvil Technologies (David D. Newell).
# @author david@newell.at

import logging, itertools, svgwrite, time
import networkx as nx
from .family import Family
from .familygraph import FamilyGraph
from .pedigree import Pedigree
from .utils import calculate_text_size
logger = logging.getLogger("genoplot")


class GenoPlot(object):
    def __init__(self,
                name,
                gedcom_file,
                output_file=None,
                font_size=10,
                hmargin=20,
                symbol_size=25,
                page_margin=100
                ):
        """
        GenoPlot - defines a pedigree plot based on specified gedcom file

        :param name: Plot name/title
        :type name: str
        :param gedcom_file: GEDCOM file path
        :type gedcom_file: str
        """
        logger.info("Creating GenoPlot named '%s' from GEDCOM '%s'", name, gedcom_file)
        self.name = name
        self._pedigree = Pedigree(name, gedcom_file, font_size=font_size, hmargin=hmargin)
        if output_file is None:
            self._output_file = "{0}.svg".format(self.name)
        else:
            self._output_file = output_file
        if ".svg" not in self._output_file:
            self._output_file += ".svg"
        self._graph = None
        self._layout = None
        self._font_size = font_size
        self._symbol_size = symbol_size
        self._hmargin = hmargin
        self._node_height = self._symbol_size*2#*6
        self._page_margin = page_margin
        self._connectors = []
        self._image_layers = {
            "-1:duplicates": [],
            "0:connectors": [],
            "1:individuals": [],
            "2:text": [],
            "3:textextent": []
        }

    def draw(self):
        """Draws pedigree plot based on specified parameters"""
        logger.info("Starting plot draw")
        draw_start = time.time()
        self._graph = FamilyGraph(self._pedigree,
                                    font_size=self._font_size,
                                    hmargin=self._hmargin,
                                    node_height=self._node_height,
                                    page_margin=self._page_margin)

        extremes = self._graph.extremes()
        self._svg = svgwrite.Drawing(filename=self._output_file,
                                    size=(extremes[1]+self._page_margin*2, extremes[3]*1.2+self._page_margin*2))

        # for vid, loc in self._layout.items():
        for vid, d in self._graph.items():
            if vid[0] == "F":
                # Draw family
                family = d["el"]
                # father = family.father()
                # if not father is None:
                #     fx = father.x
                #     fy = father.y
                # else:
                #     mother = family.mother()
                #     fx = mother.x
                #     fy = mother.y
                self._draw_family(family.id, family.x, family.y)
                # self._draw_family(int(vid[1:]), *loc)
            else:
                # Draw individual
                individual = d["el"]
                self._draw_individual(individual.id, individual.x, individual.y)
                # self._draw_individual(int(vid[1:]), *loc)

        # for vid, loc in self._layout.items():
        for vid, d in self._graph.items():
            if vid[0] == "F":
                # family = self._pedigree.family(int(vid[1:]))
                family = d["el"]
                father = family.father()
                parent = father
                if father is None:
                    fwidth = self._hmargin
                    parent = family.mother()
                else:
                    fwidth = calculate_text_size(father.output_text(), self._font_size)[0]
                if parent is None:
                    logger.critical("Parent is none for family %s; father: %s; parent: %s; cannot continue drawing", vid, father, parent)
                # Draw child connectors
                midpoint_x = parent.x+fwidth/2+self._hmargin+self._symbol_size/2
                midpoint_y = parent.y+self._symbol_size/2
                # midpoint_x = loc[0]+fwidth/2+self._hmargin+self._symbol_size/2
                # midpoint_y = loc[1]+self._symbol_size/2

                # Collect chlid coordinates
                start = (midpoint_x, midpoint_y)
                targets = []

                # Draw edges to children, if the edges exist in branched graph
                for child in family.children():
                    nid = "P{0}".format(child.id)
                    # if nid in self._branched_graph[vid] and nid in self._layout:
                    if self._graph.has_edge(vid, nid):
                        if not child.x is None and not child.y is None:
                            child_x = child.x
                            child_y = child.y
                        else:
                            logger.warn("Coordinates not persisted to %i", child.id)
                            # child_x, child_y = self._layout["P{0}".format(child.id)]
                        targets.append((child_x+self._symbol_size/2, child_y))
                    elif child.is_parent():
                        for fam in self._pedigree.individual_families(child.id, role="parent"):
                            fid = "F{0}".format(fam.id)
                            # if fid in self._branched_graph[vid]:
                            if self._graph.has_edge(vid, fid):
                                if not child.x is None and not child.y is None:
                                    child_x = child.x
                                    child_y = child.y
                                else:
                                    logger.warn("Position not found for %i - %s, using family %s position", child.id, child.name, fid)
                                    logger.warn("Coordinates not persisted to %i", child.id)
                                    # child_x, child_y = self._layout[fid]
                                targets.append((child_x+self._symbol_size/2, child_y))

                # Draw elbow connectors
                if len(targets) > 0:
                    self._draw_connector_to_multiple(start, targets)

        # Draw duplicate people connectors
        [self._draw_duplicate_person_link(individual) for individual in self._graph.duplicate_individuals()]

        # Draw connectors between added duplicate nodes
        for (nid1, nid2) in self._graph.branch_links():
            individual = self._pedigree.individual(nid1)
            if not individual.x is None and not individual.y is None:
                start = (individual.x, individual.y)
            else:
                logger.warn("Coordinates not persisted to %i", individual.id)
                # start = self._layout["P{0}".format(individual.id)]
            duplicate = self._pedigree.individual(nid2)
            if not duplicate.x is None and not duplicate.y is None:
                end = (duplicate.x, duplicate.y)
            else:
                logger.warn("Coordinates not persisted to %i", duplicate.id)
                # end = self._layout["P{0}".format(duplicate.id)]
            logger.debug("Drawing added duplicate node connector: %s %s", start, end)
            self._draw_duplicate_connector(individual.sex, start, end)

        # Add cached drawing items to image
        [self._svg.add(item) for layer in sorted(self._image_layers) for item in self._image_layers[layer]]
        # Save image
        self._svg.save()
        logger.info("Plot draw complete, took %.2fs", time.time() - draw_start)

    def _draw_family(self, fid, x, y):
        """Draws family on drawing"""
        logger.debug("Drawing family %s at (%.1f, %.1f)", fid, x, y)
        family = self._pedigree.family(fid)
        # family.set_coordinates(x, y)
        father = family.father()
        mother = family.mother()

        if father is None:
            # Draw virtual father
            self._draw_virtual_individual("M", x, y)
        else:
            self._draw_individual(father.id, father.x, father.y)

        if mother is None:
            # Draw virtual mother
            if father is None:
                logger.warn("Family %s has no parents: drawing both virtual mother and father", fid)
                fwidth = self._hmargin
            else:
                fwidth = calculate_text_size(father.output_text(), self._font_size)[0]
            mwidth = self._symbol_size
            mx = x + self._hmargin*2+fwidth/2+mwidth/2
            self._draw_virtual_individual("F", mx, y)
            end = (mx+self._symbol_size/2, y+self._symbol_size/2)
        else:
            self._draw_individual(mother.id, mother.x, mother.y)
            end = (mother.x+self._symbol_size/2, y+self._symbol_size/2)

        # Draw connector between parents
        start = (x+self._symbol_size, y+self._symbol_size/2)
        self._draw_connector(start, end)

    def _draw_virtual_individual(self, sex, x, y):
        """Draws individual on drawing"""
        if sex == "M":
            self._image_layers["1:individuals"].append(
                self._svg.rect(
                    (x, y),
                    (self._symbol_size, self._symbol_size),
                    fill="white",
                    stroke="#555555",
                    style="stroke-dasharray: 4,5;"
                )
            )
        else:
            self._image_layers["1:individuals"].append(
                self._svg.ellipse(
                    (x+self._symbol_size/2, y+self._symbol_size/2),
                    (self._symbol_size/2, self._symbol_size/2),
                    fill="white",
                    stroke="#555555",
                    style="stroke-dasharray: 4,5;"
                )
            )

    def _draw_individual(self, pid, x, y):
        """Draws individual on drawing"""
        individual = self._pedigree.individual(pid)
        individual.set_coordinates(x, y)
        if individual.sex == "M":
            self._image_layers["1:individuals"].append(
                self._svg.rect(
                    (x, y),
                    (self._symbol_size, self._symbol_size),
                    fill=individual.color(),
                    stroke="black"
                )
            )
        else:
            self._image_layers["1:individuals"].append(
                self._svg.ellipse(
                    (x+self._symbol_size/2, y+self._symbol_size/2),
                    (self._symbol_size/2, self._symbol_size/2),
                    fill=individual.color(),
                    stroke="black"
                )
            )

        text_y = y + 1.6*self._symbol_size

        for text in individual.output_text():
            self._image_layers["2:text"].append(
                self._svg.text(
                    text,
                    insert=(x+self._symbol_size/2, text_y),
                    color="black",
                    style="font-size: {0}px; text-anchor: middle; font-family: 'Helvetica Neue';".format(self._font_size)
                )
            )

            ### Temporary
            text_width, text_height = calculate_text_size(text, self._font_size)
            self._image_layers["3:textextent"].append(
                self._svg.rect(
                    (x+self._symbol_size/2-text_width/2, text_y-text_height),
                    (text_width, text_height),
                    fill="none",
                    stroke="blue",
                    style="stroke-dasharray: 1,2;"
                )
            )


            logger.debug("Text %s has width %.2f and height %.2f", text, text_width, text_height)
            text_y += text_height

    def _detect_straight_connector_overlap(self, x1, y1, x2, y2, fid=None):
        """Returns whether there is an overlapping straight line connector"""
        if y1 == y2:
            for cxn in self._connectors:
                if cxn[0][1] == y1 and cxn[1][1] == y2 and (
                    x1 <= cxn[0][0] <= x2 or
                    x1 <= cxn[1][0] <= x2 or
                    cxn[0][0] <= x1 <= cxn[1][0] or
                    cxn[0][0] <= x2 <= cxn[1][0]
                    ):
                        return True

        # If no overlaps detected, return non-overlapping
        return False

    def _find_nonoverlapping_y(self, x1, x2, y):
        """Returns non-overlapping y value for connector"""
        i = 0
        while self._detect_straight_connector_overlap(x1, y, x2, y):
            y -= 8
            i += 1
            if i > 100:
                logger.error("Drawing overlapping connector. Iterated 100 times and could not find open space on layout. X1: %i Y1: %i X2: %i Y2: %i", x1, y1, x2, y2)
                break
        if i > 0:
            logger.debug("Detected overlapping connector. Iterating %i times", i)
        return y

    def _draw_connector_to_multiple(self, start, targets):
        """Draws connector from start coordinate to one or more targets"""
        start_x, start_y = start

        max_x = start_x
        min_x = start_x
        max_y = start_y
        min_y = start_y

        for x, y in targets:
            if x > max_x:
                max_x = x
            if x < min_x:
                min_x = x
            if y > max_y:
                max_y = y
            if y < min_y:
                min_y = y

        middle_y = self._find_nonoverlapping_y(min_x, max_x, max_y - self._symbol_size)

        logger.debug("Drawing connector to multiple targets (%i). Max_X: %i Min_X: %i Max_Y: %i Min_Y: %i Middle_Y: %i", len(targets), max_x, min_x, max_y, min_y, middle_y)

        # Draw vertical section from start
        self._draw_connector(start, (start_x, middle_y))
        # Draw horizontal section
        self._draw_connector((min_x, middle_y), (max_x, middle_y))
        # Draw vertical sections to targets
        for tgt in targets:
            self._draw_connector((tgt[0], middle_y), tgt)

    def _draw_connector(self, start, end):
        """Draws connector between specified coordinates"""
        x1, y1 = start
        x2, y2 = end

        if y1 == y2 or x1 == x2:
            # Straight line connector
            if (start, end) not in self._connectors:
                self._image_layers["0:connectors"].append(
                    self._svg.line(
                        start=start,
                        end=end,
                        stroke="black"
                    )
                )
                self._connectors.append((
                        start, end
                    ))
        else:
            # Elbow connector
            middle_y = self._find_nonoverlapping_y(x1, x2, y2 - self._symbol_size)

            if (start, (x1, middle_y)) not in self._connectors:
                self._image_layers["0:connectors"].append(
                    self._svg.line(
                        start=start,
                        end=(x1, middle_y),
                        stroke="black"
                    )
                )
                self._connectors.append((
                        start, (x1, middle_y)
                    ))
            if ((x1, middle_y), (x2, middle_y)) not in self._connectors:
                self._image_layers["0:connectors"].append(
                    self._svg.line(
                        start=(x1, middle_y),
                        end=(x2, middle_y),
                        stroke="black"
                    )
                )
                self._connectors.append((
                        (x1, middle_y), (x2, middle_y)
                    ))

            if ((x2, middle_y), end) not in self._connectors:
                self._image_layers["0:connectors"].append(
                    self._svg.line(
                        start=(x2, middle_y),
                        end=end,
                        stroke="black"
                    )
                )
                self._connectors.append((
                        (x2, middle_y), end
                    ))

    def _draw_duplicate_person_link(self, individual):
        """Draws connectors for duplicate person"""
        coords = individual.coordinate_history()

        if len(coords) < 2:
            logger.warn("Individual %i - %s marked as duplicate but only has %i coordinates", individual.id, individual.name, len(coords))
            return
        elif len(coords) > 2:
            coords = itertools.combinations(coords, 2)
        else:
            coords = [coords]

        logger.debug("Drawing duplicate person link for %s - coords: %s", individual.name, ", ".join(repr(c) for c in coords))

        [self._draw_duplicate_connector(individual.sex, start, end) for (start, end) in coords]

    def _draw_duplicate_connector(self, sex, start, end):
        """Draws connector between specified coordinates"""
        x1 = start[0] + self._symbol_size/2
        x2 = end[0] + self._symbol_size/2
        y1 = start[1] + self._symbol_size/2
        y2 = end[1] + self._symbol_size/2
        sx, sy = start
        ex, ey = end

        # curve1_x = (x1 - x2) * 0.2 + x1
        # curve1_y = (y1 - y2) * 0.3 + y1
        # curve2_x = (x2 - x1) * 0.2 + x2
        # curve2_y = (y2 - y1) * 0.3 + y2
        # path = "M{0} {1} C {2} {3}, {4} {5}, {6} {7}".format(x1, y1, curve1_x, curve1_y, curve2_x, curve2_y, x2, y2)

        curve_dist = 100

        if y1 == y2:
            curve1_x = (x1 + x2) / 2
            curve1_y = y1 - curve_dist
        elif x1 == x2:
            curve1_x = x1 - curve_dist if sex == "M" else x1 + curve_dist
            curve1_y = (y1 + y2) / 2
        else:
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)

            if dy > dx:
                curve1_x = min(x1, x2) + dx * 0.2
                curve1_y = min(y1, y2) + dy * 0.2
            elif dy < dx:
                curve1_x = min(x1, x2) + dx * 0.1
                curve1_y = max(y1, y2) - dy * 0.3
            else:
                curve1_x = min(x1, x2)
                curve1_y = min(y1, y2)

        path = "M{0} {1} Q {2} {3}, {4} {5}".format(x1, y1, curve1_x, curve1_y, x2, y2)

        self._image_layers["-1:duplicates"].append(
            self._svg.path(
                d=path,
                stroke="#BAFFD2",
                fill="none"
            )
        )

        if sex == "M":
            self._image_layers["-1:duplicates"].append(
                self._svg.rect(
                    (sx - self._symbol_size*0.2, sy - self._symbol_size*0.2),
                    (self._symbol_size*1.4, self._symbol_size*1.4),
                    fill="white",
                    stroke="#BAFFD2"
                )
            )
            self._image_layers["-1:duplicates"].append(
                self._svg.rect(
                    (ex - self._symbol_size*0.2, ey - self._symbol_size*0.2),
                    (self._symbol_size*1.4, self._symbol_size*1.4),
                    fill="white",
                    stroke="#BAFFD2"
                )
            )
        else:
            self._image_layers["-1:duplicates"].append(
                self._svg.ellipse(
                    (sx + self._symbol_size/2, sy + self._symbol_size/2),
                    (self._symbol_size*1.4/2, self._symbol_size*1.4/2),
                    fill="white",
                    stroke="#BAFFD2"
                )
            )
            self._image_layers["-1:duplicates"].append(
                self._svg.ellipse(
                    (ex + self._symbol_size/2, ey + self._symbol_size/2),
                    (self._symbol_size*1.4/2, self._symbol_size*1.4/2),
                    fill="white",
                    stroke="#BAFFD2"
                )
            )

