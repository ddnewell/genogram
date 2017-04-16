# Copyright (c) 2016 by Welded Anvil Technologies (David D. Newell). All Rights Reserved.
# This software is the confidential and proprietary information of
# Welded Anvil Technologies (David D. Newell) ("Confidential Information").
# You shall not disclose such Confidential Information and shall use it
# only in accordance with the terms of the license agreement you entered
# into with Welded Anvil Technologies (David D. Newell).
# @author david@newell.at

import logging, pygraphviz, time, itertools, sys, traceback
# import grandalf.graphs as grandalf
# from grandalf.utils import convert_nextworkx_graph_to_grandalf
# from grandalf.layouts import SugiyamaLayout
import networkx as nx
from .family import Family
from .pedigree import Pedigree
from . import buchheim
from .utils import calculate_text_size
logger = logging.getLogger("genoplot")


class Branch(object):
    def __init__(self, id, subgraph, parent, font_size, hmargin=10, node_height=50):
        """
        Branch - defines a branch within the family graph

        """
        self.id = id
        self._graph = subgraph
        self.parent = parent
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.hmargin = hmargin
        self.node_height = node_height
        self.font_size = font_size
        self._extremes = [None]*4

        for node in self._graph.nodes_iter():
            self._graph.node[node]["el"].layout_branch = id

    def __len__(self):
        return len(self._graph)

    def __contains__(self, node):
        return node in self._graph

    def _bak_layout(self):
        # Get first node
        v = None
        for vid, deg in self._graph.in_degree().items():
            if deg == 0:
                v = vid
                break
        if v is None:
            logger.critical("Could not find parent node to layout graph: stopping")
            exit(1)

        heights = self.layout_preprocessing(v)

        self._extremes = [None]*4
        dt = firstwalk(Vertex(first_node))
        min_dt = second_walk(dt, height=self.node_height+max(heights))
        if min_dt < 0:
            third_walk(dt, -min_dt)
        first_vertex = dt

        # TODO: update extremes

        logger.debug("<Branch %i> First Element: %s", self.id, v)

        # Update coordinates
        dx = dy = 0
        if not self._extremes[0] == 0:
            dx = -self._extremes[0]
        if not self._extremes[2] == 0:
            dy = -self._extremes[2]
        if dx == 0 and dy == 0:
            logger.debug("<Branch %i> Extremes after initial layout: %s", self.id, self._extremes)
        else:
            logger.debug("<Branch %i> Extremes after initial layout: %s    dx: %.2f  dy: %.2f", self.id, self._extremes, dx, dy)
            self._extremes = [None]*4
            for vid, data in self._graph.nodes(data=True):
                el = data["el"]
                # logger.debug("<Branch %i> El: %s  Moving (%.1f, %.1f) to (%.1f, %.1f)", self.id, el, el.x, el.y, el.x+dx, el.y+dy)
                el.x += dx
                el.y += dy
                if self._extremes[0] is None or el.x < self._extremes[0]:
                    self._extremes[0] = el.x
                if self._extremes[1] is None or el.x > self._extremes[1]:
                    self._extremes[1] = el.x
                if self._extremes[2] is None or el.y < self._extremes[2]:
                    self._extremes[2] = el.y
                if self._extremes[3] is None or el.y > self._extremes[3]:
                    self._extremes[3] = el.y
            logger.debug("<Branch %i> Extremes after adjustment: %s", self.id, self._extremes)
        # Update branch size
        self.width = self._extremes[1] - self._extremes[0]
        self.height = self._extremes[3] - self._extremes[2]

    def layout(self):
        # Get first node
        v = None
        for vid, deg in self._graph.in_degree().items():
            if deg == 0:
                v = vid
                break
        if v is None:
            logger.critical("Could not find parent node to layout branch %i: stopping", self.id)
            exit(1)

        post_order = list(nx.dfs_postorder_nodes(self._graph, v))

        logger.debug("<Branch %i> First Element: %s; post-order: %s", self.id, v, post_order)
        heights = self.layout_preprocessing(v)
        self.layout_first_walk(v)

        self._extremes = [None]*4

        self.layout_second_walk(v, -self._graph.node[v]["el"].layout_prelim, depth=0, height=self.node_height+max(heights))

        # Update coordinates
        dx = dy = 0
        if not self._extremes[0] == 0:
            dx = -self._extremes[0]
        if not self._extremes[2] == 0:
            dy = -self._extremes[2]
        if dx == 0 and dy == 0:
            logger.debug("<Branch %i> Extremes after initial layout: %s", self.id, self._extremes)
        else:
            logger.debug("<Branch %i> Extremes after initial layout: %s    dx: %.2f  dy: %.2f", self.id, self._extremes, dx, dy)
            self._extremes = [None]*4
            for vid, data in self._graph.nodes(data=True):
                el = data["el"]
                # logger.debug("<Branch %i> El: %s  Moving (%.1f, %.1f) to (%.1f, %.1f)", self.id, el, el.x, el.y, el.x+dx, el.y+dy)
                el.x += dx
                el.y += dy
                if self._extremes[0] is None or el.x < self._extremes[0]:
                    self._extremes[0] = el.x
                if self._extremes[1] is None or el.x > self._extremes[1]:
                    self._extremes[1] = el.x
                if self._extremes[2] is None or el.y < self._extremes[2]:
                    self._extremes[2] = el.y
                if self._extremes[3] is None or el.y > self._extremes[3]:
                    self._extremes[3] = el.y
            logger.debug("<Branch %i> Extremes after adjustment: %s", self.id, self._extremes)
        # Update branch size
        self.width = self._extremes[1] - self._extremes[0]
        self.height = self._extremes[3] - self._extremes[2]

    def layout_preprocessing(self, v, prev=None, n=1, lmost_sibling=None, lsibling=None):
        el = self._graph.node[v]["el"]
        el.layout_ancestor = prev
        el.layout_number = n
        el.layout_lmost_sibling = lmost_sibling
        el.layout_lsibling = lsibling
        el.layout_thread = None
        heights = [el.height]
        self._graph.node[v]["children"] = tuple(sorted(self._graph.edge[v].keys(), key=self._sort_children))
        # for n, child in enumerate(self._graph.edge[v]):
        for n, child in enumerate(self._graph.node[v]["children"]):
            lsibling = self._graph.node[v]["children"][n-1] if n > 0 else None
            lmost_sibling = self._graph.node[v]["children"][0] if n > 0 else None # TODO: verify that we don't need to set self to left most sibling
            child_heights = self.layout_preprocessing(child, v, n+1, lmost_sibling, lsibling)
            heights.extend(child_heights)
        return heights

    def _reconcile_birth_date(self, bdate):
        if bdate is None:
            return 0
        elif type(bdate) is str:
            return 0
        else:
            return bdate

    def _sort_children(self, v):
        n = self._graph.node[v]
        if n is None:
            logger.critical("Node %s does not exist, cannot continue sorting children in layout", v)
        in_edges = self._graph.in_edges(v)
        if len(in_edges) == 0:
            logger.critical("No edges into node %s, cannot continue sorting children in layout", v)
        parent_el = self._graph.node[in_edges[0][0]]["el"]
        tgt = n["el"]
        if tgt is None:
            logger.error("Could not populate node for ID: %s", v)
            return 0

        if type(tgt) is Family:
            tgt_father = tgt.father()
            tgt_mother = tgt.mother()
            if tgt_father is None and tgt_mother is None:
                logger.critical("Empty parents found in family while sorting children; cannot continue, family ID: %i", tgt.id)
                exit(1)

            if tgt_father is None and not tgt_mother is None:
                return self._reconcile_birth_date(tgt_mother.birth)
            elif not tgt_father is None and tgt_mother is None:
                return self._reconcile_birth_date(tgt_father.birth)

            if type(parent_el) is Family:
                # Family to family link
                src_father = parent_el.father()
                src_mother = parent_el.mother()

                for s, t in itertools.product((src_father, src_mother), (tgt_father, tgt_mother)):
                    if s is None or t is None:
                        continue
                    if self.parent.is_consanguineous(s.id, t.id):
                        return self._reconcile_birth_date(t.birth)
            else:
                # Individual to family link
                if self.parent.is_consanguineous(parent_el.id, tgt_father.id):
                    return self._reconcile_birth_date(tgt_father.birth)
                else:
                    return self._reconcile_birth_date(tgt_mother.birth)
        else:
            return self._reconcile_birth_date(tgt.birth)

        return 0

    def layout_first_walk(self, v):
        el = self._graph.node[v]["el"]
        if "children" in self._graph.node[v] and len(self._graph.node[v]["children"]) > 0:
            children = self._graph.node[v]["children"]
            default_ancestor = children[0]
            for child in children:
                self.layout_first_walk(child)
                default_ancestor = self.layout_apportion(child, default_ancestor)
            self.layout_execute_shift(v)
            first_child = self._graph.node[children[0]]["el"]
            last_child = self._graph.node[children[-1]]["el"]
            midpoint = (first_child.layout_prelim + last_child.layout_prelim + last_child.size()[0]) / 2
            midpoint -= el.size()[0] / 2
            if not el.layout_lsibling is None:
                left_sibling = self._graph.node[el.layout_lsibling]["el"]
                el.layout_prelim = left_sibling.layout_prelim + left_sibling.size()[0] + self.hmargin
                el.layout_mod = el.layout_prelim - midpoint
            else:
                el.layout_prelim = midpoint
        else:
            if not el.layout_lmost_sibling is None:
                left_sibling = self._graph.node[el.layout_lsibling]["el"]
                el.layout_prelim = left_sibling.layout_prelim + left_sibling.size()[0] + self.hmargin
            else:
                el.layout_prelim = 0

        logger.debug("<Branch %i> Element: %s prelim: %.1f, mod: %.1f, change: %.1f", self.id, v, el.layout_prelim, el.layout_mod, el.layout_change)

    def layout_apportion(self, v, default_ancestor):
        # o = outside, i = inside, l/- = left, r/+ = right
        # v = vertex
        # s = sum(vertex mod properties)
        el = self._graph.node[v]["el"]
        left_sibling = el.layout_lsibling
        logger.debug("<Branch %i> layout_apportion - older_sibling: %s", self.id, left_sibling)
        if not left_sibling is None:
            vir = vor = v
            vil = left_sibling
            vol = el.layout_lmost_sibling
            sir = sor = el.layout_mod

            vil_el = self._graph.node[vil]["el"]
            vir_el = self._graph.node[vir]["el"]
            vol_el = self._graph.node[vol]["el"]
            vor_el = self._graph.node[vor]["el"]

            sil = vil_el.layout_mod
            sol = vol_el.layout_mod

            loop_i = 0

            while (not self.layout_next_element(vil, direction="right") is None and
                    not self.layout_next_element(vir, direction="left") is None):

                vil = self.layout_next_element(vil, direction="right")
                vir = self.layout_next_element(vir, direction="left")
                vol = self.layout_next_element(vol, direction="left")
                vor = self.layout_next_element(vor, direction="right")

                vil_el = self._graph.node[vil]["el"]
                vir_el = self._graph.node[vir]["el"]
                vol_el = self._graph.node[vol]["el"]
                vor_el = self._graph.node[vor]["el"]

                vor_el.layout_ancestor = v

                width = vir_el.size()[0] + self.hmargin * 2
                shift = (vil_el.layout_prelim + sil) - (vir_el.layout_prelim + sir) + width
                logger.info("<Branch %i> Loop #%i... shift: %i", self.id, loop_i, shift)
                if shift > 0:
                    local_ancestor = self.layout_left_ancestor(vil, v, default_ancestor)
                    self.layout_move_subtree(local_ancestor, v, shift)
                    sir += shift
                    sor += shift

                sil += vil_el.layout_mod
                sir += vir_el.layout_mod
                # if not vol is None:
                sol += vol_el.layout_mod
                # if not vor is None:
                sor += vor_el.layout_mod

            vil_next_right = self.layout_next_element(vil, direction="right")
            if not vil_next_right is None and self.layout_next_element(vor, direction="right") is None:# and not vil_next_right == vor:
                logger.debug("<Branch %i> Setting thread from %s to %s", self.id, vor, vil_next_right)
                vor_el.layout_thread = vil_next_right
                vor_el.layout_mod += sil - sor
            else:
                vir_next_left = self.layout_next_element(vir, direction="left")
                if not vir_next_left is None and self.layout_next_element(vol, direction="left") is None:# and not vir_next_left == vol:
                    logger.debug("<Branch %i> Setting thread from %s to %s", self.id, vol, vir_next_left)
                    vol_el.layout_thread = vir_next_left
                    vol_el.layout_mod += sir - sol
                default_ancestor = v

        return default_ancestor

    def layout_oldest_sibling(self, v):
        logger.debug("<Branch %i> layout_oldest_sibling - v: %s", self.id, v)
        if "children" in self._graph.node[v]:
            return self._graph.node[v]["children"][0]
        return None

    def layout_left_sibling(self, v):
        logger.debug("<Branch %i> layout_left_sibling - v: %s", self.id, v)
        in_edges = self._graph.in_edges(nbunch=(v))
        if len(in_edges) > 0:
            parent = in_edges[0][0]
            if ("children" in self._graph.node[parent] and
                        len(self._graph.node[parent]["children"]) > 0 and
                        v in self._graph.node[parent]["children"]):
                index = self._graph.node[parent]["children"].index(v)
                if index > 0:
                    return self._graph.node[parent]["children"][index-1]
        return None

    def layout_next_element(self, v, direction="left"):
        logger.debug("<Branch %i> layout_next_element - Element: %s direction: %s", self.id, v, direction)
        if not self._graph.has_node(v):
            logger.error("<Branch %i> layout_next_element - Graph does not contain node: %s", self.id, v)
            return None
        elif "children" in self._graph.node[v] and len(self._graph.node[v]["children"]) > 0:
            if direction == "left":
                index = 0
            elif direction == "right":
                index = -1
            else:
                index = 0
            logger.debug("<Branch %i> layout_next_element - Element: %s returning %s child at index %i: %s", self.id, v, direction, index, str(self._graph.node[v]["children"][index]))
            return self._graph.node[v]["children"][index]
        else:
            logger.debug("<Branch %i> layout_next_element - Element: %s returning thread: %s", self.id, v, str(self._graph.node[v]["el"].layout_thread))
            return self._graph.node[v]["el"].layout_thread

    def layout_move_subtree(self, vl, vr, shift):
        # l/- = left, r/+ = right
        # v = vertex
        vr_el = self._graph.node[vr]["el"]
        vl_el = self._graph.node[vl]["el"]
        # subtrees = max(1, vr_el.layout_number - vl_el.layout_number)
        # subtrees = 1
        subtrees = vr_el.layout_number - vl_el.layout_number
        logger.info("<Branch %i> layout_move_subtree - vl: %s, vr: %s, shift: %.2f, subtrees: %i", self.id, vl, vr, shift, subtrees)
        vr_el.layout_change -= shift / subtrees
        vr_el.layout_shift += shift
        vl_el.layout_change -= shift / subtrees
        vr_el.layout_prelim += shift
        vr_el.layout_mod += shift

    def layout_execute_shift(self, v):
        if "children" in self._graph.node[v]:
            logger.debug("<Branch %i, node %s> Executing shift", self.id, v)
            shift = 0
            change = 0
            for child in reversed(self._graph.node[v]["children"]):
                child_el = self._graph.node[child]["el"]
                child_el.layout_prelim += shift
                child_el.layout_mod += shift
                change += child_el.layout_change
                shift += child_el.layout_shift + change

    def layout_left_ancestor(self, vil, v, default_ancestor):
        logger.info("<Branch %i> layout_left_ancestor - vil: %s  v: %s  default_ancestor: %s", self.id, vil, v, default_ancestor)
        if self._graph.has_node(vil):
            vil_ancestor = self._graph.node[vil]["el"].layout_ancestor
            if not vil_ancestor is None:
                in_edges = self._graph.in_edges(nbunch=[vil_ancestor])
                if len(in_edges) > 0:
                    parent = in_edges[0][0]
                    if "children" in self._graph.node[parent] and len(self._graph.node[parent]["children"]):
                        if v in self._graph.node[parent]["children"]:
                            return vil_ancestor
        return default_ancestor

    def layout_second_walk(self, v, shift, depth, height=0):
        el = self._graph.node[v]["el"]
        el.x = el.layout_prelim + shift
        el.y = depth
        logger.debug("<Branch %i> Element: %s (%.1f, %.1f)", self.id, v, el.x, el.y)
        logger.debug("<Branch %i> Element: %s (%.1f, %.1f) prelim: %.1f, mod: %.1f, change: %.1f", self.id, v, el.x, el.y, el.layout_prelim, el.layout_mod, el.layout_change)
        if self._extremes[0] is None or el.x < self._extremes[0]:
            self._extremes[0] = el.x
        if self._extremes[1] is None or el.x > self._extremes[1]:
            self._extremes[1] = el.x
        if self._extremes[2] is None or el.y < self._extremes[2]:
            self._extremes[2] = el.y
        if self._extremes[3] is None or el.y > self._extremes[3]:
            self._extremes[3] = el.y
        if "children" in self._graph.node[v]:
            for child in self._graph.node[v]["children"]:
                self.layout_second_walk(child, shift + el.layout_mod, depth + height, height)

    def set_coordinates(self, x, y):
        """Sets coordinates for branch and applies changes to all nodes"""
        dx = x - self.x
        dy = y - self.y
        self.x = x
        self.y = y

        self._extremes = [None]*4

        for vid, data in self._graph.nodes(data=True):
            el = data["el"]
            el.x += dx
            el.y += dy
            if self._extremes[0] is None or el.x < self._extremes[0]:
                self._extremes[0] = el.x
            if self._extremes[1] is None or el.x > self._extremes[1]:
                self._extremes[1] = el.x
            if self._extremes[2] is None or el.y < self._extremes[2]:
                self._extremes[2] = el.y
            if self._extremes[3] is None or el.y > self._extremes[3]:
                self._extremes[3] = el.y

    def persist_coordinates(self):
        """Sets coordinates for branch and applies changes to all nodes"""
        [
            data["el"].set_coordinates(data["el"].x, data["el"].y, add_to_history=True)
            for vid, data in self._graph.nodes(data=True)
        ]

    def _buchheim_layout(self):
        # Get first node
        v = None
        for vid, deg in self._graph.in_degree().items():
            if deg == 0:
                v = vid
                break
        if v is None:
            logger.critical("Could not find parent node to layout graph: stopping")
            exit(1)
        # Create layout nodes
        self.first_vertex = buchheim.LayoutNode(vid=v,
                                                branch=self,
                                                graph=self._graph,
                                                font_size=self.font_size,
                                                hmargin=self.hmargin,
                                                node_height=self.node_height)
        # Start first walk
        buchheim.first_walk(self.first_vertex)
        # Start second walk
        buchheim.second_walk(self.first_vertex)
        # Update coordinates
        self._extremes = self.first_vertex.update()
        dx = dy = 0
        if not self._extremes[0] == 0:
            dx = -self._extremes[0]
        if not self._extremes[2] == 0:
            dy = -self._extremes[2]
        if dx == 0 and dy == 0:
            logger.debug("Extremes after initial layout: %s", self._extremes)
        else:
            logger.info("Extremes after initial layout: %s    dx: %.2f  dy: %.2f", self._extremes, dx, dy)
            self._extremes = self.first_vertex.alter_coordinates(dx, dy)
            logger.info("Extremes after adjustment: %s", self._extremes)
        # Update branch size
        self.width = self._extremes[1] - self._extremes[0]
        self.height = self._extremes[3] - self._extremes[2]

    def extremes(self):
        """Returns coordinate extremes for branch"""
        return self._extremes

    def size(self):
        """Returns overall width and height for branch"""
        return self.width, self.height


