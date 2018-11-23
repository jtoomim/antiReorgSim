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
        return "[%6s: parent=%6s, time=%6.0f, height=%3i, diff=%1.2f, PoW=%5.1f]" % (
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
    for chaintip, opponent in ((a, b), (b,a)):
        blk = chaintip
        while blk.pow < opponent.pow:
            blk = Block(blk, opponent.firstseen, tag='-TBD')
        chainpenalty = 1.
        blocks = []
        while blk != root:
            blocks.append(blk)
            blk = blk.parent
        for blk in reversed(blocks):
            ts = time_to_beat(a if chaintip == b else b, blk.pow)
            delay = max(0, blk.firstseen - ts)
            penalty = delay / tc
            chainpenalty += penalty / (blk.height - root.height)**.5
            if debug>2: print "    Block %6s increased chain penalty by %4.2f to %5.2f from %4.0f sec delay" % (
                str(blk), penalty, chainpenalty, delay)
        score = (chaintip.pow - root.pow) / chainpenalty
        if debug>1: print "Overall for %s: score=%f, pow=%f, penalty=%f\n" % (
            str(chaintip), score, chaintip.pow - root.pow, chainpenalty)
        if bestchain == None or score > bestchain[0]:
            bestchain = [score, chaintip]
    return bestchain[1]

if __name__ == "__main__":
    root = Block(None, 0, '')
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
    del chain_b[0]
    
    # print "Chain A:"
    # for block in chain_a: print `block`
    # print "\nChain B:"
    # for block in chain_b: print `block`

    print "Chain A:\t\t\tChain B:"
    for h in range(max(chain_a[-1].height, chain_b[-1].height)):
        a, b = None, None
        for blk in chain_a:
            if blk.height == h:
                a = blk
                break
        for blk in chain_b:
            if blk.height == h:
                b = blk
                break
        print `a` if a else " "*70, `b` if b else ""



    #for block in chain_a: print `block`
    #print "\nChain B:"
    #for block in chain_b: print `block`


    print "\nPenalty and score calculations:"

    swinner = compare_blocks_simple_pow(chain_a[-1], chain_b[-1])
    ttwinner = compare_blocks_toomim_time(chain_a[-1], chain_b[-1])

    print "\ncompare_blocks_simple_pow winner: ", `swinner`
    print "compare_blocks_toomim_time winner:", `ttwinner`
