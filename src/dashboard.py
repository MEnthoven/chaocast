import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import xarray as xr
import pandas as pd
import logging
import warnings
from pathlib import Path
import dash_leaflet as dl
import plotly.express as px
import pandas as pd
import seaborn as sns
import numpy as np
import os
import plotly.graph_objects as go
import matplotlib.dates as mdates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore', message='All-NaN slice encountered')


# Initialize the Dash app
app = dash.Dash(__name__)

# Default coordinates for Utrecht
UTRECHT_LAT = 52.0907
UTRECHT_LON = 5.1214

# Get the path from environment variable, raise error if not set
NETCDF_PATH = os.getenv('NETCDF_PATH', None)
if NETCDF_PATH is None:
    raise RuntimeError("Environment variable NETCDF_PATH must be set to the path of the netCDF file.")

GLOBAL_DS = None
def load_initial_data():    
    try:
        logger.info("Attempting to load netCDF file...")
        if NETCDF_PATH is None:
            raise ValueError("NETCDF_PATH is None. Cannot load dataset.")
        ds = xr.open_dataset(NETCDF_PATH)
        logger.info("Successfully loaded netCDF file")
        return ds
    except Exception as e:
        logger.error(f"Error loading netCDF file: {e}")
        return None

GLOBAL_DS = load_initial_data()

  
def compute_rolling_difference(df, variable='prec'):
    return df.groupby(['run_number'])[variable].diff()



# Function to get weather data for specific coordinates
def get_location_data(ds, lat, lon):
    logger.info(f"Getting data for coordinates: lat={lat}, lon={lon}")
    if ds is None:
        logger.warning("Dataset is None, returning empty DataFrames")
        return pd.DataFrame(), pd.DataFrame()
    
    # Select nearest point to given coordinates
    location_data = ds.sortby('run_number').sel(lat=lat, lon=lon,method='nearest').to_dataframe()
    location_data['prec_diff'] = compute_rolling_difference(location_data, 'prec')
    logger.info("Successfully retrieved location data")   
    
    return location_data


def create_map():
    return dl.Map([
        dl.TileLayer()
    ],
        center=[UTRECHT_LAT, UTRECHT_LON],
        zoom=8,
        minZoom=8,
        id='map',
        style={'height': '50vh'},
        maxBounds=[[50.75, 3.2], [53.7, 7.22]],  # Netherlands bounds
        maxBoundsViscosity=1,  # Prevents bouncing at edges    
        # clickData={'lat': UTRECHT_LAT, 'lon': UTRECHT_LON}
    )

app.layout = html.Div([
    # Leaflet map component
    create_map(),
    
    # Store clicked location data (lat, lon)
    dcc.Store(id='clicked-location'),  
    
    # Graph for temperature data
    dcc.Graph(id='temperature-graph'),
    
    # Graph for precipitation data
    dcc.Graph(id='precipitation-graph')
], style={'padding': '20px'})  # Added padding of 20px around all content

# Callback to capture click location and store it
@app.callback(
    Output('clicked-location', 'data'),  # Store clicked location
    Input('map', 'n_clicks'),  # Triggered when the map is clicked
    State('map', 'clickData')  # Capture the click data
    , prevent_initial_call=True
)
def store_click_location(n_clicks, clickData):
    if clickData:
        # Extract latitude and longitude from the click data
        lat = clickData['latlng']['lat']
        lon = clickData['latlng']['lng']
        return {'lat': lat, 'lon': lon}
    return None

