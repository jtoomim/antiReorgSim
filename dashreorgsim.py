#!/usr/bin/pypy
import random, traceback, platform
import dash
import dash_core_components as dcc
import dash_html_components as html
from math import *

from reorgsim import *

params = {'attacker_rate':1.5,        # attacker hashrate, where 1.0 is 100% of the pre-fork hashrate
          'defender_rate':1.,         # defender hashrate
          'attacker_delay':20*60.,     # seconds that the attacker waits before publishing their chain
          'duration':500*3600.,         # seconds before the attacker gives up if they're not ahead
          'finalize':0,               # allow finalization after this many blocks (0 to disable)
          'exp':1.9,                  # exponent for decaying contributions of later blocks to the penalty factor
          'tc':120.}                  # time constant for penalizing blocks. A delay of tc on the first block gives a penalty of +1 (2x)

debug=3

seed = 5#random.randint(0, 2**32-2) # you can also set this to a specific integer for repeatability
print "Seed = %i" % seed

if __name__ == "__main__":

    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

    random.seed(seed)
    result = reorgattack(**params)
    root = find_shared_ancestor(result[5], result[4])
    att_pow = []
    att_ts = []
    att_chainpenalty = []
    att_score = []
    att_hypochainpenalty = []
    att_hyposcore = []
    blk = result[4]
    while blk != None:
        att_pow.append(blk.pow)
        att_ts.append(blk.firstseen/3600.)
        if not hasattr(blk, 'chainpenalty'):
            blk.chainpenalty = 1.
        att_chainpenalty.append(blk.chainpenalty)
        att_score.append((blk.pow - root.pow) / blk.chainpenalty)
        att_hyposcore.append(0. if not hasattr(blk, 'hyposcore') else blk.hyposcore)
        att_hypochainpenalty.append(0. if not hasattr(blk, 'hypochainpenalty') else blk.hypochainpenalty)
        blk = blk.parent
    att_pow.reverse()
    att_ts.reverse()
    att_chainpenalty.reverse()
    att_score.reverse()
    att_hypochainpenalty.reverse()
    att_hyposcore.reverse()

    def_pow = []
    def_ts = []
    def_chainpenalty = []
    def_score = []
    def_hypochainpenalty = []
    def_hyposcore = []
    blk = result[5]
    while blk != None:
        def_pow.append(blk.pow)
        def_ts.append(blk.firstseen/3600.)
        if not hasattr(blk, 'chainpenalty'):
            blk.chainpenalty = 1.
        def_chainpenalty.append(blk.chainpenalty)
        def_score.append((blk.pow - root.pow) / blk.chainpenalty)
        def_hyposcore.append(0. if not hasattr(blk, 'hyposcore') else blk.hyposcore)
        def_hypochainpenalty.append(0. if not hasattr(blk, 'hypochainpenalty') else blk.hypochainpenalty)
        blk = blk.parent
    def_pow.reverse()
    def_ts.reverse()
    def_chainpenalty.reverse()
    def_score.reverse()
    def_hypochainpenalty.reverse()
    def_hyposcore.reverse()


    app.layout = html.Div(children=[
        html.H1(children="jtoomim's time-first-seen rule simulation"),

        html.Div(children="Defender won the sample round above\n" if result[0] else "Attacker won the sample round above\n"),
        html.Div(children="Parameters: att_hashrate = %(attacker_rate)3.2f, def_hashrate = %(defender_rate)3.2f, attacker_delay = %(attacker_delay)4.0f, attack_endurance = %(duration)5.0f, maxreorgdepth = %(finalize)i" % params),

        html.Div(children=("Randomness seed: ", dcc.Input(id='Seed', value=seed, type="number", name="Randomness seed"))),
        html.Div(children=("att_hashrate:", dcc.Input(id='attacker_rate', value=params['attacker_rate'], type="number", step=0.05, min=0, required=True),
                           " def_hashrate:", dcc.Input(id='defender_rate', value=params['defender_rate'], type="number", step=0.05, min=0, required=True),
                           " att_delay (min):", dcc.Input(id='attacker_delay', value=params['attacker_delay']/60., type="number", step=1, min=0, required=True),
                           " duration (hr):", dcc.Input(id='duration', value=params['duration']/3600., type="number", step=1, min=0, required=True),
            )),
        html.Div(id='testingcallbacks'),
        dcc.Graph(
            id='Score',
            figure={
                'data': [
                    {'x': att_ts, 'y': att_score, 'type': 'markers', 'name': 'Attacker', 'line':{'color':'red'}},
                    {'x': def_ts, 'y': def_score, 'type': 'markers', 'name': 'Defender', 'line':{'color':'blue'}},
                    {'x': def_ts, 'y': def_hyposcore, 'type': 'markers', 'name': 'Defender hypothetical', 'line':{'color':'aqua'}},
                ],
                'layout': {
                    'title': "Score",
                    'xaxis': {
                        'title':'Hours since fork'
                    }
                }
            }
        ),
        dcc.Graph(
            id='PoW',
            figure={
                'data': [
                    {'x': att_ts, 'y': att_pow, 'type': 'markers', 'name': 'Attacker PoW', 'line':{'color':'red'}},
                    {'x': def_ts, 'y': def_pow, 'type': 'markers', 'name': 'Defender PoW', 'line':{'color':'blue'}},
                ],
                'layout': {
                    'title': "Chain PoW since fork",
                    'xaxis': {
                        'title':'Hours since fork'
                    }
                }
            }
        ),
        dcc.Graph(
            id='Penalty',
            figure={
                'data': [
                    {'x': att_ts, 'y': att_chainpenalty, 'type': 'markers', 'name': 'Attacker', 'line':{'color':'red'}},
                    {'x': def_ts, 'y': def_chainpenalty, 'type': 'markers', 'name': 'Defender', 'line':{'color':'blue'}},
                    {'x': def_ts, 'y': def_hypochainpenalty, 'type': 'markers', 'name': 'Defender hypothetical', 'line':{'color':'aqua'}},
                ],
                'layout': {
                    #'title': "Hidden reorg attack sim (%2.0f min delay, %2.0f%% attacker hashrate)" % (params['attacker_delay']/60, 100.*params['attacker_rate'] / (params['attacker_rate'] + params['defender_rate'])),
                    'title': "Chain penalty",
                    'xaxis': {
                        'title':'Hours since fork'
                    }
                }
            }
        ),        
    ])

    @app.callback(
        dash.dependencies.Output(component_id='testingcallbacks', component_property='children'),
        [dash.dependencies.Input(component_id='attacker_rate', component_property='value'),
         dash.dependencies.Input(component_id='Seed', component_property='value')])
    def update_testingcallbacks(attacker_rate, seed):
        return "Values entered were attacker_rate=%f, seed=%i" % (attacker_rate, seed)
    app.run_server(debug=True, host='0.0.0.0')