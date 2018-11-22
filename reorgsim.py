#!/usr/bin/python
import random

debug=3


class Block:
    def __init__(self, parent, firstseen, tag=''):
        self.parent = parent
        self.firstseen = firstseen
        self.height = parent.height + 1 if parent else 0
        self.difficulty = 1. # not yet implemented
        self.pow = parent.pow + self.difficulty if parent else self.difficulty
        self.name = str(self.height) + tag

    def __str__(self):
        return self.name

    def __repr__(self):
        return "%s: p=%s, fs=%f, h=%i, d=%f, pow=%f" % (
            self.name, str(self.parent), self.firstseen, self.height, self.difficulty, 
            self.pow)

def find_shared_ancestor(a, b):
    known = set()
    while a.parent or b.parent:
        if a.parent: 
            a = a.parent
            if a in known: return a
            known.add(a)
        if b.parent:
            b = b.parent
            if b in known: return b
            known.add(b)
    return None

def compare_blocks_simple_pow(a, b):
    return a if a.pow > b.pow else b

def time_to_beat(enemytip, pow):
    while enemytip.parent and pow < enemytip.parent.pow:
        enemytip = enemytip.parent
    if not enemytip.parent:
        print "huh, couldn't find an equivalent PoW block"
        raise
    interp = (pow - enemytip.parent.pow) / (enemytip.pow - enemytip.parent.pow)
    return enemytip.parent.firstseen + interp * (enemytip.firstseen - enemytip.parent.firstseen)

def compare_blocks_toomim_time(a, b, tc=600.):
    root = find_shared_ancestor(a, b)
    if root == None: # this ain't no fork
        if debug: print "Hey, you're forkless!"
        return compare_blocks_simple_pow(a, b)
    bestchain = None
    for chaintip in [a, b]:
        blk = chaintip
        chainpenalty = 1.
        while blk != root:
            ts = time_to_beat(a if chaintip == b else b, blk.pow)
            delay = max(0, blk.firstseen - ts)
            penalty = delay / tc
            chainpenalty += penalty / (blk.height - root.height)**.5
            if debug>2: print "    Block %s increased chain penalty by %f to %f from %f sec delay" % (
                str(blk), penalty, chainpenalty, delay)
            blk = blk.parent
        score = (chaintip.pow - root.pow) / chainpenalty
        if debug>1: print "Overall for %s: score=%f, pow=%f, penalty=%f" % (
            str(chaintip), score, chaintip.pow - root.pow, chainpenalty)
        if bestchain == None or score > bestchain[0]:
            bestchain = [score, chaintip]
    return bestchain[1]

if __name__ == "__main__":
    root = Block(None, 0, '-genesis')
    chain_a = [root]
    t = 0
    for i in range(random.randint(5, 20)):
        t += random.random() * 600
        chain_a.append(Block(chain_a[-1], t, tag="-A"))
    
    tgt =random.randint(0, len(chain_a)-1)
    chain_b = [chain_a[tgt]]
    t = chain_b[-1].firstseen
    for i in range(random.randint(5, 20)):
        t += random.random() * 600
        chain_b.append(Block(chain_b[-1], t, tag="-B"))
    
    print "\nchain_a:"
    for block in chain_a: print `block`
    print "\nchain_b:"
    for block in chain_b: print `block`


    print "\ntarget: ", tgt
    print find_shared_ancestor(chain_a[-1], chain_b[-1])

    swinner = compare_blocks_simple_pow(chain_a[-1], chain_b[-1])
    ttwinner = compare_blocks_toomim_time(chain_a[-1], chain_b[-1])

    print "\ncompare_blocks_simple_pow winner: ", `swinner`
    print "compare_blocks_toomim_time winner:", `ttwinner`
