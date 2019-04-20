# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 17:43:39 2019

@author: Stephen Day
"""

import statistics
from collections import OrderedDict

import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import pandas as pd
from dash.dependencies import Input, Output, State

import utils

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

pkdata = pd.DataFrame({'subject_index': [0, 0, 0, 0, 0, 0, 0, 0,
                                         1, 1, 1, 1, 1, 1, 1, 1,
                                         2, 2, 2, 2, 2, 2, 2, 2],
                       'time': [5, 15, 30, 60, 120, 240, 360, 480,
                                5, 15, 30, 60, 120, 240, 360, 480,
                                5, 15, 30, 60, 120, 240, 360, 480],
                       'conc': [1, 3, 5, 4, 2, 1, .5, 0.25,
                                1, 3.2, 5.1, 4.1, 2.0, 1, .55, 0.3,
                                1, 3.2, 5.1, 4.1, 2.4, 1, .55, 0.3]
                       })

n_subjects = len(pkdata.subject_index.unique())
n_times = len(pkdata.time.unique())

app.layout = html.Div(className='container', children=[
    html.H1(children='Noncompartmental Pharmacokinetics Analysis'),

    html.Div(children=[

        html.Div([
            'Time Points:',
            dcc.Input(
                id='times-input',
                placeholder='Enter a value...',
                type='number',
                value=n_times,
                debounce=True,
                style={'margin': 10, 'width': 50}
            ),
            'Subjects:',

            dcc.Input(
                id='subjects-input',
                placeholder='Enter a value...',
                type='number',
                value=n_subjects,
                debounce=True,
                style={'margin': 10, 'width': 50}
            ),
        ]),

        html.Div(children=[
            dash_table.DataTable(
                id='data-table',
                columns=[{"name": 'Time (min)', "id": 'time', 'type': 'numeric'}] +
                        [{"name": 'Conc{} (uM)'.format(subject), 'id': subject, 'type': 'numeric'}
                         for subject in pkdata.subject_index.unique()],
                data=utils.pkdata2dt(pkdata),
                editable=True,
                content_style='fit'
            )
        ]),

        html.Div(children=[
            dcc.Graph(
                id='results-graph',

            )
        ]),

        html.Div(children=[
            dash_table.DataTable(
                id='results-table',
                style_data_conditional=[{
                    'if': {'column_id': 'param'},
                    'fontFamily': 'times',
                }],
                content_style='fit',
                style_cell={'padding-left': 20}
            )
        ]),
    ])
])


@app.callback(
    [Output('data-table', 'columns'),
     Output('data-table', 'data')],
    [Input('subjects-input', 'value'),
     Input('times-input', 'value')],
    [State('data-table', 'data')])
def update_data_table(subjects, rows, records):
    columns = [{"name": 'Time (min)', "id": 'time', 'type': 'numeric'}] + \
              [{"name": 'Subj{} Conc (uM)'.format(subject + 1), 'id': subject, 'type': 'numeric'}
               for subject in range(subjects)]

    change = rows - len(records)
    if change > 0:
        for i in range(change):
            records.append({c['id']: '' for c in columns})
    elif change < 0:
        records = records[:rows]

    for record in records:
        current_subjects = len(record) - 1
        for x in range(subjects, current_subjects):
            record.pop(str(x))

    return columns, records


@app.callback([Output('results-graph', 'figure'),
               Output('results-table', 'columns'),
               Output('results-table', 'data')],
              [Input('data-table', 'data')])
def update_output(records):
    pkd = utils.dt2pkdata(records)
    fig_data = []
    results = {}

    for subject in pkd.subject_index.unique():
        df = pkd.loc[pkd.subject_index == subject, ['time', 'conc']]
        fig_data.append(
            go.Scatter(
                x=df['time'],
                y=df['conc'],
                name='Subj{}'.format(subject + 1),
                mode='lines+markers'
            )
        )

        results[subject] = utils.calc_pk(df['time'],
                                         df['conc'])

    figure = go.Figure(

        data=fig_data,

        layout=go.Layout(
            xaxis=dict(title='Time (min)'),
            yaxis=dict(title='Conc (uM)',
                       type='log',
                       rangemode='tozero')
        )
    )

    columns = [{"name": "Parameter", "id": 'param'}] + \
              [{"name": 'Subj{}'.format(subject + 1), 'id': subject, 'type': 'numeric'}
               for subject in pkd.subject_index.unique()] + \
              [{'name': 'Mean', 'id': 'mean'}, {'name': 'StDev', 'id': 'stdev'}]

    result_names = OrderedDict(t_half='T½ (min)', auc0_t='AUC_0-t (uM*min)', auc0_inf='AUC_0-inf (uM*min)',
                               percent_extrap='%Extrap', c_max='Cmax (uM)', t_max='Tmax (min)')

    data = []
    for key, name in result_names.items():
        d = dict(param=name)
        for subject in pkd.subject_index.unique():
            d[int(subject)] = round(getattr(results[subject], key), 1)

        d['mean'] = round(statistics.mean([getattr(results[s], key) for s in pkd.subject_index.unique()]), 1)
        d['stdev'] = round(statistics.stdev([getattr(results[s], key) for s in pkd.subject_index.unique()]), 2)

        data.append(d)

    return figure, columns, data


if __name__ == '__main__':
    app.run_server(debug=True)
