# 3lips

Target localisation for multi-static radar using ellipse intersections. Not a dating app.

~~See a live instance at [http://3lips.30hours.dev](http://3lips.30hours.dev).~~

![3lips example display](./example.png "3lips")

## Features

- Provides a JSON API for geolocation of targets given [blah2](http://github.com/30hours/blah2) radar nodes.
- Uses a [CesiumJS](http://github.com/CesiumGS/cesium) web front-end to visualise data.
- Ability to compare a number of algorithms for target localisation.

## Usage

- Install docker and docker-compose on the host machine.
- Clone this repository to some directory.
- Create a `.env` file based on `.env.example` and configure your environment variables.
- Run the docker compose command.

```bash
sudo git clone http://github.com/30hours/3lips /opt/3lips
cp .env.example .env  # Create and edit your .env file
sudo docker compose up -d —build
```

### Testing

#### Unit Tests
```bash
# Run tests locally
cd 3lips
./run_tests.sh

# Run tests in container
docker exec -it 3lips-event python -m pytest test/
```

#### Integration Tests
The system includes comprehensive integration tests for RETINASolver functionality:

```bash
# Start full test environment with synthetic data
docker compose -f tests/docker-compose.retina.yml up -d

# Verify all services are running
./tests/verify-retina-services.sh

# Run integration tests using Claude Code with Puppeteer MCP
# Load and run: tests/retina-solver-test-suite.js
```

Test coverage includes:
- **UI Integration**: RETINASolver dropdown selection and form submission
- **Pipeline Integration**: Data flow from synthetic ADS-B through RETINASolver
- **End-to-End**: Complete aircraft tracking and visualization

~~The API front-end is available at [http://localhost:49156](http://localhost:49156).~~

### Environment Variables

The following environment variables can be configured:

#### Radar Configuration
- `RADAR_NAMES` - a comma separated list of identifiable radar names
- `RADAR_URLS` - a comma separated list of urls from which to poll data

#### Map Configuration
- `MAP_LATITUDE`, `MAP_LONGITUDE` - Center coordinates of the map
- `MAP_CENTER_WIDTH`, `MAP_CENTER_HEIGHT` - Map dimensions
- `TAR1090_URL` - URL for TAR1090 service

#### Localisation Configuration
- `ELLIPSE_N_SAMPLES`, `ELLIPSE_THRESHOLD`, `ELLIPSE_N_DISPLAY` - Ellipse sampling parameters
- `ELLIPSOID_N_SAMPLES`, `ELLIPSOID_THRESHOLD`, `ELLIPSOID_N_DISPLAY` - Ellipsoid sampling parameters
- `RETINA_SOLVER_MAX_ITERATIONS` - Maximum iterations for RETINASolver optimization (default: 100)
- `RETINA_SOLVER_CONVERGENCE_THRESHOLD` - Convergence threshold for optimization (default: 1e-6)
- `RETINA_SOLVER_PATH` - Path to RETINASolver module (default: /app/RETINAsolver)

#### ADSB Configuration
- `ADSB_T_DELETE` - Time to delete ADSB data

#### 3LIPS Configuration
- `THREE_LIPS_SAVE` - Whether to save data (true/false)
- `THREE_LIPS_T_DELETE` - Time to delete old data

## Method of Operation

The association uses the following algorithm:

- ADS-B associator will associate the closest target within some delay and Doppler around the truth.

The target localisation uses 1 of the following algorithms:

- **Ellipse parametric** samples an ellipse (2D) at 0 altitude. Find intersections between 3 or more ellipses such that the distance to each point is under some threshold.

- **Ellipsoid parametric** samples an ellipsoid (3D). Find intersections between 3 or more ellipsoids such that the distance to each point is under some threshold.

- **Spherical intersection** a closed form solution which applies when a common receiver or transmitter are used. As described in [Two Methods for Target Localization in Multistatic Passive Radar](https://ieeexplore.ieee.org/document/6129656).

- **RETINA Solver** uses Levenberg-Marquardt optimization for TDOA/FDOA localization. This advanced algorithm:
  - Generates intelligent initial position guesses based on detection geometry
  - Applies least squares optimization to solve target positions from bistatic range and Doppler measurements
  - Handles 3 or more radar detections for improved accuracy
  - Provides robust error handling for non-converging cases

The system architecture is as follows:

- The API server and HTML pages are served through a [Flask](http://github.com/pallets/flask) in Python.
- An initial API request with a new set of parameters (algorithms or radar nodes) will add these parameters to a common processing loop. This is so fair comparisons can be made on the same input data.
- A set of API parameters will continue to be processed unless there is no API call in some specified time - see *main.py* to update. This allows the latest geolocation to be provided, rather than adding to the processing loop and waiting for the update from the next time increment.

## Future Work

- Implement an association algorithm that is not reliant on ADS-B truth.
- Choose to use detection or track data from each radar.
- Long term plots to show metrics such as 2D location accuracy to ADS-B, number of aircraft tracked, etc.
- Scale number of samples in ellipse/ellipsoid to size of shape.

## License

[MIT](http://choosealicense.com/licenses/mit)

