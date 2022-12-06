
from pyradios import RadioBrowser
from requests_cache import CachedSession
from datetime import timedelta
import pandas as pd
import plotly.graph_objects as go
import requests
from dash import Dash, dcc, html, Input, Output
from dash.exceptions import PreventUpdate

# styles 
teal = '#5f9ea0'
stickyFooter =  { 'position': 'fixed', 'bottom': '0', 'width': '100%'}
stationInfo  =  {
                'margin':'auto', 'width': '50%', 'text-align':'center',   # this centers the station info
                'font-family':'monospace', 'font-size':20, 'font-weight':'bold', 'color':teal # font color/size
                }
centerText=  { 'margin': 'auto', 'width': '50%', 'text-align':'center', 'padding': '1%'}



app = Dash(__name__)
app.title = 'Elsewhere Radio'
app._favicon = ("icons8-radio-emoji-32.png")
server = app.server
rb = RadioBrowser()


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
        html.Audio(id='playing', autoPlay=True), 
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
                    html.Div(id="loading-output-1"), 
                    ], style=stationInfo
                ),
            ]
        ),
        html.P(['Listen to internet radio stations from around the world.'], 
        style=centerText),
        html.P(['Radio stations may take up to 5 seconds to start playing. After 5 seconds, click the country again to try a different station. Some countries may not have any working stations.'], 
        style=centerText),
        html.Footer( 
            html.A(
                children = [    
                    html.P(
                        ['elsewhere radio is an open source application'], 
                        style=centerText
                    )],
                href="https://github.com/katyaslepoy1/worldradio"
            ),
            style=stickyFooter
        )
   ])
])

# play station when country is clicked
@app.callback(
    Output("loading-output-2", "children"),
    Output('basic-interactions', 'clickData'),
    Output('station-num', 'value'), 
    Output('country-code', 'value'),
    Output('playing', 'src'),
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
    #    print(numStations)

        # don't allow switching if there is only one station (prevents radio cutting out)
        if i == 0 and numStations == 1:
            raise PreventUpdate

        status_code = 0
        while status_code != 200:
            i = (i + 1) % numStations
     
            # pull station url
            station = thisCountriesStations[i]
            url = station['url']
            
            # skip azul pop because it sucks
            if "azul" in  station['name'].lower():
                continue
            try:
                r = requests.head(url)
            except:
                continue
            status_code = r.status_code
            if status_code == 200: # request is good we still get bad streams
                r = requests.get(url, stream=True)
                for line in r.iter_content(64): # pull the first chunk to test
                    content = line
                    break
                print(content)
                if  b'\xff' not in content: # this is the start of a good stream?
                    # just fail if the stream isnt returning anything good
                    status_code = 0
                    continue
        # save info of station playing to display on bottom
        countryName = station['country']
        stationName = station['name']

        display_info = "{} {}".format(countryName, stationName)
        display_info_2 =  "{} of {}".format(i+1, numStations)
        # reset clickData so we can click same button twice
        return ["", display_info, html.Br(), display_info_2], None, i, countrycode, url

    # do nothing
    raise PreventUpdate

