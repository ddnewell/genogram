# Copyright (c) 2016 by Welded Anvil Technologies (David D. Newell). All Rights Reserved.
# This software is the confidential and proprietary information of
# Welded Anvil Technologies (David D. Newell) ("Confidential Information").
# You shall not disclose such Confidential Information and shall use it
# only in accordance with the terms of the license agreement you entered
# into with Welded Anvil Technologies (David D. Newell).
# @author david@newell.at

import logging, itertools
from .family import Family
logger = logging.getLogger("genoplot")

class LayoutNode(object):
    def __init__(self, vid, branch, graph, font_size=10, hmargin=0, vmargin=0, parent=None, depth=0, number=1, child=0):
        self.vid = vid
        self.branch = branch
        self.node = branch.parent.node(vid)["el"]
        if self.node is None:
            logger.error("Could not populate node for ID: %s", vid)
        if type(self.node) is Family:
            self.width, h = self.node.size(font_size, hmargin=hmargin)
        else:
            self.width, h = self.node.size(font_size)
            self.width += hmargin
        self.height = vmargin
        logger.debug("Layout Node %s width: %i height: %i", vid, self.width, self.height)
        self.x = self.width+hmargin
        self.y = depth
        self.font_size = font_size
        self.hmargin = hmargin
        self.vmargin = vmargin
        self.graph = graph
        # Create layout nodes for children sorted by birth date
        self.children = tuple(LayoutNode(vid=c,
                                        branch=branch,
                                        graph=graph,
                                        font_size=font_size,
                                        hmargin=hmargin,
                                        vmargin=vmargin,
                                        parent=self,
                                        depth=depth+self.height,
                                        number=i+1,
                                        child=i)
                         for i, c in enumerate(sorted(graph.successors(self.vid), key=self._sort_children)))
        self.parent = parent
        self.thread = None
        self.offset = 0
        self.mod = 0
        self.ancestor = self
        self.change = self.shift = 0
        self.child = child
        self._lmost_sibling = None
        #this is the number of the node in its group of siblings 1..n
        self.number = number

    def _reconcile_birth_date(self, bdate):
        if bdate is None:
            return 0
        elif type(bdate) is str:
            return 0
        else:
            return bdate

    def _sort_children(self, v):
        n = self.branch.parent.node(v)
        if n is None:
            logger.critical("Node %s does not exist, cannot continue sorting children in layout", v)
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

            if type(self.node) is Family:
                # Family to family link
                src_father = self.node.father()
                src_mother = self.node.mother()

                for s, t in itertools.product((src_father, src_mother), (tgt_father, tgt_mother)):
                    if s is None or t is None:
                        continue
                    if self.branch.parent.is_consanguineous(s.id, t.id):
                        return self._reconcile_birth_date(t.birth)
            else:
                # Individual to family link
                if self.branch.parent.is_consanguineous(self.node.id, tgt_father.id):
                    return self._reconcile_birth_date(tgt_father.birth)
                else:
                    return self._reconcile_birth_date(tgt_mother.birth)
        else:
            return self._reconcile_birth_date(tgt.birth)

        return 0

    def alter_coordinates(self, dx, dy):
        self.x += dx
        self.y += dy
        extremes = [self.x, self.x, self.y, self.y]
        for c in self.children:
            coords = c.alter_coordinates(dx, dy)
            for i in range(4):
                if (i%2 == 0 and coords[i] < extremes[i]) or (coords[i] > extremes[i]):
                    extremes[i] = coords[i]
        return extremes

    def update(self):
        extremes = [self.x, self.x, self.y, self.y]
        for c in self.children:
            coords = c.update()
            for i in range(4):
                if (i%2 == 0 and coords[i] < extremes[i]) or (coords[i] > extremes[i]):
                    extremes[i] = coords[i]
        return extremes

    def persist_coordinates(self):
        if type(self.node) is Family:
            self.node.set_coordinates(self.x, self.y, self.font_size, hmargin=self.hmargin, add_to_history=True)
        else:
            self.node.set_coordinates(self.x, self.y, add_to_history=True)
        [c.persist_coordinates() for c in self.children]

    def right_sibling(self):
        if self.parent:
            if self.child + 1 < len(self.parent.children) and self.child > -1:
                return self.parent.children[self.child + 1]
        return None

    def left_sibling(self):
        if self.parent:
            if self.child > 0 and self.child < len(self.parent.children):
                return self.parent.children[self.child - 1]
        return None

    def get_leftmost_sibling(self):
        if not self._lmost_sibling and self.parent and self != self.parent.children[0]:
            self._lmost_sibling = self.parent.children[0]
        return self._lmost_sibling


def first_walk(v):
    distance = v.width
    if len(v.children) == 0:
        if v.get_leftmost_sibling():
            v.x = v.left_sibling().x + distance
        else:
            v.x = 0
    else:
        default_ancestor = v.children[0]
        for w in v.children:
            first_walk(w)
            default_ancestor = apportion(w, default_ancestor, distance)
        execute_shifts(v)

        midpoint = (v.children[0].x + v.children[-1].x) / 2

        ell = v.children[0]
        arr = v.children[-1]
        w = v.left_sibling()
        if w:
            v.x = w.x + distance
            v.mod = v.x - midpoint
        else:
            v.x = midpoint
    return v


def apportion(v, default_ancestor, distance):
    w = v.left_sibling()
    if w is not None:
        #in buchheim notation:
        #i == inner; o == outer; r == right; l == left;
        vir = vor = v
        vil = w
        vol = v.get_leftmost_sibling()
        sir = sor = v.mod
        sil = vil.mod
        sol = vol.mod
        while vil.right_sibling() and vir.left_sibling():
            vil = vil.right_sibling()
            vir = vir.left_sibling()
            if not vol is None:
                vol = vol.left_sibling()
            if not vor is None:
                vor = vor.right_sibling()
            if not vor is None:
                vor.ancestor = v
            shift = (vil.x + vil.width + sil) - (vir.x + vir.width + sir) + distance
            if shift > 0:
                a = ancestor(vil, v, default_ancestor)
                move_subtree(a, v, shift)
                sir = sir + shift
                sor = sor + shift
            if not vil is None:
                sil += vil.mod
            if not vir is None:
                sir += vir.mod
            if not vol is None:
                sol += vol.mod
            if not vor is None:
                sor += vor.mod

        if not vil is None and not vor is None:
            if vil.right_sibling() and not vor.right_sibling():
                vor.thread = vil.right_sibling()
                vor.mod += sil - sor
            else:
                if vir.left_sibling() and not vol.left_sibling():
                    vol.thread = vir.left_sibling()
                    vol.mod += sir - sol
                default_ancestor = v
    return default_ancestor


def move_subtree(wl, wr, shift):
    if not wl == wr:
        subtrees = wr.number - wl.number
        if subtrees <= 0:
            logger.error("Error moving subtrees, difference is less than zero; wr: %s with number %i - wl: %s with number %i", wr.vid, wr.number, wl.vid, wl.number)

        wr.change -= shift / subtrees
        wl.change += shift / subtrees

        wr.shift += shift
        wr.x += shift
        wr.mod += shift


def execute_shifts(v):
    shift = change = 0
    for w in v.children[::-1]:
        w.x += shift
        w.mod += shift
        change += w.change
        shift += w.shift + change


def ancestor(vil, v, default_ancestor):
    if vil.ancestor in v.parent.children:
        return vil.ancestor
    else:
        return default_ancestor


def second_walk(v, m=0, depth=0):
    v.x += m
    v.y = depth

    for w in v.children:
        second_walk(w, m + v.mod, depth+v.height)
