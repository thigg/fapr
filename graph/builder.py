#!/usr/bin/env python

# Copyright (c) 2007-2008 Pedro Matiello <pmatiello@gmail.com>
# License: MIT (see COPYING file)

# Import graphviz
import sys
import itertools
sys.path.append('..')

# Import pygraph
from pygraph.classes.digraph import digraph
from pygraph.algorithms import cycles as cycl
from sets import Set
from joblib import Parallel, delayed
import multiprocessing

# Graph creation

network_size = 6


def powerset(seq):
    """
    Returns all the subsets of this set. This is a generator.
    """
    if len(seq) <= 1:
        yield seq
        yield []
    else:
        for item in powerset(seq[1:]):
            yield [seq[0]] + item
            yield item


def node(dir, x, y, z, pdir):
    return dir + str(x) + "." + str(y) + "." + str(z) + pdir

# print node("a",1,2,3,"in")
# Add nodes and edges
dirs = {-3: "d", -2: "s", -1: "w", 0: "l", 1: "e", 2: "n", 3: "u"}

# turnmodel.extend([(1, -2), (-2, -1), (-1, 2), (2, 1)])
#print turnmodel


def buildNetwork(network_size, turnmodel):
    return [[[turnmodel for _ in range(0, network_size)] for _ in range(0, network_size)] for _ in
           range(0, network_size)]



def checkTurnmodelForCycles(network_size, network):
    "checks the given network represented by a 3d array of turnmodel for cycles, returns the nr of cycles"
    gr = digraph()
    # create basic graph with inter node connections and cons to and from local
    for x in range(0, network_size):
        for y in range(0, network_size):
            for z in range(0, network_size):
                for dir in 0, -3, -2, -1, 1, 2, 3:  #we have to do 0 first
                    # build in and out nodes for this port
                    gr.add_node(node(dirs[dir], x, y, z, "in"))
                    gr.add_node(node(dirs[dir], x, y, z, "out"))
                    # connect to local
                    if dir != 0:
                        gr.add_edge((node(dirs[dir], x, y, z, "in"), node("l", x, y, z, "in")))
                        gr.add_edge((node("l", x, y, z, "out"), node(dirs[dir], x, y, z, "out")))

                # create inter node connections
                # connect to nodes which are in negative direction
                for d in range(-3, -0):
                    coord = [x, y, z]
                    # calculate opposite node for my current dir
                    coord[-d - 1] -= 1  #decrement the coord in this direction if d= -1 we have to go -1 in west dir
                    if coord[-d - 1] < 0: continue  #break this loop if the router does not exist
                    gr.add_edge((node(dirs[d], x, y, z, "out"), node(dirs[-d], coord[0], coord[1], coord[2], "in")))
                    gr.add_edge((node(dirs[-d], coord[0], coord[1], coord[2], "out"), node(dirs[d], x, y, z, "in")))

                # apply turnmodel to this node
                for turn in network[x][y][z]:
                    gr.add_edge((node(dirs[turn[0]], x, y, z, "in"), node(dirs[turn[1]], x, y, z, "out")))

    return len(cycl.find_cycle(gr))


turnmodel = []
# basic turnmodel: straight connections
for i in range(-3, 4):
    if i != 0:
        turnmodel.append((i, -i))  # straight

all_turns = itertools.product([-3, -2, -1, 1, 2, 3], [-3, -2, -1, 1, 2, 3])  # all possible turns
all_turns = list(Set(all_turns).difference(Set(turnmodel)))

num_cores = multiprocessing.cpu_count()


def testtm(tm):
    # now build a network from it and add the straight turns before to the tm
    turns = Set(tm).union(Set(turnmodel))
    result = (checkTurnmodelForCycles(network_size, buildNetwork(network_size, turns)), tm)
    print result

# the powerset are all possible turns
Parallel(n_jobs=num_cores)(delayed(testtm)(tm) for tm in powerset(all_turns))