class FamilyGraph(object):
    def __init__(self, pedigree, font_size, hmargin=10, node_height=50, page_margin=10):
        self._pedigree = pedigree
        self.hmargin = hmargin
        self.node_height = node_height
        self.page_margin = page_margin
        self.font_size = font_size
        self._branches = []
        self._duplicate_people = set()
        self._graph = None
        self._branched_graph = None
        self._undirected_graph = None
        self._branch_links = set()
        self._create()
        self._layout()

    def has_node(self, node):
        return self._branched_graph.has_node(node)

    def has_edge(self, u, v):
        return self._branched_graph.has_edge(u, v)

    def extremes(self):
        """Returns coordinate extremes for familygraph"""
        extremes = [None]*4
        for branch in self._branches:
            bext = branch.extremes()
            for i in range(4):
                if bext[i] is None: #TODO
                    continue
                if extremes[i] is None or (i%2 == 0 and bext[i] < extremes[i]) or (bext[i] > extremes[i]):
                    extremes[i] = bext[i]
        return extremes

    def is_consanguineous(self, pid1, pid2):
        """Returns whether the specified individual IDs share a bloodline"""
        # Check for basic path between individuals, otherwise have to look at families
        graph_pid1 = "P{0}".format(pid1)
        graph_pid2 = "P{0}".format(pid2)
        if graph_pid1 in self._undirected_graph and \
                    graph_pid2 in self._undirected_graph and \
                    nx.has_path(self._undirected_graph, graph_pid1, graph_pid2):
            return True
        # Get individuals
        p1 = self._pedigree.individual(pid1)
        p2 = self._pedigree.individual(pid2)

        if graph_pid1 not in self._undirected_graph and graph_pid2 in self._undirected_graph:
            # Get first person's families
            f1 = ["F{0}".format(family.id) for family in p1.families()]
            # Check for path from first person's families to second person
            if any(nx.has_path(self._undirected_graph, f, graph_pid2) for f in f1 if f in self._undirected_graph):
                return True

        if graph_pid1 in self._undirected_graph and graph_pid2 not in self._undirected_graph:
            # Get second person's families
            f2 = ["F{0}".format(family.id) for family in p2.families()]
            # Check for path from first person families to second person
            if any(nx.has_path(self._undirected_graph, f, graph_pid1) for f in f2 if f in self._undirected_graph):
                return True

        if graph_pid1 not in self._undirected_graph and graph_pid2 not in self._undirected_graph:
            # Get families
            f1 = ["F{0}".format(family.id) for family in p1.families()]
            f2 = ["F{0}".format(family.id) for family in p2.families()]
            # If if one of the individuals has no families, don't continue
            if len(f1) == 0 or len(f2) == 0:
                return False
            # Check for paths between combinations of families, otherwise, individuals are not consanguineous
            return any(nx.has_path(self._undirected_graph, family1, family2)
                        for family1, family2 in itertools.product(f1, f2)
                        if family1 in self._undirected_graph and family2 in self._undirected_graph)

        return False

    def items(self):
        return self._branched_graph.nodes_iter(data=True)

    def branch_links(self):
        return self._branch_links

    def duplicate_individuals(self):
        return self._duplicate_people

    def node(self, id):
        try:
            return self._branched_graph.node[id]
        except:
            logger.warn("Could not retrieve %s node from familygraph", id)
            return None

    def _create(self):
        """Returns NetworkX directed graph of vertices in pedigree"""
        logger.info("Creating family graph")
        create_start = time.time()
        self._graph = nx.DiGraph()

        vertices = {}
        self._branch_links = set()

        # Create vertices
        for el in self._pedigree.vertices():
            if type(el) is Family:
                vid = "F{0}".format(el.id)
            else:
                vid = "P{0}".format(el.id)
            # Add node to graph
            self._graph.add_node(vid, el=el)
            vertices[vid] = el

        for vid, v in vertices.items():
            logger.debug("Adding vertex %s of type %s", vid, type(v))
            if type(v) is Family:
                # Note: don't have to reach up to parent's families because they are captured in another family's down edges
                # A family typed vertex has children, which may be in families
                logger.debug("Family has %i children", v.children_count())
                children = v.children()
                for child in children:
                    if child.is_parent():
                        logger.debug("Child is parent: %s", child.id)
                        for family in self._pedigree.families_with_parent(child.id):
                            fid = "F{0}".format(family.id)
                            self._graph.add_edge(vid, fid, link="standard")
                            # self._graph.node[fid]["sibling"] = children.index(child)
                            logger.debug("Adding edge %s to %s", vid, fid)
                    else:
                        cid = "P{0}".format(child.id)
                        self._graph.add_edge(vid, cid, link="standard")
                        # self._graph.node[cid]["sibling"] = children.index(child)
                        logger.debug("Adding edge %s to %s", vid, cid)
            else:
                # An individual typed vertex does not have any children; get family for edges into vertex
                mother = v.mother
                father = v.father

                if mother is None and father is None:
                    continue
                elif mother is None:
                    families = self._pedigree.families_with_parent(mother)
                elif father is None:
                    families = self._pedigree.families_with_parent(father)
                else:
                    families = self._pedigree.families_with_parent([mother, father])

                logger.debug("Number of families for vertex %s: %i", vid, len(families))

                for family in families:
                    self._graph.add_edge("F{0}".format(family.id), vid, link="standard")
                    logger.debug("Adding edge %s to %s", "F{0}".format(family.id), vid)

        # Create branched graph
        self._branched_graph = nx.maximum_branching(self._graph)

        for v, d in self._graph.nodes_iter(data=True):
            for k, val in d.items():
                self._branched_graph.node[v][k] = val

        # Add duplicate children to support cross-branch links
        removed_edges = set(self._graph.edges_iter()) - set(self._branched_graph.edges_iter())
        for (nid1, nid2) in removed_edges:
            # Update original graph
            self._graph[nid1][nid2]["link"] = "branch"
            # Create cross-branch links
            if nid2[0] == "F":
                children = self._pedigree.family(int(nid2[1:])).parents()
            else:
                children = [self._pedigree.individual(int(nid2[1:]))]

            if nid1[0] == "F":
                family = self._pedigree.family(int(nid1[1:]))
                for child in children:
                    if family.contains_child(child.id):
                        duplicate_child = self._pedigree.duplicate_individual(child)
                        # vwidth = calculate_text_size(el.output_text(), self._font_size)[0]
                        self._branched_graph.add_node("P{0}".format(duplicate_child.id), el=duplicate_child)
                        self._branched_graph.add_edge(nid1, "P{0}".format(duplicate_child.id))
                        self._branch_links.add((child.id, duplicate_child.id))
                        logger.debug("Added duplicate child: %i, %i", child.id, duplicate_child.id)

        # Create an undirected copy of graph
        self._undirected_graph = self._graph.to_undirected()

        # logger.info("Family graph creation took %.2fs", time.time()-create_start)
        # logger.info("Creating branches")
        # branch_start = time.time()

        # Create branches
        self._branches = [Branch(id=i,
                                subgraph=component,
                                parent=self,
                                font_size=self.font_size,
                                hmargin=self.hmargin,
                                node_height=self.node_height)
                            for i, component in enumerate(nx.weakly_connected_component_subgraphs(self._branched_graph, copy=False))]

        # logger.info("Branch creation took %.4fs", time.time()-branch_start)

        logger.info("Family graph and branch creation took %.2fs", time.time()-create_start)

    def _layout(self):
        """Calculate layout for graph"""
        logger.info("Starting graph layout for %i branches", len(self._branches))
        layout_start = time.time()

        branch_graph = nx.Graph()

        x = self.page_margin
        y = self.page_margin

        for i, branch in enumerate(self._branches):
            branch_layout_start = time.time()
            # try:
            branch.layout()
            branch.set_coordinates(x, y)
            branch.persist_coordinates()
            bwidth, bheight = branch.size()
            x += bwidth + self.hmargin*10
            # y += bheight + self.node_height*2
            logger.debug("<Branch %i> Width: %.2f Height: %.2f", i, bwidth, bheight)
            logger.debug("<Branch %i> layout took: %.4fs", i, time.time()-branch_layout_start)
            # except Exception as e:
            #     logger.warn("Error laying out branch %i:\t%s\n%s", i, sys.exc_info()[0], "".join(traceback.format_tb(sys.exc_info()[2])))
        logger.info("Graph layout took: %.2fs", time.time()-layout_start)




        # layout_start = time.time()

        # branch_graph = self._graph.copy()
        # remove_edges = [(u,v) for u, v, d in branch_graph.edges_iter(data=True) if d["link"] == "standard"]
        # branch_graph.remove_edges_from(remove_edges)
        # branched_edges = branch_graph.edges()
        # branched_nodes = {}
        # for u, v in branched_edges:
        #     branched_nodes[u] = set()
        #     branched_nodes[v] = set()

        # branch_graph = nx.Graph()

        # for i, branch in enumerate(self._branches):
        #     branch_layout_start = time.time()
        #     branch.layout()
        #     bwidth, bheight = branch.size()
        #     branch_graph.add_node(i, width=bwidth, height=bheight)
        #     logger.info("<Branch %i> Added node to branch graph width: %i height: %i", i, bwidth, bheight)
        #     for k in branched_nodes:
        #         if k in branch:
        #             branched_nodes[k].add(i)
        #     logger.info("Branch %i layout took: %.4fs", i, time.time() - branch_layout_start)

        # for u, v in branched_edges:
        #     for s, t in itertools.product(branched_nodes[u], branched_nodes[v]):
        #         if branch_graph.has_edge(s, t):
        #             branch_graph.edge[s][t]["weight"] += 1
        #         else:
        #             branch_graph.add_edge(s, t, weight=1)

        # branch_pos = nx.spring_layout(branch_graph, dim=5000, k=len(branch_graph))

        # for i, branch in enumerate(self._branches):
        #     logger.info("<Branch %i> Set branch position to x: %.2f y: %.2f", i, 6000*branch_pos[i][0]+x, 6000*branch_pos[i][0]+y)
        #     branch.set_coordinates(6000*branch_pos[i][0]+x, 6000*branch_pos[i][0]+y)
        #     branch.persist_coordinates()

        # logger.info("Graph layout took: %.4fs", time.time() - layout_start)

    def _create_original(self):
        """Returns NetworkX directed graph of vertices in pedigree"""
        self._graph = nx.DiGraph()

        vertices = {}
        node_height = 1.2

        max_family_width = None
        max_individual_width = None
        min_family_width = None
        min_individual_width = None

        # Create vertices
        for el in self._pedigree.vertices():
            if type(el) is Family:
                vid = "F{0}".format(el.id)
                fsize = el.size()
                vwidth = fsize[0]
                if max_family_width is None or vwidth > max_family_width:
                    max_family_width = vwidth
                if min_family_width is None or vwidth < min_family_width:
                    min_family_width = vwidth
                el_type = "Family"
                pids = el.parent_ids()
            else:
                vid = "P{0}".format(el.id)
                psize = el.size()
                vwidth = psize[0]
                if max_individual_width is None or vwidth > max_individual_width:
                    max_individual_width = vwidth
                if min_individual_width is None or vwidth < min_individual_width:
                    min_individual_width = vwidth
                el_type = "Individual"
                pids = [el.id]

            self._graph.add_node(vid,
                                el=el,
                                el_type=el_type,
                                pids=pids,
                                label=vid,
                                width=vwidth,
                                height=node_height)
            vertices[vid] = el

        for vid, v in vertices.items():
            logger.debug("Adding vertex %s of type %s", vid, type(v))
            if type(v) is Family:
                # Note: don't have to reach up to parent's families because they are captured in another family's down edges
                # A family typed vertex has children, which may be in families
                logger.debug("Family has %i children", v.children_count())
                for child in v.children():
                    if child.is_parent():
                        logger.debug("Child is parent: %s", child.id)
                        for family in self._pedigree.families_with_parent(child.id):
                            fid = "F{0}".format(family.id)
                            self._graph.add_edge(vid, fid, link="standard")
                            logger.debug("Adding edge %s to %s", vid, fid)
                    else:
                        cid = "P{0}".format(child.id)
                        self._graph.add_edge(vid, cid, link="standard")
                        logger.debug("Adding edge %s to %s", vid, cid)
            else:
                # An individual typed vertex does not have any children; get family for edges into vertex
                mother = v.mother
                father = v.father

                if mother is None and father is None:
                    continue
                elif mother is None:
                    families = self._pedigree.families_with_parent(mother)
                elif father is None:
                    families = self._pedigree.families_with_parent(father)
                else:
                    families = self._pedigree.families_with_parent([mother, father])

                logger.debug("Number of families for vertex %s: %i", vid, len(families))

                for family in families:
                    self._graph.add_edge("F{0}".format(family.id), vid, link="standard")
                    logger.debug("Adding edge %s to %s", "F{0}".format(family.id), vid)

        # Create branched graph
        self._branched_graph = nx.maximum_branching(self._graph)

        # Add duplicate children to support cross-branch links
        removed_edges = set(self._graph.edges_iter()) - set(self._branched_graph.edges_iter())
        for (nid1, nid2) in removed_edges:
            # Update original graph
            self._graph[nid1][nid2]["link"] = "branch"
            # Create cross-branch links
            if nid2[0] == "F":
                children = self._pedigree.family(int(nid2[1:])).parents()
            else:
                children = [self._pedigree.individual(int(nid2[1:]))]

            if nid1[0] == "F":
                family = self._pedigree.family(int(nid1[1:]))
                for child in children:
                    if family.contains_child(child.id):
                        duplicate_child = self._pedigree.duplicate_individual(child)
                        vwidth = el.width
                        self._branched_graph.add_node("P{0}".format(duplicate_child.id),
                                                        el=duplicate_child,
                                                        el_type="Individual",
                                                        pids=[duplicate_child.id],
                                                        label=duplicate_child.id,
                                                        width=vwidth,
                                                        height=node_height)
                        self._branched_graph.add_edge(nid1, "P{0}".format(duplicate_child.id))
                        self._branch_links.add((child.id, duplicate_child.id))
                        logger.debug("Added duplicate child: %i, %i", child.id, duplicate_child.id)

        # Normalize node widths
        for n in self._branched_graph:
            before = self._branched_graph.node[n]["width"]
            if self._branched_graph.node[n]["el_type"] == "Family":
                self._branched_graph.node[n]["width"] = max(self._branched_graph.node[n]["width"] * 2 / min_family_width, 2 * 2)
            else:
                self._branched_graph.node[n]["width"] *= 0.7 / min_individual_width

        # Create branches
        self._branches = [Branch(component, self) for component in nx.weakly_connected_component_subgraphs(self._branched_graph)]

        # Create an undirected copy of graph
        self._undirected_graph = self._graph.to_undirected()

    def _graphviz_layout(self):
        """"Calculate layout for graph using graphviz"""
        layout_start = time.time()

        # -------------------------
        #  Graphviz Layout Method
        # -------------------------
        # self._layout = nx.nx_agraph.pygraphviz_layout(self._graph, prog="dot")
        A = nx.nx_agraph.to_agraph(self._branched_graph)
        A.graph_attr["remincross"] = "true"
        A.graph_attr["ordering"] = "out"
        A.graph_attr["packMode"] = "node"
        A.layout(prog="dot")
        self._layout = {}
        people = set()
        self._duplicate_people = set()

        # Get maximum coordinates
        self.max_x = None
        self.max_y = None
        self.min_x = None
        self.min_y = None

        for n in self._branched_graph:
            node = pygraphviz.Node(A, n)
            try:
                coord = node.attr["pos"].split(',')
                self._layout[n] = (float(coord[0]), float(coord[1]))
            except:
                logger.warn("No position for node %s", n)
                self._layout[n] = (0.0, 0.0)

            if self.max_x is None or self._layout[n][0] > self.max_x:
                self.max_x = self._layout[n][0]
            if self.max_y is None or self._layout[n][1] > self.max_y:
                self.max_y = self._layout[n][1]

            if self.min_x is None or self._layout[n][0] < self.min_x:
                self.min_x = self._layout[n][0]
            if self.min_y is None or self._layout[n][1] < self.min_y:
                self.min_y = self._layout[n][1]

            if n[0] == "F":
                family = self._pedigree.family(int(n[1:]))
                father = family.father()
                mother = family.mother()
                if not father is None:
                    if father in people:
                        self._duplicate_people.add(father)
                    else:
                        people.add(father)
                if not mother is None:
                    if mother in people:
                        self._duplicate_people.add(mother)
                    else:
                        people.add(mother)
            else:
                individual = self._pedigree.individual(int(n[1:]))
                if individual in people:
                    self._duplicate_people.add(individual)
                else:
                    people.add(individual)

        if self.max_x is None or self.max_y is None or self.min_x is None or self.min_y is None:
            logger.critical("Error computing layout: bounding box not completed (%.2f, %.2f, %.2f, %.2f)", self.min_x, self.min_y, self.max_x, self.max_y)
            exit(1)

        # Adjust coordinate values to SVG values and set overall coordinates
        for i, c in self._layout.items():
            self._layout[i] = (c[0] + self._margin - self.min_x, self.max_y - c[1] + self._margin)

            if i[0] == "F":
                family = self._pedigree.family(int(i[1:])).set_coordinates(*self._layout[i], self._font_size, self._hmargin)
            else:
                self._pedigree.individual(int(i[1:])).set_coordinates(*self._layout[i])

        if len(self._duplicate_people) > 1:
            logger.warn("Found %i duplicate people in drawing: %s", len(self._duplicate_people), ", ".join(d.name for d in self._duplicate_people if not d is None))

        logger.info("Pedigree layout completed in %.4fs", time.time()-layout_start)

    def _grandalf_layout(self):
        # ----------------
        # Grandalf version
        # ----------------

        vertices = {}
        edges = []

        # Create vertices
        for el in self._pedigree.vertices():
            if type(el) is Family:
                vid = "F{0}".format(el.id)
            else:
                vid = "P{0}".format(el.id)
            v = grandalf.Vertex(el)
            # v.data = el
            v.view = NodeView(w=50, h=50)
            vertices[vid] = v

        for vid, v in vertices.items():
            if type(v.data) is Family:
                # Note: don't have to reach up to parent's families because they are captured in another family's down edges
                # A family typed vertex has children, which may be in families
                for child in v.data.children():
                    if child.is_parent():
                        for family in self._pedigree.families_with_parent(child.id):
                            edges.append(grandalf.Edge(v, vertices["F{0}".format(family.id)]))
            else:
                # An individual typed vertex does not have any children; get family for edges into vertex
                mother = v.data.mother
                father = v.data.father

                if mother is None and father is None:
                    continue
                elif mother is None:
                    families = self._pedigree.families_with_parent(mother)
                elif father is None:
                    families = self._pedigree.families_with_parent(father)
                else:
                    families = self._pedigree.families_with_parent([mother, father])

                for family in families:
                    edges.append(grandalf.Edge(vertices["F{0}".format(family.id)], v))

        G = grandalf.Graph(list(vertices.values()), edges)

        for subgraph in G.C:
            logger.info("Processing layout for subgraph %s", subgraph)
            sug = SugiyamaLayout(subgraph)
            sug.init_all()
            sug.draw()

        self._graph = G






