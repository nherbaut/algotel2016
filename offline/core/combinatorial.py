import os
import re
import subprocess
import sys
from collections import defaultdict
from itertools import chain, combinations, product

OPTIM_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../optim')
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../results')

from threading import Lock

mutex = Lock()


def shortest_path(node1, node2):
    '''

    :param node1: a name of a service_graph node
    :param node2: a name of a service_graph node
    :return: the shortest_path length
    '''
    # print("%s %s" % (node1,node2))

    if node1 == node2:
        return 0

    with open(os.path.join(RESULTS_FOLDER, "node1.data"), "w") as f:
        f.write("%s\n" % node1)
    with open(os.path.join(RESULTS_FOLDER, "node2.data"), "w") as f:
        f.write("%s\n" % node2)

    subprocess.call(["scip", "-c", "read %s" % os.path.join(OPTIM_FOLDER, "sp.zpl"), "-c",
                     "read %s" % os.path.join(OPTIM_FOLDER, "sp.zpl"), "-c", "optimize ", "-c",
                     "write solution %s" % (os.path.join(RESULTS_FOLDER, "solutions.data")), "-c", "q"],
                    stdout=open(os.devnull, 'wb')
                    )

    with open(os.path.join(RESULTS_FOLDER, "solutions.data"), "r") as sol:
        data = sol.read()
        data = data.split("\n")

    for line in data:
        matches = re.findall("^objective value: *([0-9\.]*)$", line)
        if (len(matches) > 0):
            return float(matches[0])

    return None


def generate_problem_combinaisons(node_count, group_count):
    res = []
    if group_count == node_count:  # trivial
        return [[1 for x in range(1, node_count + 1)], ]
    elif group_count == 1:  # also trivial
        return [[node_count]]
    elif group_count == 2:  # solving the pb for 2
        for i in range(1, int(node_count / 2 + 1)):
            res.append([i, node_count - i])
        return res
    else:
        for i in range(1, node_count - group_count + 1):
            for j in generate_problem_combinaisons(node_count - i, group_count - 1):
                res.append([i] + j)
        return res


def powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


class Tree:
    def __init__(self, parent=None, node=("root",), distance=lambda x: len(x), substrate=None):
        self.node = node
        self.children = []
        self.parent = parent
        self.score = None
        self.d = distance
        self.best_leaf = None
        self.substrate = substrate
        assert self.substrate is not None

    def has_ancester(self, node):
        if self.parent is not None:

            if node in self.node:
                return True
            else:
                return self.parent.has_ancester(node)

        return False

    def compute_best_leaf(self,substrate):

        for c in self.children:
            c.compute_best_leaf(substrate)

        if self.parent is not None:
            my_best_children = self.score if self.score is not None else 0
            my_value = self.d(self.node,substrate)
            if self.parent.score is None or my_best_children + my_value < self.parent.score:
                self.parent.score = my_value + my_best_children
                self.parent.best_leaf = [self.node, ]
                if self.best_leaf is not None:
                    for i in self.best_leaf:
                        self.parent.best_leaf.append(i)


class AncesterError(Exception):
    pass


cache = {}


def do_dist(bunch, substrate):
    if bunch in cache:
        return cache[bunch]
    else:
        asum = 0

        for i in [x for x in [x.split(" ") for x in set([" ".join(sorted(i)) for i in product(bunch, bunch)])] if x[0] != x[1]]:

            value = shortest_path_cached(str(i[0]), str(i[1]), substrate)

            if value is not None:
                asum += value
            else:
                print()
                "failure: %s" % str(i)

        return asum


def build_exhaustive_tree(data, settings, tree,substrate):
    '''

    :param data: {1: [("a","b","c"], 2: [("a","b")]}
    :param settings: [1,2,2]
    :param tree:
    :return:
    '''
    if len(settings) == 0:
        return

    for j in data[settings[0]]:
        try:
            for k in j:
                if tree.has_ancester(k):
                    raise AncesterError()
            subtree = Tree(node=j, parent=tree, distance=tree.d,substrate=substrate)
            tree.children.append(subtree)
            build_exhaustive_tree(data, settings[1:], subtree,substrate)

        except AncesterError:
            continue



def shortest_path_cached(node1, node2, substrate):
    if (node1, node2) not in cache:
        mutex.acquire()
        try:
            cache[(node1, node2)] = substrate.compute_delay(substrate.shortest_path(node1, node2))
        finally:
            mutex.release()

    res = cache[(node1, node2)]

    return res


def get_vhg_cdn_mapping(vhgs, cdns, substrate):
    '''

    :param vhgs: [ ("1025",'vhg1'), ("1026",'vhg2')]
    :param cdns: [ ("1025",'cdn1'), ("1026",'cdn3')]
    :return: [ "vhg1":"cdn3"]
    '''
    # logging.debug("managing %d vhgs and %d cdns" % (len(vhgs), len(cdns)))
    res = {}
    for vhg in vhgs:
        best = sys.maxsize
        for cdn in cdns:
            value = shortest_path_cached(vhg[0], cdn[0], substrate)
            if value is not None:
                # logging.debug("from %s to %s we have %lf" % (vhg[1], cdn[1], value))
                if value < best:
                    best = value
                    res[vhg[1]] = cdn[1]
    # print res
    return res


def get_node_clusters(nodes, class_count, substrate):
    '''
    split the provided nodes into class according to proximity on the graph
    :param nodes: a list of nodes from the graph
    :param class_count: the the number of class
    :param substrate: the substrate on which to perform the computation
    :return: a dict with where keys are nodes and values are their respective class
    '''
    # logging.debug("get_node_clusters %s %d" % (nodes, class_count))

    nodes = sorted(nodes)

    data = defaultdict(list)
    for i in powerset(nodes):
        if len(i) > 0:
            data[len(i)].append(i)

    combinaisons = [[int(x) for x in x.split(" ")] for x in
                    set([" ".join([str(x) for x in (sorted(x))]) for x in
                         generate_problem_combinaisons(len(nodes), class_count)])]

    min_score = sys.maxsize
    candidate = None

    for i in combinaisons:
        tree = Tree(distance=do_dist,substrate=substrate)
        build_exhaustive_tree(data, i, tree,substrate)
        tree.compute_best_leaf(substrate)
        if tree.score < min_score:
            min_score = tree.score
            candidate = tree.best_leaf

    i = 1
    res = {}
    if candidate is not None:
        for x in candidate:
            for y in x:
                res[y] = i

            i += 1

    return min_score , res
