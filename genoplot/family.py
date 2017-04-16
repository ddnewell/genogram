# Copyright (c) 2016 by Welded Anvil Technologies (David D. Newell). All Rights Reserved.
# This software is the confidential and proprietary information of
# Welded Anvil Technologies (David D. Newell) ("Confidential Information").
# You shall not disclose such Confidential Information and shall use it
# only in accordance with the terms of the license agreement you entered
# into with Welded Anvil Technologies (David D. Newell).
# @author david@newell.at

import logging
from .utils import calculate_text_size
logger = logging.getLogger("genoplot")


class Family(object):
    """
    Family - defines a family in a pedigree
    :param family: Raw Gedcom parsed family
    :type family: object
    :param pedigree: Pedigree object to which family belongs
    :type pedigree: object
    """
    def __init__(self, family, pedigree=None, font_size=10, hmargin=0, **kwargs):
        """
        Family - defines a family in a pedigree
        :param family: Raw Gedcom parsed family
        :type family: object
        :param pedigree: Pedigree object to which family belongs
        :type pedigree: object
        """
        self._raw = family
        self._pedigree = pedigree
        self._father = None
        self._mother = None

        self._font_size = font_size
        self._hmargin = hmargin
        self.x = 0
        self.y = 0

        self.layout_number = 0
        self.layout_prelim = 0
        self.layout_mod = 0
        self.layout_change = 0
        self.layout_shift = 0
        self.layout_thread = None
        self.layout_ancestor = None
        self.layout_branch = None

        [setattr(self, k, v) for k, v in kwargs.items()]

        self._setup()
        self.width, self.height = self.size()

    def _setup(self):
        self.id = int(self._raw.id.replace("@", "").replace("F", ""))
        self._parent_ids = []
        self._children_ids = []
        for person in self._raw.partners:
            pid = int(person.value.replace("@", "").replace("P", ""))
            self._parent_ids.append(pid)
            if person.tag == "HUSB":
                self._father = pid
            elif person.tag == "WIFE":
                self._mother = pid

        for el in self._raw.child_elements:
            if el.tag == "CHIL":
                pid = int(el.value.replace("@", "").replace("P", ""))
                self._children_ids.append(pid)
        self._sort_children()

    def _sort_children(self):
        self._children_ids.sort(key=self._sort_by_birth)

    def _sort_by_birth(self, cid):
        child = self._pedigree.individual(cid)
        if cid is None or child is None:
            logger.critical("Individual %s does not exist, cannot continue sorting children in family %s", cid, self.id)
            return 0
        if child.birth is None:
            return 0
        elif type(child.birth) is str:
            return 0
        else:
            return child.birth

    def add_child(self, pid):
        """Adds specified individual to family"""
        self._children_ids.append(pid)
        self._sort_children()

    def set_coordinates(self, x, y, add_to_history=False):
        """Sets coordinates for parents

        :param x: Family x coordinate
        :type x: float
        :param y: Family y coordinate
        :type y: float
        """
        father = self.father()
        mother = self.mother()
        self.x = x
        self.y = y
        if not father is None:
            father.set_coordinates(x, y, add_to_history)
            fwidth = father.size()[0]
        else:
            fwidth = self._hmargin
        if not mother is None:
            mwidth = mother.size()[0]
            mx = x+fwidth/2+mwidth/2+self._hmargin*2
            mother.set_coordinates(mx, y, add_to_history)
        else:
            pass

    def father_id(self):
        """Returns father individual ID"""
        return self._father

    def mother_id(self):
        """Returns mother individual ID"""
        return self._mother

    def father(self):
        """Returns father individual object"""
        if self._pedigree is None:
            raise Exception("Pedigree is not defined")
        if self._father is None:
            return None
        return self._pedigree.individual(self._father)

    def mother(self):
        """Returns mother individual object"""
        if self._pedigree is None:
            raise Exception("Pedigree is not defined")
        if self._mother is None:
            return None
        return self._pedigree.individual(self._mother)

    def parent_count(self):
        """Returns number of parents in family"""
        return len(self._parent_ids)

    def parent_ids(self):
        """Returns IDs of parents in family"""
        return self._parent_ids

    def parents(self):
        """Returns Individual objects for parents in family"""
        if self._pedigree is None:
            raise Exception("Pedigree is not defined")
        return [self._pedigree.individual(pid) for pid in self._parent_ids]

    def children_count(self):
        """Returns number of children in family"""
        return len(self._children_ids)

    def children_ids(self):
        """Returns IDs of children in family"""
        return self._children_ids

    def children(self):
        """Returns Individual objects for children in family"""
        if self._pedigree is None:
            raise Exception("Pedigree is not defined")
        return [self._pedigree.individual(pid) for pid in sorted(self._children_ids, key=self._sort_by_birth)]

    def contains_parent(self, pid):
        """Returns whether specified id is a parent in this family

        :param pid: Individual ID
        :type pid: int
        """
        return pid in self._parent_ids

    def contains_child(self, pid):
        """Returns whether specified id is a child in this family

        :param pid: Individual ID
        :type pid: int
        """
        return pid in self._children_ids

    def __contains__(self, pid):
        """Returns whether specified id is in this family (either parent or child)

        :param pid: Individual ID
        :type pid: int
        """
        return self.contains_child(pid) or self.contains_parent(pid)

    def size(self):
        """
        Returns label size of indivdual at specified font size

        :param font_size: Font size for which to calculate size
        :type font_size: float
        :param hmargin: Horizontal margin
        :type hmargin: float
        """
        height = 0
        width = 0

        mother = self.mother()
        father = self.father()

        for parent in self.parents():
            if not parent is None:
                pw, ph = parent.size()
                width += pw
                height += ph

        if width > 0:
            width += self._hmargin*2

        return width, height

