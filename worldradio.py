
from pyradios import RadioBrowser
import pandas as pd
import plotly.graph_objects as go
import requests
import dash
from dash import html, dcc, callback, Input, Output, Dash
from dash.exceptions import PreventUpdate

# styles 
teal = '#5f9ea0'
stickyFooter =  { 'bottom': '0', 'width': '100%'}
stationInfo  =  {
                'margin':'auto', 'width': '50%', 'text-align':'center',   # this centers the station info
                'font-family':'monospace', 'font-size':20, 'font-weight':'bold', 'color':teal # font color/size
                }
centerText=  { 'margin': 'auto', 'width': '50%', 'text-align':'center', 'padding': '1%'}


app = Dash(__name__, use_pages=True, pages_folder='')
app.title = 'Elsewhere Radio'
app._favicon = ("icons8-radio-emoji-32.png")
server = app.server
rb = RadioBrowser()



# put all the countries from the radio api into a dataframe
countries = rb.countries()
stations = {}
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



def layout(country="", station_id=0):
    return html.Div([
    dcc.Graph(
        id='basic-interactions',
        figure=f,

    ),
    html.Div([
        dcc.Input(type='hidden', id='station-num', value=station_id),
        dcc.Input(type='hidden', id='country-code', value=country),
        dcc.Location(id='share-url', refresh='callback-nav'),
        html.Div([html.Audio(id='playing', autoPlay=True, controls=True)], style=centerText),
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



# page design
dash.register_page("home", layout=layout, path="/")
app.layout = html.Div(dash.page_container)

cache = {}
# play station when country is clicked
@app.callback(
    Output("loading-output-2", "children"),
    Output('basic-interactions', 'clickData'),
    Output('playing', 'src'),
    Output('share-url', 'search'),
    Input('basic-interactions', 'clickData'),
    Input('share-url', 'search'),
    Input('country-code', 'value'),
    Input('station-num', 'value'))
def play_station(clickData, search, countrycode, station):
    
    if search == "" and clickData == None: # landing page
        raise PreventUpdate
    
    i = int(station)
        

    if clickData != None: 
        i += 1 # if we clicked, we should increment the url

        # find country clicked
        clicked = clickData['points'][0]
        clickedCountry = clicked['customdata']

        # start from station 0 if we switched countries
        if clickedCountry != countrycode:
            i = 0
        
        countrycode = clickedCountry

    # this call is expensive so just do it the first time
    if countrycode not in cache:
        countryStations = rb.stations_by_countrycode(countrycode)
        numStations = len(countryStations)
        cache[countrycode] = [countryStations, numStations]
        
    else:
        countryStations = cache[countrycode][0]
        numStations = cache[countrycode][1]

    # don't allow switching if there is only one station (prevents radio cutting out)
    if i == 0 and numStations == 1:
        raise PreventUpdate

    status_code = 0
    fail = -1
    while status_code != 200:

        fail += 1
        if fail == numStations:
            no_stations = "This country has no working stations right now :("
            return ["", no_stations], None, i, countrycode, ""
 
        i = i % numStations
    
        # pull station url
        station = countryStations[i]
        url = station['url']
        
        # skip station
        if "abdulbasit" in  station['name'].lower():
            i += 1
            continue
        try:
            r = requests.get(url, stream=True)
            status_code = r.status_code
        except:
            i += 1
            continue

        # redirect if necessary
        if status_code == 302:
            url = r.headers['Location']
            r = requests.get(url, stream=True)
            status_code = r.status_code

        
        if status_code == 200: # request is good we still get bad streams
            r = requests.get(url, stream=True)
            for line in r.iter_content(1): # pull the first chunk to test
                content = line
                break
            if  b'\xff' not in content: # this is the start of a good stream?
                # just fail if the stream isnt returning anything good
                status_code = 0
                i += 1
                continue
            break
        i += 1

    # save info of station playing to display on bottom
    countryName = station['country']
    stationName = station['name']

    display_info = "{} {}".format(countryName, stationName)
    display_info_2 =  "{} of {}".format(i+1, numStations)
    share_url =  '?country={}&station_id={}'.format(countrycode, i)
    # reset clickData so we can click same button twice
    return ["", display_info, html.Br(), display_info_2], None, url, share_url

