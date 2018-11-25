#!/usr/bin/pypy
import random, traceback, platform, sys
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input, State
from math import *
import cPickle as pickle

from reorgsim import *

sys.setrecursionlimit(100000)

params = {'attacker_rate':2.,        # attacker hashrate, where 1.0 is 100% of the pre-fork hashrate
          'defender_rate':1.,         # defender hashrate
          'attacker_delay':60*60.,     # seconds that the attacker waits before publishing their chain
          'duration':50*3600.,         # seconds before the attacker gives up if they're not ahead
          'finalize':0,               # allow finalization after this many blocks (0 to disable)
          'exp':1.9,                  # exponent for decaying contributions of later blocks to the penalty factor
          'tc':120.}                  # time constant for penalizing blocks. A delay of tc on the first block gives a penalty of +1 (2x)

debug=3

seed = 123456 #random.randint(0, 2**32-2) # you can also set this to a specific integer for repeatability
print "Seed = %i" % seed

class Nothing:
    pass

if __name__ == "__main__":

    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

    def run_round(params, seed):
        df = Nothing()
        random.seed(seed)
        df.result = reorgattack(**params)
        df.root = find_shared_ancestor(df.result[5], df.result[4])
        df.att_pow = []
        df.att_ts = []
        df.att_chainpenalty = []
        df.att_score = []
        df.att_hypochainpenalty = []
        df.att_hyposcore = []
        blk = df.result[4]
        while blk != None:
            df.att_pow.append(blk.pow)
            df.att_ts.append(blk.firstseen/3600.)
            if not hasattr(blk, 'chainpenalty'):
                blk.chainpenalty = 1.
            df.att_chainpenalty.append(blk.chainpenalty)
            df.att_score.append((blk.pow - df.root.pow if df.root else 0.) / blk.chainpenalty)
            df.att_hyposcore.append(0. if not hasattr(blk, 'hyposcore') else blk.hyposcore)
            df.att_hypochainpenalty.append(0. if not hasattr(blk, 'hypochainpenalty') else blk.hypochainpenalty)
            blk = blk.parent

        df.def_pow = []
        df.def_ts = []
        df.def_chainpenalty = []
        df.def_score = []
        df.def_hypochainpenalty = []
        df.def_hyposcore = []
        df.def_hypots =[]
        blk = df.result[5]
        while blk != None:
            df.def_pow.append(blk.pow)
            df.def_ts.append(blk.firstseen/3600.)
            if not hasattr(blk, 'chainpenalty'):
                blk.chainpenalty = 1.
            df.def_chainpenalty.append(blk.chainpenalty)
            df.def_score.append((blk.pow - df.root.pow if df.root else 0.) / blk.chainpenalty)
            if hasattr(blk, 'hyposcore'):
                df.def_hyposcore.append(blk.hyposcore)
                df.def_hypochainpenalty.append(blk.hypochainpenalty)
                df.def_hypots.append(blk.firstseen/3600.)
            blk = blk.parent
        return df

    df = run_round(params, seed)

    app.layout = html.Div(children=[
        html.H1(children="\"Toomim time\" time-first-seen penalization rule simulation"),

        html.Div(children=(dcc.Input(id='Seed', value=seed, type="number", name="Randomness seed"), "Randomness seed")),
        html.Div(children=(dcc.Input(id='attacker_rate', value=params['attacker_rate'], type="number", step=0.05, min=0.25, required=True), "Attacker hashrate")),
        html.Div(children=(dcc.Input(id='defender_rate', value=params['defender_rate'], type="number", step=0.05, min=0.25, required=True), "Defender hashrate")),
        html.Div(children=(dcc.Input(id='attacker_delay', value=params['attacker_delay']/60., type="number", step=1, min=0, required=True), "Delay before reveal of hidden mining blocks (minutes)")),
        html.Div(children=(dcc.Input(id='duration', value=params['duration']/3600., type="number", step=1, min=0, required=True), "Time before attacker gives up (hours)")),
        html.Div(children=(dcc.Input(id='finalize', value=params['finalize'], type="number", step=1, min=0, required=True), "Finalize blocks at this depth if defender chain score is 2x attacker's (0 to disable)")),
        html.Div(children=(dcc.Input(id='tc', value=params['tc'], type="number", step=1, min=0, required=True), "Time constant for punishment (e.g. if the first block is delayed by this amount, it adds a penalty of 1)")),
        html.Div(children=(dcc.Input(id='exp', value=params['exp'], type="number", step=.05, min=0.5, required=True), "Exponent")),
        #html.Div(id='testingcallbacks'),
        html.Div(id='winner'), 
        html.Div(id='results_of_run', style={'display':'none'}),
        dcc.Graph(
            id='pow-graph',
            figure={}
        ),
        dcc.Graph(
            id='score-graph',
            figure={}
        ),
        dcc.Graph(
            id='penalty-graph',
            figure={},
        ),        
    ])

    @app.callback(
        Output(component_id='results_of_run', component_property='children'),
        [Input(component_id='attacker_rate', component_property='value'),
         Input(component_id='defender_rate', component_property='value'),
         Input(component_id='attacker_delay', component_property='value'),
         Input(component_id='duration', component_property='value'),
         Input(component_id='finalize', component_property='value'),
         Input(component_id='tc', component_property='value'),
         Input(component_id='exp', component_property='value'),
         Input(component_id='Seed', component_property='value'),
         ])
    def update_results_of_run(attacker_rate, defender_rate, attacker_delay, duration, finalize, tc, exp, seed):
        params = {
          'attacker_rate':float(attacker_rate),        # attacker hashrate, where 1.0 is 100% of the pre-fork hashrate
          'defender_rate':float(defender_rate),         # defender hashrate
          'attacker_delay':attacker_delay*60.,     # seconds that the attacker waits before publishing their chain
          'duration':duration*3600.,         # seconds before the attacker gives up if they're not ahead
          'finalize':finalize,               # allow finalization after this many blocks (0 to disable)
          'exp':float(exp),                  # exponent for decaying contributions of later blocks to the penalty factor
          'tc':float(tc)
          }
        return pickle.dumps(run_round(params, seed))

    @app.callback(Output(component_id='score-graph', component_property='figure'),
                  [Input(component_id='results_of_run', component_property='children')])
    def update_score_graph(pickled_results):
        df = pickle.loads(pickled_results)
        return {'data': [
                    {'x': df.att_ts, 'y': df.att_score, 'mode': 'lines+markers', 'name': 'Attacker', 'line':{'color':'red'}},
                    {'x': df.def_ts, 'y': df.def_score, 'mode': 'lines+markers', 'name': 'Defender', 'line':{'color':'blue'}},
                    {'x': df.def_hypots, 'y': df.def_hyposcore, 'mode': 'lines+markers', 'name': 'Defender hypothetical', 'line':{'color':'aqua'}}],
               'layout': {'title': "Score", 'xaxis': {'title':'Hours since fork'}, 'yaxis': {'title':"Chain score"}}}
    @app.callback(Output(component_id='pow-graph', component_property='figure'),
                  [Input(component_id='results_of_run', component_property='children')])
    def update_pow_graph(pickled_results):
        df = pickle.loads(pickled_results)
        return {'data': [
                    {'x': df.att_ts, 'y': df.att_pow, 'mode': 'lines+markers', 'name': 'Attacker', 'line':{'color':'red'}},
                    {'x': df.def_ts, 'y': df.def_pow, 'mode': 'lines+markers', 'name': 'Defender', 'line':{'color':'blue'}}],
               'layout': {'title': "Chain PoW", 'xaxis': {'title':'Hours since fork'}, 'yaxis': {'title':"PoW"}}}
    @app.callback(Output(component_id='penalty-graph', component_property='figure'),
                  [Input(component_id='results_of_run', component_property='children')])
    def update_penalty_graph(pickled_results):
        df = pickle.loads(pickled_results)
        return {'data': [
                    {'x': df.att_ts, 'y': df.att_chainpenalty, 'mode': 'lines+markers', 'name': 'Attacker', 'line':{'color':'red'}},
                    {'x': df.def_ts, 'y': df.def_chainpenalty, 'mode': 'lines+markers', 'name': 'Defender', 'line':{'color':'blue'}},
                    {'x': df.def_hypots, 'y': df.def_hypochainpenalty, 'mode': 'lines', 'name': 'Defender hypothetical', 'line':{'color':'aqua'}}],
               'layout': {'title': "Chain penalty", 'xaxis': {'title':'Hours since fork'}, 'yaxis': {'title':"Penalty factor"}}}
    @app.callback(Output(component_id='winner', component_property='children'),
                  [Input(component_id='results_of_run', component_property='children')])
    def update_winner(pickled_results):
        df = pickle.loads(pickled_results)
        return "Defender won" if df.result[0] else "Attacker won"

    app.run_server(debug=True, host='0.0.0.0')