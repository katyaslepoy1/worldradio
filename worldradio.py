from pyradios import RadioBrowser
from requests_cache import CachedSession
from datetime import timedelta
import pandas as pd
from ipywidgets import Output, VBox
import plotly.express as px
import plotly.graph_objects as go
import vlc
import random
import time
from dash import Dash, dcc, html, Input, Output
from dash.exceptions import PreventUpdate

# todo
#  click on country makes pop up box with all the stations?
#  get rid of hover?
#  save favorites


app = Dash(__name__)

# cached radio browser session
expire_after = timedelta(days=3)
session = CachedSession(
    cache_name='cache',
    backend='sqlite',
    expire_after=expire_after)
rb = RadioBrowser(session=session)

# creating a vlc instance
vlc_instance = vlc.Instance()
player = vlc_instance.media_player_new()



# put all the countries from the radio api into a dataframe
countries = rb.countries()
df = pd.DataFrame(columns = ['countrycode', 'country'])
for country in countries:
    code = country["iso_3166_1"]
    countryName = country["name"]
    numStations = country["stationcount"]
    if numStations > 0:
        row = pd.DataFrame ( [[code, countryName]], columns = ['countrycode', 'country'])
        df = pd.concat([df, row])



# place one marker per country
f = go.FigureWidget()
f.add_scattergeo(
    False, 
    locationmode="country names",
    locations=df["country"], 
    mode="markers",
    customdata=df["countrycode"]
)

# display country lines
f.update_geos(showcountries=True)

# no margin on map
f.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# set color and size of dots
numCountries = len(df)
teal = '#5f9ea0'
scatter = f.data[0]
scatter.marker.color=[teal] * numCountries
scatter.marker.size=[10] * numCountries



# page design
app.layout = html.Div([
    dcc.Graph(
        id='basic-interactions',
        figure=f,

    ),
    html.Div([
        dcc.Input(type='hidden', id='station-num', value=-1),
        dcc.Input(type='hidden', id='country-code', value=""),
        dcc.Loading(
            id="loading-2",
            type="circle",
            color=teal,
            style={'margin':'auto'},
            children=[
                html.Div([
                    html.Div(id="loading-output-2"), 
                    html.P(id='station-info'),
                    html.P([html.Br()]),
                    html.P(id='station-number-info'),
                    ], style={
                       'margin':'auto', 'width': '50%', 'text-align':'center',   # this centers the station info
                       'font-family':'monospace', 'font-size':20, 'font-weight':'bold', 'color':teal # font color/size
                       }
                ),
            ]
        )
    ])
])


# play station when country is clicked
@app.callback(
    Output("loading-output-2", "children"),
    Output('basic-interactions', 'clickData'),
    Output('station-num', 'value'), 
    Output('country-code', 'value'), 
    Input('basic-interactions', 'clickData'),
    Input('station-num', 'value'),
    Input('country-code', 'value')) 
def play_station(clickData, i, previous_country_code):
    if clickData != None:

        # find country clicked
        clicked = clickData['points'][0]
        countrycode = clicked['customdata']

        # start from station 0 if we switched countries
        if countrycode != previous_country_code:
            i = -1

        # pull stations
        thisCountriesStations =  rb.stations_by_countrycode(countrycode)
        numStations = len(thisCountriesStations)

        # don't allow switching if there is only one station (prevents radio cutting out)
        if i == 0 and numStations == 1:
            raise PreventUpdate

        
        # stop any media already playing
        player.stop()

        # continue until success
        while player.is_playing() != 1:
            i = (i + 1) % numStations
            
            # pull station url
            station = thisCountriesStations[i]
            url = station['url']

            # start playing song
            media = vlc_instance.media_new(url) 
            player.set_media(media)
            player.play()
            time.sleep(1.7)

            # save info of station playing to display on bottom
            countryName = station['country']
            stationName = station['name']

        display_info = "{} {}".format(countryName, stationName)
        display_info_2 =  "{} of {}".format(i+1, numStations)
        # reset clickData so we can click same button twice
        return ["", display_info, html.Br(), display_info_2], None, i, countrycode

    # do nothing
    raise PreventUpdate
if __name__ == '__main__':
    app.run_server(debug=True)