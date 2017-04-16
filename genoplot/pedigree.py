# Copyright (c) 2016 by Welded Anvil Technologies (David D. Newell). All Rights Reserved.
# This software is the confidential and proprietary information of
# Welded Anvil Technologies (David D. Newell) ("Confidential Information").
# You shall not disclose such Confidential Information and shall use it
# only in accordance with the terms of the license agreement you entered
# into with Welded Anvil Technologies (David D. Newell).
# @author david@newell.at

import logging, gedcom, time, copy
from .family import Family
from .individual import Individual
logger = logging.getLogger("genoplot")


class Pedigree(object):
    def __init__(self, name, gedcom_file, font_size=10, hmargin=0, **kwargs):
        """
        Pedigree - defines a pedigree built from a gedcom file

        :param name: Pedigree name/title
        :type name: str
        :param gedcom_file: GEDCOM file path
        :type gedcom_file: str
        """
        self.name = name
        self._gedcom = gedcom.parse(gedcom_file)
        self._individuals = {}
        self._families = {}
        self._parent_ids = set()
        self._children_ids = set()

        self._font_size = font_size
        self._hmargin = hmargin

        [setattr(self, k, v) for k, v in kwargs.items()]

        self._setup()

    def _setup(self):
        logger.debug("Processing individuals in GEDCOM")
        start = time.time()
        for individual in self._gedcom.individuals:
            try:
                i = Individual(individual, self, font_size=self._font_size)
            except Exception:
                logger.warn("Error adding individual: %s", individual)
                continue

            logger.debug("Adding individual: %s", i.name)
            self._individuals[i.id] = i
        logger.info("Processing individuals took %.4fs", time.time()-start)

        logger.debug("Processing families in GEDCOM")
        start = time.time()
        for family in self._gedcom.families:
            try:
                f = Family(family, self, font_size=self._font_size, hmargin=self._hmargin)
            except Exception:
                logger.warn("Error adding family: %s", family)
                continue

            logger.debug("Adding family: %s", f.id)
            self._families[f.id] = f
            [self._parent_ids.add(id) for id in f.parent_ids()]
            [self._children_ids.add(id) for id in f.children_ids()]
        logger.info("Processing families took %.4fs", time.time()-start)
        logger.info("Parsing GEDCOM complete: %i individuals and %i families found", len(self._individuals), len(self._families))

    def __len__(self):
        """Returns number of individuals in pedigree"""
        return len(self._individuals)

    def duplicate_individual(self, individual):
        """Creates and returns duplicate of supplied individual"""
        if individual.id in self._individuals:
            duplicate = copy.copy(individual)
            duplicate.id = max(self._individuals) + 1
            self._individuals[duplicate.id] = duplicate
            [family.add_child(duplicate.id) for family in self.individual_families(individual.id, role="child")]
            logger.debug("Created duplicate individual: %s\tID: %i -> %i", individual.name, individual.id, duplicate.id)
            return duplicate
        else:
            logger.warn("Creating duplicate individual not in pedigree: %i - %s", individual.id, individual.name)
            return copy.copy(individual)

    def is_parent(self, pid):
        """Returns whether specified individual ID is a parent in a family in this pedigree"""
        return pid in self._parent_ids

    def is_child(self, pid):
        """Returns whether specified individual ID is a child in a family in this pedigree"""
        return pid in self._children_ids

    def individual(self, pid):
        """Returns individual for specified individual ID

        :param pid: Individual ID
        :type pid: int
        """
        if pid not in self._individuals:
            logger.warn("Individual not found in pedigree: %i", pid)
            return None
        else:
            return self._individuals[pid]

    def individual_families(self, pid, role="parent"):
        """Returns families in which specified individual ID belongs

        :param pid: Individual ID
        :type pid: int
        :param role: Role in family
        :type: str
        """
        if role == "parent":
            return [family for family in self._families.values() if family.contains_parent(pid)]
        elif role == "child":
            return [family for family in self._families.values() if family.contains_child(pid)]
        else:
            return [family for family in self._families.values() if pid in family]

    def family(self, fid):
        """Returns family for specified family ID

        :param fid: Family ID
        :type fid: int
        """
        if fid not in self._families:
            return None
        else:
            return self._families[fid]

    def families_with_parent(self, parents=[]):
        """Returns families with parent IDs specified

        :param parents: Parent(s) to find in family
        :type parents: int or list
        """
        if type(parents) is int:
            return [family for family in self._families.values() if parents in family.parent_ids()]
        elif type(parents) is list:
            f = None
            for parent in parents:
                if f is None:
                    f = set(self.families_with_parent(parent))
                else:
                    f.intersection_update(set(self.families_with_parent(parent)))
            return list(f)
        else:
            return []

    def vertices(self):
        """Returns families and individuals who comprise all vertices in family tree plot"""
        vertices = list(self._families.values())
        individual_keys = [individual for individual in self._individuals.values() if not individual.is_parent()]
        vertices.extend(individual_keys)
        return vertices


