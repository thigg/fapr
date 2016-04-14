#!/usr/bin/env python


# Arguments: arg1 num_cpus to use

import sys
import itertools
from multiprocessing import Pool
import datetime

# Import pygraph
from pygraph.classes.digraph import digraph
from pygraph.algorithms import cycles as cycl
from pygraph.algorithms import searching as gsearch

import multiprocessing


# Graph creation

network_size = 3
dirs = {-3: "d", -2: "s", -1: "w", 0: "l", 1: "e", 2: "n", 3: "u"}

def test_reachability(tm):
    """
    Tests a turnmodel if all nodes are reachable from every node
    The idea is, that either a turn or it's opposite have to exists
    Example: NE or EN
    is not covering all turnmodels which are fully connected via non minimal paths

    """
    for a in all_turns:
        b, c = a
        if (b, c) in tm or (c, b) in tm:
            continue
        else:
            return False
    return True


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
    """
    builds a string for a port
    :param dir: cardinal direction, one of neswudl
    :param x: x
    :param y: y
    :param z: z
    :param pdir: in or out
    :return: a string representing this
    """
    return dir + str(x) + "." + str(y) + "." + str(z) + pdir



def buildNetwork(network_size, turnmodel):
    """
    applies the turnmodel to the whole network size
    :param network_size:
    :param turnmodel:
    :return: a 3d array containing the tm in every field
    """
    return [[[turnmodel for _ in range(0, network_size)] for _ in range(0, network_size)] for _ in
            range(0, network_size)]


lock = multiprocessing.Lock()

# checks if the specified turnmodel is cyclefree
#
def checkTurnmodelForCycles(network_size, network, tm):
    """
    checks the given network represented by a 3d array of turnmodel for cycles, returns the nr of cycles
    todo: remove the tm reference and print in testtm
    """
   # if not test_reachability(tm):
   #     return None
    gr = digraph()

    # create basic graph with inter node connections and cons to and from local
    for x in range(0, network_size):
        for y in range(0, network_size):
            for z in range(0, network_size):
                for dir in 0, -3, -2, -1, 1, 2, 3:  # we have to do 0 first
                    # build in and out nodes for this port
                    gr.add_node(node(dirs[dir], x, y, z, "in"))
                    gr.add_node(node(dirs[dir], x, y, z, "out"))
                    # connect to local
                    if dir != 0:# reverse local labeling here local out is the output from the processing element
                        gr.add_edge((node(dirs[dir], x, y, z, "in"), node("l", x, y, z, "in")))
                        gr.add_edge((node("l", x, y, z, "out"), node(dirs[dir], x, y, z, "out")))

                # create inter node connections
                # connect to nodes which are in negative direction
                for d in range(-3, -0):
                    coord = [x, y, z]
                    # calculate opposite node for my current dir
                    coord[-d - 1] -= 1  # decrement the coord in this direction if d= -1 we have to go -1 in west dir
                    if coord[-d - 1] < 0:
                        continue  # break this loop if the router does not exist
                    if (coord == [x, y, z]):
                        print '#wtf'
                    gr.add_edge((node(dirs[d], x, y, z, "out"), node(dirs[-d], coord[0], coord[1], coord[2], "in")))
                    gr.add_edge((node(dirs[-d], coord[0], coord[1], coord[2], "out"), node(dirs[d], x, y, z, "in")))


                # apply turnmodel to this node
                for turn in network[x][y][z]:
                    if (turn[0] == turn[1]):  # uturns shouldnt be allowed
                        print '#wtf'
                    gr.add_edge((node(dirs[turn[0]], x, y, z, "in"), node(dirs[turn[1]], x, y, z, "out")))

    # ...is fully connected
    if not check_connectivity_with_graphsearch(gr):
        return None
    # ... and has no cycles
    res = len(cycl.find_cycle(gr))
    if res != 0:
        return None
    return (res, tm)



def check_connectivity_with_graphsearch(gr):
    """
    checks if the local nodes in the graph are fully connected
    :param gr: the graph to check
    :return: true if the local nodes are fully connected, false if not
    """
    # check connectivity
    for x in range(0, network_size):
        for y in range(0, network_size):
            for z in range(0, network_size):
                dic, trash = gsearch.breadth_first_search(gr, root=node("l", x, y, z, "out"))
                for x1 in range(0, network_size):
                    for y1 in range(0, network_size):
                        for z1 in range(0, network_size):
                            if  x != x1 and y != y1 and z != z1:
                                if not node("l", x1, y1, z1, "in") in dic:
                                    return False
    return True




def testtm(tm):
    """
    Tests the given turnmodel
    :param tm: the turnmodel
    :return: a tuple of cycle length and the turnmodel, so if first element is 0 it is cycle free and interesting
    """
    # now build a network from it and add the straight turns before to the tm
    if (len(tm) > 10):  # require at least 12 turns
        turns = set(tm).union(set(turnmodel))
        return checkTurnmodelForCycles(network_size, buildNetwork(network_size, turns), tm)
    else:
        return None


if __name__ == "__main__":

    if len(sys.argv) > 1:
        num_cores = int(sys.argv[1])
    else:
        num_cores = multiprocessing.cpu_count()

    print 'started @ ' + str(datetime.datetime.now()) + " used cpus: " + str(num_cores)

    # Build all_turns
    turnmodel = []
    # basic turnmodel: straight connections
    for i in range(-3, 4):
        if i != 0:
            turnmodel.append((i, -i))  # straight

    oports = [-3, -2, -1, 1, 2, 3]  # all non local dirs

    all_turns = itertools.product(oports, oports)  # all possible turns
    all_turns = list(
        set(all_turns).difference(set(turnmodel)).difference(zip(oports, oports)))  #remove straights and u-turns

    nrmodelsperturnnr = [0 for x in range(25)]


    pool = Pool(processes=num_cores)  # use all available CPUs

    #run now in parallel with a chunksize of 1000
    for result in pool.imap_unordered(testtm, powerset(all_turns), chunksize=1000):
        if result != None:
            print(len(result[1]), (result))  # print the found turnmodels
            nrmodelsperturnnr[len(result[1])] += 1
        else:
            print "None"

    akku  = 0
    for i, a in enumerate(nrmodelsperturnnr):
        print( (i, a))
        akku += a

    print 'finished @ ' + str(datetime.datetime.now()) + " with " + str(akku) +" turnmodels found."




