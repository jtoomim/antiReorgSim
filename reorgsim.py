#!/usr/bin/pypy
import random, traceback, platform
from math import *

params = {'attacker_rate':1.5,        # attacker hashrate, where 1.0 is 100% of the pre-fork hashrate
          'defender_rate':1.,         # defender hashrate
          'attacker_delay':1200.,     # seconds that the attacker waits before publishing their chain
          'duration':60000.,          # seconds before the attacker gives up if they're not ahead
          'finalize':10}              # allow finalization after this many blocks (0 to disable)

debug=3

seed = random.randint(0, 2**32-1) # you can also set this to a specific integer for repeatability
print "Seed = %i" % seed
random.seed(seed)




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

def time_to_beat(enemytip, pow, mytime):
    if enemytip.pow < pow:
        return mytime
    while enemytip.parent and pow < enemytip.parent.pow:
        enemytip = enemytip.parent
    if not enemytip.parent:
        print "huh, couldn't find an equivalent PoW block"
        raise

    interp = (pow - enemytip.parent.pow) / (enemytip.pow - enemytip.parent.pow)
    return enemytip.parent.firstseen + interp * (enemytip.firstseen - enemytip.parent.firstseen)

def compare_blocks_toomim_time(a, b, tc=120., finalize=False, debug=debug):
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
            if not hasattr(blk, 'penalty'): # small optimization because python is slow
                ts = time_to_beat(a if chaintip == b else b, blk.pow, blk.firstseen)
                pseudoheight = (blk.pow - root.pow) / root.difficulty
                blk.delay = max(0, blk.firstseen - ts)
                blk.penalty = (blk.delay / tc) / (pseudoheight)**2
                blk.chainpenalty = blk.parent.chainpenalty + blk.penalty if hasattr(blk.parent, 'chainpenalty') else 1.+blk.penalty
            chainpenalty += blk.penalty
            if debug>2: print "    Block %6s increased chain penalty by %4.2f to %5.2f from %4.0f sec delay" % (
                str(blk), blk.penalty, chainpenalty, blk.delay)
        score = (chaintip.pow - root.pow) / chainpenalty
        if debug>1: print "Overall for %s: score=%f, pow=%f, penalty=%f, chaintip.chainpenalty=%f\n" % (
            str(chaintip), score, chaintip.pow - root.pow, chainpenalty, chaintip.chainpenalty)

        if bestchain and finalize:
            winscore = max(score, bestchain[0])
            losescore = min(score, bestchain[0])
            winner = chaintip if score == winscore else bestchain[1]
            loser = chaintip if score == losescore else bestchain[1]
            return winscore / losescore > 2 and winner.height - root.height > finalize

        if bestchain == None or score > bestchain[0]:
            bestchain = [score, chaintip]
    return bestchain[1]

def print_chains(chain_a, chain_b, labels=("Chain A", "Chain B")):
    print labels[0] + " "*65 + labels[1]
    for h in range(1+max(chain_a[-1].height, chain_b[-1].height)):
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

def randomcomparison():
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

    print_chains(chain_a, chain_b)
    
    print "\nPenalty and score calculations:"

    swinner = compare_blocks_simple_pow(chain_a[-1], chain_b[-1])
    ttwinner = compare_blocks_toomim_time(chain_a[-1], chain_b[-1])

    print "\ncompare_blocks_simple_pow winner: ", `swinner`
    print "compare_blocks_toomim_time winner:", `ttwinner`

def reorgattack(attacker_rate, defender_rate, attacker_delay, duration, finalize=10, debug=debug):
    root = Block(None, 0, '')
    chain_att = [root]
    chain_def = [root]
    finalized = 0
    t=0.
    while t < attacker_delay:
        t += random.expovariate(1) * 600. / (attacker_rate + defender_rate)
        if random.random() < attacker_rate / (attacker_rate + defender_rate):
            chain_att.append(Block(chain_att[-1], attacker_delay, tag='-A'))
        else:
            chain_def.append(Block(chain_def[-1], t, tag='-D'))

    while compare_blocks_toomim_time(chain_def[-1], chain_att[-1], debug=0) == chain_def[-1] and t < duration and not finalized:
        t += random.expovariate(1) * 600. / (attacker_rate + defender_rate)
        if random.random() < attacker_rate / (attacker_rate + defender_rate):
            chain_att.append(Block(chain_att[-1], t, tag='-A'))
        else:
            chain_def.append(Block(chain_def[-1], t, tag='-D'))
        if finalize > 0 and compare_blocks_toomim_time(chain_def[-1], chain_att[-1], finalize=finalize, debug=0):
            finalized = 1

    if debug>1: print_chains(chain_def, chain_att, labels=("Defender", "Attacker"))
    return compare_blocks_toomim_time(chain_def[-1], chain_att[-1], debug=debug) == chain_def[-1], len(chain_att), len(chain_def), finalized


if __name__ == "__main__":
    print "Defender won the sample round above\n" if reorgattack(**params)[0] else "Attacker won the sample round above\n"

    if platform.python_implementation() == 'PyPy':
        rounds = 10000
    else:
        rounds = 100
        print "Note: PyPy is strongly recommended for running this code. Falling back to 100 rounds for performance."
    print "Parameters: att_hashrate = %(attacker_rate)3.2f, def_hashrate = %(defender_rate)3.2f, attacker_delay = %(attacker_delay)4.0f, attack_endurance = %(duration)5.0f, maxreorgdepth = %(finalize)i" % params
    results = [reorgattack(debug=0, **params) for i in range(rounds)]
    wins = [1 if res[0] else 0 for res in results]
    att_blocks = [res[1] for res in results]
    def_blocks = [res[2] for res in results]
    total_blocks = [res[1] + res[2] for res in results]
    def_losses = [res[2] if not res[0] else 0 for res in results]
    att_losses = [res[1] if res[0] else 0 for res in results]
    net_blocks = [(res[1] - res[2]) *  (-1 if res[0] else 1) for res in results]
    def_finals = [res[3] for res in results if res[0]]
    att_finals = [res[3] for res in results if not res[0]]
    print "Defender won %i of %i rounds" % (sum(wins), len(wins))
    print "Defender orphan rate:   %3.1f%%" % (100.* sum(def_losses) / sum(def_blocks))
    print "Attacker orphan rate:   %3.1f%%" % (100.* sum(att_losses) / sum(att_blocks))
    print "Defender finalizations: %3.1f%%" % (100.* sum(def_finals) / len(results))
    print "Attacker finalizations: %3.1f%%" % (100.* sum(att_finals) / len(results))

    print sum(total_blocks), sum(att_blocks), sum(def_blocks), sum(def_losses), sum(att_losses), sum(net_blocks)

    reorgs = [(i, len([1 for res in results if res[2]==i and not res[0]])) for i in range(20)]
    print "\nReorg_size\tProbability"
    for org in reorgs: print "%i       \t%3.1f%%" % (org[0], 100.*org[1]/len(results))

    print "Chance of >=10 block reorg: %3.1f%%" % (100.* sum(org[1] for org in reorgs[10:])/len(results))
