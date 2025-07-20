# About this app
This application offers an  approach to visualizing weather forecast uncertainty. Instead of a single, definitive forecast, it presents the spectrum of possible weather outcomes, empowering users to make more informed decisions.

## Overview
The app's interactive visualizations of meteorological uncertainty are achieved by analyzing the full 36-member ensemble data from the KNMI HARMONIE Cy43 model. To accomplish this, the app utilizes (among other tools):
- Xarray, netCDF4, and pygrib: These are for efficiently reading and handling complex, multi-dimensional weather data.
- Dash and Dash-Leaflet: These build the interactive web isualizations of meteorological uncertainty.
  
Currently, the app focuses on visualizing uncertainty for temperature and precipitation, but its flexible architecture allows for easy extension to include other relevant meteorological variables. The core objective is to help you explore and comprehend the diverse range of potential weather scenarios for specific locations.

Visit the [KNMI](https://www.knmidata.nl/open-data/harmonie#:~:text=KNMI%20gebruikt%20en%20mede-ontwikkelt,hoge%20resolutie%20op%20korte%20afstanden.) site for more information on ensemble forecasts.


<figure>
<img src="image.png" alt="alt text" width="500"/>
  <figcaption>Temperature and Precipitaition Percentile Confidence Interval plot. Light blue: 90% confidence, 9/10 members. Dark blue = 50% confidence, 5/10 members. Dotted line: Median Forecast.</figcaption>
</figure>




## Getting Started
### Setup
1. **Clone the repository:**
   ```
   git clone https://github.com/menthoven/chaocast.git
   cd chaocast
   ```

2. **Get an API KEY**
    - See [here](https://developer.dataplatform.knmi.nl/open-data-api) for the KNMI developer portal to get an API key
    

2. **Set up environment variables:**
   - Create a `.env` file in the project root.
   - Add your API key:
     ```
     API_KEY=your_api_key_here
     ```

### Running with Docker
1. **Build the image and start the docker container**
   ```
   docker compose up --build
   ```

2. **Wait for approximately 20 minutes (depends on Internet speed) to finish downloading and preprocessing**
    - The app will download approximately 12GB of forecasts to the local `./data` folder
    - All files will be unpacked and preprocessed into a single NetCDF file. 

> [!WARNING] 
> Local testing showed that peak memory usage can exceed 18GB. Consider increasing Docker memory limits if you're running into issues.


3. **Access the dashboard:**
   - Open your browser and go to [http://localhost:8050](http://localhost:8050)
   - Click on any location on the map to visualize the uncertainty in weather forecasts.
