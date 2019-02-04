from flask import render_template, flash, redirect, url_for, request, send_file
from app import app, db
from app.forms import LoginForm, RegistrationForm, DateSelectForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from werkzeug.urls import url_parse
import pymysql
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import plotly
import plotly.graph_objs as go
import io
import base64
import json
from datetime import datetime, timedelta
from datetime import timezone
import time
import os

track_db = pymysql.connect('trackingdbinstance-1.ch4vficxrcmw.us-east-2.rds.amazonaws.com', 'DefenseDaily', 'htK5N6a8Bry4e49H', 'tracking')


def create_plot(start_date='', end_date=''):
    good_data_query = """SELECT DefenseDaily_TrackingData.`pixel.timestamp`, status, reason 
        FROM DefenseDaily_TrackingAdsFilter 
        join DefenseDaily_TrackingData ON pixel_id = DefenseDaily_TrackingData.id
        """
    cursor = track_db.cursor()
    cursor.execute(good_data_query)
    total_data_myresult = cursor.fetchall()

    timestamp = []
    status = []
    reason = []

    for num in range(0, len(total_data_myresult)):
        timestamp.append(total_data_myresult[num][0])
        status.append(total_data_myresult[num][1])
        reason.append(total_data_myresult[num][2])

    #print(len(total_data_myresult))

    data_dict = {
        'timestamp': timestamp,
        'status': status,
        'reason': reason}

    df = pd.DataFrame(data_dict)

    if start_date:
        start_day = datetime.strptime(start_date, '%m/%d/%Y')
        end_day = datetime.strptime(end_date, '%m/%d/%Y')
        end_day = end_day + timedelta(days=1)
        start_stamp = time.mktime(start_day.date().timetuple())
        end_stamp = time.mktime(end_day.date().timetuple())
        df_filtered = df[(df['timestamp'] >= start_stamp) & (df['timestamp'] < end_stamp)]
        df = df_filtered
        #print(df_filtered)

    df['date'] = pd.to_datetime(df['timestamp'], unit='s')

    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    #print(df)

    def displayed_count(x):
        if x['status'] == 'displayed':
            return 1
        else:
            return 0

    def blocked_count(df):
        if df['status'] == 'blocked':
            return 1
        else:
            return 0

    df['blocked_count'] = df.apply(lambda x: blocked_count(x), axis=1)

    df['displayed_count'] = df.apply(lambda x: displayed_count(x), axis=1)

    df_reasons = pd.pivot_table(df, index='reason', values=['blocked_count'], aggfunc=np.sum)
    df_reasons = df_reasons.sort_values(by='blocked_count', ascending=False)
    df_reasons.to_csv(os.path.join(app.root_path, 'temp/')+str(current_user.id)+'_first.csv')

    df_reasons.reset_index(level=0, inplace=True)

    # Reasons Chart
    #ax = df_reasons['blocked_count'].plot(kind='barh', title='Blocked Reasons')
    data = [go.Bar(x=df_reasons['blocked_count'], y=df_reasons['reason'], orientation='h', marker={'color': df_reasons['blocked_count'],
                                                                                                   'colorscale': 'Jet'})]
    graphJSON1 = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    table1 = pd.DataFrame(df_reasons).to_html(classes=['table', 'is-hoverable', 'is-fullwidth', 'is-striped'], border=0)

    # Pivot Chart / Graph
    df_pivot = pd.pivot_table(df, index='date', values=['displayed_count', 'blocked_count'], aggfunc=np.sum)
    df_pivot['total_visits'] = df_pivot['blocked_count'] + df_pivot['displayed_count']
    df_pivot['percent_blocked_from_ads'] = df_pivot['blocked_count'] / df_pivot['total_visits']
    df_pivot.to_csv(os.path.join(app.root_path, 'temp/') + str(current_user.id) + '_second.csv')

    df_pivot.reset_index(level=0, inplace=True)
    trace1 = go.Bar(x=df_pivot['date'], y=df_pivot['displayed_count'], name='Visitors With Ads',
                    marker=dict(
                        color='rgba(55, 128, 191, 0.7)',
                        line=dict(
                            color='rgba(55, 128, 191, 1.0)',
                            width=2,
                        )
                    )),
    trace2 = go.Bar(x=df_pivot['date'], y=df_pivot['blocked_count'], name='Bots / Blocked Ads',
                    marker=dict(
                        color='rgba(219, 64, 82, 0.7)',
                        line=dict(
                            color='rgba(219,64,82,1.0)',
                            width=2,
                        )
                    )),
    graphJson2 = []
    trace1_dump = json.dumps(trace1, cls=plotly.utils.PlotlyJSONEncoder)
    trace2_dump = json.dumps(trace2, cls=plotly.utils.PlotlyJSONEncoder)
    graphJson2.append(json.loads(trace1_dump)[0])
    graphJson2.append(json.loads(trace2_dump)[0])
    table2 = pd.DataFrame(df_pivot).to_html(classes=['table', 'is-hoverable', 'is-fullwidth', 'is-striped'], border=0)

    graphJSON = [graphJSON1, graphJson2, table1, table2]

    return graphJSON, start_date, end_date


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
@login_required
def index():
    #today_stamp = time.mktime(datetime.utcnow().date().timetuple())
    #sql = "SELECT * FROM DefenseDaily_TrackingAdsFilter WHERE `pixel.timestamp` > {}".format(today_stamp)
    #df = pd.read_sql_query(sql, track_db)

    #cursor = track_db.cursor()
    #cursor.execute(sql)
    #results = cursor.fetchall()
    #print(cursor.description)

    #df1 = df
    #df['count'] = 1
    #df1['pixel.timestamp'] = df1['pixel.timestamp'].apply(lambda x: pd.datetime.utcfromtimestamp(x).strftime('%Y-%m-%d %H'))
    #display_df = df1.drop(['pixel_id', 'reason'], axis=1)
    #display_df = display_df.pivot(index='pixel.timestamp', columns='status')

    #print(df1['pixel.timestamp'].unique())
    #print(display_df)
    #print(df1.dtypes)
    #for result in results:
    #    print(result)
        #print(datetime.utcfromtimestamp(int(result[1])).strftime('%Y-%m-%d %H'))
    #print(len(results))
    form = DateSelectForm()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date:
        start_obj = datetime.strptime(start_date, '%m/%d/%Y')
        end_obj = datetime.strptime(end_date, '%m/%d/%Y')
        if start_obj >= end_obj:
            flash('Invalid date range')
            return redirect(url_for('index'))
    graphs, start_date, end_date = create_plot(start_date, end_date)
    return render_template('index.html', title='Home Page', graphs=graphs, form=form, start_date=start_date, end_date=end_date)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/download/blocked-reason')
def download_blocked():
    file_name = os.path.join(os.path.join(app.root_path, 'temp/')+str(current_user.id)+'_first.csv')
    return send_file(file_name, attachment_filename='blocked-reason.csv', mimetype='text/csv', as_attachment=True)


@app.route('/download/visit-block-ads')
def download_visit():
    file_name = os.path.join(os.path.join(app.root_path, 'temp/')+str(current_user.id)+'_second.csv')
    return send_file(file_name, attachment_filename='visit-block-ads.csv', mimetype='text/csv', as_attachment=True)

