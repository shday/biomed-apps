# -*- coding: utf-8 -*-

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

table_header_style = {
    'backgroundColor': 'rgb(2,21,70)',
    'color': 'white',
    'textAlign': 'center'
}

app = dash.Dash(__name__)

pkdata = pd.DataFrame({'subject_index': [0, 0, 0, 0, 0, 0, 0, 0,
                                         1, 1, 1, 1, 1, 1, 1, 1,
                                         2, 2, 2, 2, 2, 2, 2, 2],
                       'time': [0.0833, 0.25, 0.5, 1, 2, 4, 6, 8,
                                0.0833, 0.25, 0.5, 1, 2, 4, 6, 8,
                                0.0833, 0.25, 0.5, 1, 2, 4, 6, 8, ],
                       'conc': [1.1, 3.04, 4.85, 3.93, 2.01, 1.02, .51, 0.25,
                                0.92, 2.8, 4.6, 4.1, 1.99, 1.05, .55, 0.3,
                                1.04, 3.23, 5.35, 4.1, 2.4, 1.12, .52, 0.27]
                       })

n_subjects = len(pkdata.subject_index.unique())
n_times = len(pkdata.time.unique())

app.layout = html.Div(className='', children=[
    html.Div(className='pkcalc-banner', children='Noncompartmental Pharmacokinetics Analysis'),
    html.Div(className='container', children=[
        html.Div(className='row', style={}, children=[

            html.Div(className='four columns pkcalc-settings', children=[
                html.P(['Study Design']),
                html.Div([
                    html.Label([html.Div(['Time points']),
                                dcc.Input(
                                    id='times-input',
                                    placeholder='Enter a value...',
                                    type='number',
                                    value=n_times,
                                    # debounce=True,
                                    min=3,
                                    max=999
                                )]),
                    html.Label([html.Div(['Subjects']),

                                dcc.Input(
                                    id='subjects-input',
                                    placeholder='Enter a value...',
                                    type='number',
                                    value=n_subjects,
                                    # debounce=True,
                                    min=1,
                                    max=48
                                )]),
                ]),
            ]),
            html.Div(className='eight columns pkcalc-data-table', children=[
                dash_table.DataTable(
                    id='data-table',
                    columns=[{"name": 'Time (hr)', "id": 'time', 'type': 'numeric'}] +
                            [{"name": 'Conc{} (uM)'.format(subject), 'id': subject, 'type': 'numeric'}
                             for subject in pkdata.subject_index.unique()],
                    data=utils.pkdata2dt(pkdata),
                    editable=True,
                    style_header=table_header_style,
                    active_cell=[0, 0],
                    selected_cells=[[0, 0]]
                )
            ])

        ]),
        html.Div(className='row', children=[
            html.Div(className='six columns', children=[
                dcc.Graph(
                    id='results-graph',

                )
            ]),

            html.Div(className='six columns pkcalc-results-table', children=[
                dash_table.DataTable(
                    id='results-table',
                    style_header=table_header_style,
                    style_cell_conditional=[
                        {
                            'if': {'column_id': 'param'},
                            'textAlign': 'right',
                            'paddingRight': 10
                        },
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'white'
                        }
                    ],
                )
            ]),
        ])
    ])
])


@app.callback(
    [Output('data-table', 'columns'),
     Output('data-table', 'data'),
     ],
    [Input('subjects-input', 'value'),
     Input('times-input', 'value')],
    [State('data-table', 'data'),
     ])
def update_data_table(subjects, rows, records):
    columns = [{"name": 'Time (hr)', "id": 'time', 'type': 'numeric'}] + \
              [{"name": 'Subj{} Conc (uM)'.format(subject + 1), 'id': subject, 'type': 'numeric'}
               for subject in range(subjects)]

    #   adjust number of rows
    change = rows - len(records)
    if change > 0:
        for i in range(change):
            records.append({c['id']: '' for c in columns})
    elif change < 0:
        records = records[:rows]

    #   delete column data if needed
    valid_column_ids = ['time'] + [str(x) for x in range(subjects)]
    for record in records:
        invalid_column_ids = set(record.keys()) - set(valid_column_ids)
        for col_id in invalid_column_ids:
            record.pop(col_id)

    return columns, records


@app.callback([Output('results-graph', 'figure'),
               Output('results-table', 'columns'),
               Output('results-table', 'data')],
              [Input('data-table', 'data')])
def update_output(records):
    pkd = utils.dt2pkdata(records)

    if not pkd.empty:
        subjects = pkd.subject_index.unique()
    else:
        subjects = []

    fig_data = []
    results = {}
    for subject in subjects:
        df = pkd.loc[pkd.subject_index == subject, ['time', 'conc']]
        fig_data.append(
            go.Scatter(
                x=df['time'],
                y=df['conc'],
                name='Subj{}'.format(subject + 1),
                mode='lines+markers'
            )
        )
        results[subject] = utils.calc_pk(df['time'], df['conc'])

    figure = go.Figure(
        data=fig_data,
        layout=go.Layout(
            xaxis=dict(zeroline=False),
            yaxis=dict(title=dict(text='Conc (uM)',
                                  font=dict(
                                      family='"Open Sans", "HelveticaNeue", "Helvetica Neue",'
                                             ' Helvetica, Arial, sans-serif',
                                      size=12)
                                  ),
                       type='log',
                       rangemode='tozero',
                       zeroline=False,
                       showticklabels=False
                       ),
            margin=dict(
                l=40,
                r=30,
                b=50,
                t=50,
            ),
            showlegend=False,
            height=294,
            paper_bgcolor='rgb(245, 247, 249)',
            plot_bgcolor='rgb(245, 247, 249)',
        )
    )

    columns = [{"name": "Parameter", "id": 'param'}] + \
              [{"name": 'Subj{}'.format(subject + 1), 'id': subject, 'type': 'numeric'}
               for subject in subjects] + \
              [{'name': 'Mean', 'id': 'mean'}, {'name': 'StDev', 'id': 'stdev'}]

    result_names = OrderedDict(t_half='T½ (hr)', auc0_t='AUC_0-t (uM*hr)', auc0_inf='AUC_0-inf (uM*hr)',
                               percent_extrap='%Extrap', c_max='Cmax (uM)', t_max='Tmax (hr)')

    data = []
    for key, name in result_names.items():
        d = dict(param=name)
        for subject in subjects:
            try:
                d[int(subject)] = round(getattr(results[subject], key), 1)
            except (AttributeError, TypeError):
                d[int(subject)] = None
        try:
            d['mean'] = round(statistics.mean([getattr(results[s], key) for s in subjects]), 1)
            d['stdev'] = round(statistics.stdev([getattr(results[s], key) for s in subjects]), 2)
        except (statistics.StatisticsError, AttributeError, TypeError):
            d['mean'] = None
            d['stdev'] = None
        data.append(d)

    return figure, columns, data


if __name__ == '__main__':
    app.run_server(debug=True)