def create_percentile_plot(data_series, ylabel ='', title='Time Series Percentile Distribution'):
    """
    Create a percentile plot from a time series data.
    
    Parameters:
    -----------
    data_series : pandas.Series
        Time series data to plot, should be unstacked with time index and multiple columns
    title : str
        Title for the plot (default: 'Time Series Percentile Distribution')
        
    Returns:
    --------
    plotly.graph_objects.Figure
        The created figure object
    """
    # Calculate percentiles    
    percentiles = np.nanpercentile(data_series, q=[5, 25, 50, 75, 95], axis=1)
    time_steps = data_series.index

    name = title
    line_color= 'blue'

    # Calculate percentiles
    p5 = percentiles[0]
    p25 = percentiles[1]
    p50 = percentiles[2]
    p75 = percentiles[3]
    p95 = percentiles[4]  
    
    # Create figure
    fig = go.Figure()

    t = np.concatenate([time_steps, time_steps[::-1]])
    
    # Add 5-95 percentile band (most transparent)
    fig.add_trace(go.Scatter(
        x=t,
        y=np.concatenate([p95, p5[::-1]]),
        fill='toself',
        fillcolor=line_color,
        line=dict(color='rgba(255,255,255,0)'),
        opacity=0.2,
        name=f'{name} (90% chance, 9/10 members, 5-95th percentile)',
        showlegend=True
    ))
    
    # Add 25-75 percentile band (medium transparent)
    fig.add_trace(go.Scatter(
        x=t,
        y=np.concatenate([p75, p25[::-1]]),
        fill='toself',
        fillcolor=line_color,
        line=dict(color='rgba(255,255,255,0)'),
        opacity=0.4,
        name=f'{name} (50% chance, 5/10 members, 25-75th percentile)',
        showlegend=True
    ))
    
    # Add median line
    fig.add_trace(go.Scatter(
        x=time_steps,
        y=p50,
        line=dict(color=line_color, width=2),
        mode='lines+markers',
        name=f'{name} (median)',
        showlegend=True
    ))
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title='',
        yaxis_title=ylabel,
        hovermode='x unified',
        template='plotly_white'
    )
    
    
    return fig

# Callback to update graphs based on clicked location
@app.callback(
    [Output('temperature-graph', 'figure'),
     Output('precipitation-graph', 'figure')],
    Input('clicked-location', 'data')  # Triggered when the clicked-location is updated
)

def update_graphs(location):
    if location is None:
        return go.Figure(), go.Figure()  # Return empty figures if no location clicked    
    
    # Dummy data for the temperature and precipitation graphs
    # In a real-world scenario, you would query an API or use real data based on lat/lon
    
    # Load data once at startup
    lat, lon = location['lat'], location['lon']   
    
    
    location_data = get_location_data(GLOBAL_DS, lat, lon)    

    # Temperature graph
    data_temp= location_data['temp'].unstack('run_number') # type: ignore
    temperature_figure = create_percentile_plot(data_temp, ylabel = 'Tempearture [Celcius]', title=f'Temperature Forecast')
    y_values = location_data['temp']
    y_min = np.floor(y_values.min() / 10) * 10
    y_max = np.ceil(y_values.max()/ 10) * 10
    temperature_figure.update_layout(yaxis_range=[y_min, y_max])
    
    # Precipitation graph
    data_temp = location_data['prec_diff'].unstack('run_number')
    precipitation_figure = create_percentile_plot(data_temp, ylabel='Precipitation [mm]', title='Precipitation Forecast')
    y_max = data_temp.max().max()
    if y_max < 2.5:
        y_limit = 2.5
        label = "Light"
    elif y_max < 7.5:
        y_limit = 7.5
        label = "Moderate"
    elif y_max < 50:
        y_limit = 50
        label = "Heavy"
    else:
        y_limit = np.ceil(y_max)
        label = "Extreme"

    precipitation_figure.update_layout(
        yaxis_range=[0, y_limit],
        annotations=[
            dict(x=0.02, y=2.5, text="Light", showarrow=False, xref="paper", yref="y"),
            dict(x=0.02, y=7.5, text="Moderate", showarrow=False, xref="paper", yref="y"),
            dict(x=0.02, y=50, text="Heavy", showarrow=False, xref="paper", yref="y")
        ]
    )

    return temperature_figure, precipitation_figure



# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)