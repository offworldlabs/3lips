#!/usr/bin/env python3
"""
End-to-End Integration Test: RETINASolver with Synthetic-ADSB
Tests complete pipeline: synthetic-adsb → radar detection → RETINASolver → track initiation → visualization

This test verifies:
1. Synthetic-ADSB data flows to 3lips
2. RETINASolver processes radar detections
3. Tracks are initiated and maintained
4. Visual confirmation via Puppeteer interface
"""

import json
import subprocess
import time

import requests


def setup_test_environment():
    """Set up the test environment with synthetic-adsb and RETINASolver."""
    print("🚀 Setting up End-to-End Integration Test Environment")
    print("=" * 60)

    setup_results = {
        "synthetic_adsb": False,
        "retina_solver": False,
        "services_running": False,
        "network_connectivity": False,
    }

    # Step 1: Create enhanced docker-compose with synthetic-adsb
    print("\n1. Creating integrated docker-compose configuration...")

    enhanced_compose = """
version: '3.8'

networks:
  3lips:
    driver: bridge
  retina-network:
    external: true
    name: retina-network

services:
  # Synthetic ADS-B data source
  synthetic-adsb:
    build:
      context: ../synthetic-adsb
      dockerfile: Dockerfile
    image: synthetic-adsb
    ports:
      - "5001:5001"
    networks:
      - retina-network
      - 3lips
    container_name: synthetic-adsb-test
    environment:
      - PYTHONUNBUFFERED=1
      - TRANSMITTER_LAT=-34.9286
      - TRANSMITTER_LON=138.5999
      - RADAR1_LAT=-34.9000
      - RADAR1_LON=138.6000
      - RADAR2_LAT=-34.9500
      - RADAR2_LON=138.6000
    volumes:
      - ../synthetic-adsb:/app
    command: ["python", "server.py"]

  # 3lips API with RETINASolver
  api:
    extends:
      file: docker-compose.yml
      service: api
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=1
      - LOCALISATION_ALGORITHM=retina-solver  # Use RETINASolver!
      - ADSB_URL=http://synthetic-adsb-test:5001
    depends_on:
      - event
      - synthetic-adsb

  # Event processor with RETINASolver integration
  event:
    extends:
      file: docker-compose.yml
      service: event
    environment:
      - TRACKER_VERBOSE=true
      - LOCALISATION_ALGORITHM=retina-solver  # Use RETINASolver!
      - ADSB_URL=http://synthetic-adsb-test:5001
      - SYNTHETIC_RADAR_URLS=http://synthetic-adsb-test:5001/radar1,http://synthetic-adsb-test:5001/radar2,http://synthetic-adsb-test:5001/radar3
    depends_on:
      - synthetic-adsb

  # Cesium visualization
  cesium-apache:
    extends:
      file: docker-compose.yml
      service: cesium-apache
"""

    with open("docker-compose-e2e-test.yml", "w") as f:
        f.write(enhanced_compose)

    print("   ✅ Enhanced docker-compose configuration created")

    # Step 2: Start the integrated environment
    print("\n2. Starting integrated test environment...")
    try:
        # Stop any existing containers
        subprocess.run(["docker", "compose", "down"], capture_output=True)
        subprocess.run(
            ["docker", "compose", "-f", "docker-compose-e2e-test.yml", "down"],
            capture_output=True,
        )

        # Start the test environment
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose-e2e-test.yml",
                "up",
                "-d",
                "--build",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            setup_results["services_running"] = True
            print("   ✅ Test environment started successfully")
        else:
            print(f"   ❌ Failed to start environment: {result.stderr}")
            return setup_results

    except Exception as e:
        print(f"   ❌ Error starting environment: {e}")
        return setup_results

    # Step 3: Wait for services to initialize
    print("\n3. Waiting for services to initialize...")
    time.sleep(15)

    # Step 4: Verify synthetic-adsb is running
    print("\n4. Verifying synthetic-adsb data source...")
    try:
        response = requests.get("http://localhost:5001/data/aircraft.json", timeout=10)
        if response.status_code == 200:
            aircraft_data = response.json()
            if aircraft_data and aircraft_data.get("aircraft", []):
                setup_results["synthetic_adsb"] = True
                print(
                    f"   ✅ Synthetic-ADSB running with {len(aircraft_data.get('aircraft', []))} aircraft"
                )
            else:
                print("   ⚠️  Synthetic-ADSB running but no aircraft data")
        else:
            print(f"   ❌ Synthetic-ADSB not responding: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cannot reach synthetic-ADSB: {e}")

    # Step 5: Verify RETINASolver integration
    print("\n5. Verifying RETINASolver integration...")
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "3lips-event",
                "python",
                "-c",
                """
import sys
sys.path.insert(0, '/app')
try:
    from algorithm.localisation.RETINASolverLocalisation import RETINASolverLocalisation
    solver = RETINASolverLocalisation()
    print('RETINASolver available')
except Exception as e:
    print(f'RETINASolver error: {e}')
            """,
            ],
            capture_output=True,
            text=True,
        )

        if "RETINASolver available" in result.stdout:
            setup_results["retina_solver"] = True
            print("   ✅ RETINASolver integration verified")
        else:
            print(
                f"   ❌ RETINASolver integration failed: {result.stdout} {result.stderr}"
            )
    except Exception as e:
        print(f"   ❌ Cannot verify RETINASolver: {e}")

    # Step 6: Test network connectivity
    print("\n6. Testing network connectivity...")
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "3lips-event",
                "curl",
                "-s",
                "http://synthetic-adsb-test:5001/data/aircraft.json",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and len(result.stdout) > 10:
            setup_results["network_connectivity"] = True
            print("   ✅ Network connectivity verified")
        else:
            print(f"   ❌ Network connectivity failed: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Cannot test connectivity: {e}")

    return setup_results


def monitor_track_initiation(duration_minutes=5):
    """Monitor the 3lips system for track initiation using RETINASolver."""
    print(f"\n📡 Monitoring Track Initiation for {duration_minutes} minutes")
    print("=" * 60)

    monitoring_results = {
        "start_time": time.time(),
        "duration_minutes": duration_minutes,
        "tracks_detected": [],
        "retina_solver_calls": 0,
        "successful_localizations": 0,
        "api_responses": [],
    }

    end_time = time.time() + (duration_minutes * 60)
    check_interval = 30  # Check every 30 seconds

    print(f"🔍 Starting monitoring loop (checks every {check_interval}s)...")

    while time.time() < end_time:
        remaining = int((end_time - time.time()) / 60)
        print(f"\n⏱️  Time remaining: {remaining}m - Checking system status...")

        try:
            # Check API for track data
            try:
                response = requests.get("http://localhost:8080/api", timeout=10)
                if response.status_code == 200:
                    try:
                        api_data = response.json()
                        monitoring_results["api_responses"].append(
                            {
                                "timestamp": time.time(),
                                "tracks": len(api_data.get("system_tracks", [])),
                                "algorithm": api_data.get("localisation", "unknown"),
                                "detections_associated": len(
                                    api_data.get("detections_associated", {})
                                ),
                                "detections_localised": len(
                                    api_data.get("detections_localised", {})
                                ),
                            }
                        )

                        current_tracks = len(api_data.get("system_tracks", []))
                        current_algorithm = api_data.get("localisation", "unknown")

                        print("   📊 System Status:")
                        print(f"      Algorithm: {current_algorithm}")
                        print(f"      Active tracks: {current_tracks}")
                        print(
                            f"      Detections associated: {len(api_data.get('detections_associated', {}))}"
                        )
                        print(
                            f"      Detections localized: {len(api_data.get('detections_localised', {}))}"
                        )

                        if current_tracks > len(monitoring_results["tracks_detected"]):
                            new_tracks = current_tracks - len(
                                monitoring_results["tracks_detected"]
                            )
                            print(f"   🎉 {new_tracks} new track(s) initiated!")
                            monitoring_results["tracks_detected"].extend(
                                [f"track_{i}" for i in range(new_tracks)]
                            )

                    except json.JSONDecodeError:
                        print("   ⚠️  API returned non-JSON response")
                else:
                    print(f"   ❌ API request failed: {response.status_code}")
            except requests.RequestException as e:
                print(f"   ❌ Cannot reach API: {e}")

            # Check RETINASolver logs
            try:
                result = subprocess.run(
                    ["docker", "logs", "--tail", "50", "3lips-event"],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    log_lines = result.stdout.split("\n")
                    retina_logs = [line for line in log_lines if "RETINASolver" in line]

                    if retina_logs:
                        print("   🔧 Recent RETINASolver activity:")
                        for log in retina_logs[-3:]:  # Show last 3 RETINASolver logs
                            print(f"      {log.strip()}")

                        monitoring_results["retina_solver_calls"] += len(retina_logs)

                        success_logs = [
                            line for line in retina_logs if "result for" in line
                        ]
                        monitoring_results["successful_localizations"] += len(
                            success_logs
                        )
            except Exception as e:
                print(f"   ⚠️  Cannot check logs: {e}")

            # Check synthetic-adsb activity
            try:
                response = requests.get(
                    "http://localhost:5001/data/aircraft.json", timeout=5
                )
                if response.status_code == 200:
                    aircraft_data = response.json()
                    aircraft = aircraft_data.get("aircraft", [])
                    print(f"   ✈️  Synthetic-ADSB: {len(aircraft)} aircraft active")
                else:
                    print("   ⚠️  Synthetic-ADSB not responding")
            except Exception as e:
                print(f"   ⚠️  Cannot reach Synthetic-ADSB: {e}")

        except Exception as e:
            print(f"   ❌ Monitoring error: {e}")

        if time.time() < end_time:
            print(f"   ⏳ Waiting {check_interval}s for next check...")
            time.sleep(check_interval)

    # Final summary
    monitoring_results["end_time"] = time.time()
    monitoring_results["total_duration"] = (
        monitoring_results["end_time"] - monitoring_results["start_time"]
    )

    print("\n📊 Monitoring Results Summary:")
    print(f"   Duration: {monitoring_results['total_duration'] / 60:.1f} minutes")
    print(f"   Tracks detected: {len(monitoring_results['tracks_detected'])}")
    print(f"   RETINASolver calls: {monitoring_results['retina_solver_calls']}")
    print(
        f"   Successful localizations: {monitoring_results['successful_localizations']}"
    )
    print(f"   API checks performed: {len(monitoring_results['api_responses'])}")

    return monitoring_results


def create_puppeteer_test_script():
    """Create a Puppeteer test script for visual validation."""

    puppeteer_script = """
/**
 * Puppeteer Test Script for RETINASolver Track Initiation Validation
 *
 * This script should be run with Puppeteer MCP to visually verify:
 * 1. Map loads with RETINASolver-generated tracks
 * 2. Track count matches expected values
 * 3. Ellipsoids/detections are visible
 * 4. Track paths show aircraft movement
 */

async function validateRETINASolverTracks(navigate, screenshot, evaluate) {
    console.log('🎭 Starting Puppeteer Validation of RETINASolver Track Initiation');

    const results = {
        timestamp: Date.now(),
        tests: {},
        screenshots: [],
        summary: { passed: 0, failed: 0, warnings: 0 }
    };

    try {
        // Step 1: Navigate to main page
        console.log('📍 Step 1: Navigate to main interface');
        await navigate('http://localhost:8080');
        await screenshot('retina_solver_main_page');
        results.screenshots.push('retina_solver_main_page');

        // Step 2: Check API data
        console.log('📍 Step 2: Check API for RETINASolver usage');
        const apiData = await evaluate(`
            fetch('/api')
                .then(response => response.json())
                .then(data => {
                    console.log('🔍 API Data:', data);
                    return {
                        algorithm: data.localisation,
                        tracks: data.system_tracks ? data.system_tracks.length : 0,
                        detections_associated: Object.keys(data.detections_associated || {}).length,
                        detections_localised: Object.keys(data.detections_localised || {}).length,
                        timestamp: data.timestamp
                    };
                })
                .catch(error => ({
                    error: error.message,
                    algorithm: 'unknown'
                }));
        `);

        results.tests.apiCheck = apiData;

        if (apiData.algorithm === 'retina-solver') {
            console.log('✅ RETINASolver is active algorithm');
            results.summary.passed++;
        } else {
            console.log(`❌ Expected retina-solver, got: ${apiData.algorithm}`);
            results.summary.failed++;
        }

        if (apiData.tracks > 0) {
            console.log(`✅ ${apiData.tracks} tracks detected`);
            results.summary.passed++;
        } else {
            console.log('⚠️ No tracks detected yet');
            results.summary.warnings++;
        }

        // Step 3: Navigate to map
        console.log('📍 Step 3: Navigate to map interface');
        await evaluate(`
            const buttons = Array.from(document.querySelectorAll('button, a'));
            const mapButton = buttons.find(b => b.textContent?.trim() === 'Map');
            if (mapButton) mapButton.click();
        `);

        // Wait for map to load
        await new Promise(resolve => setTimeout(resolve, 3000));
        await screenshot('retina_solver_map_loaded');
        results.screenshots.push('retina_solver_map_loaded');

        // Step 4: Analyze map entities
        console.log('📍 Step 4: Analyze map visualization');
        const mapAnalysis = await evaluate(`
            if (window.viewer) {
                const viewer = window.viewer;
                const entities = viewer.entities.values;

                const analysis = {
                    totalEntities: entities.length,
                    entityTypes: {
                        points: entities.filter(e => !!e.point).length,
                        ellipsoids: entities.filter(e => !!e.ellipsoid).length,
                        polylines: entities.filter(e => !!e.polyline).length,
                        models: entities.filter(e => !!e.model).length
                    },
                    trackVisualization: {
                        hasRadarMarkers: entities.some(e =>
                            e.id && (e.id.includes('radar') || e.id.includes('rx') || e.id.includes('tx'))
                        ),
                        hasTrackPaths: entities.some(e => !!e.polyline),
                        hasDetectionPoints: entities.filter(e => !!e.point).length > 10
                    }
                };

                // Check track legend
                const trackInfo = document.body.textContent;
                analysis.trackLegend = {
                    activeTracksVisible: trackInfo.includes('Active Tracks'),
                    adsbTracksVisible: trackInfo.includes('ADS-B'),
                    activeTrackCount: trackInfo.match(/Active Tracks: (\\d+)/)?.[1] || '0',
                    adsbTrackCount: trackInfo.match(/ADS-B: (\\d+)/)?.[1] || '0'
                };

                console.log('🗺️ Map Analysis:', analysis);
                return analysis;
            } else {
                return { error: 'Cesium viewer not available' };
            }
        `);

        results.tests.mapAnalysis = mapAnalysis;

        // Validate map results
        if (mapAnalysis.totalEntities > 0) {
            console.log(`✅ ${mapAnalysis.totalEntities} entities on map`);
            results.summary.passed++;
        } else {
            console.log('❌ No entities found on map');
            results.summary.failed++;
        }

        if (mapAnalysis.trackVisualization?.hasTrackPaths) {
            console.log('✅ Track paths visible');
            results.summary.passed++;
        } else {
            console.log('⚠️ No track paths visible');
            results.summary.warnings++;
        }

        if (mapAnalysis.trackVisualization?.hasRadarMarkers) {
            console.log('✅ Radar markers visible');
            results.summary.passed++;
        } else {
            console.log('⚠️ No radar markers visible');
            results.summary.warnings++;
        }

        // Step 5: Test track controls
        console.log('📍 Step 5: Test track control buttons');
        const controlTest = await evaluate(`
            const buttons = Array.from(document.querySelectorAll('button'));
            const showTracksBtn = buttons.find(b => b.textContent?.includes('Track'));
            const showPathsBtn = buttons.find(b => b.textContent?.includes('Path'));

            let controlResults = {
                buttonsFound: buttons.map(b => b.textContent?.trim()),
                trackButtonClicked: false,
                pathButtonClicked: false
            };

            if (showTracksBtn) {
                showTracksBtn.click();
                controlResults.trackButtonClicked = true;
                console.log('✅ Clicked track button');
            }

            if (showPathsBtn) {
                showPathsBtn.click();
                controlResults.pathButtonClicked = true;
                console.log('✅ Clicked paths button');
            }

            return controlResults;
        `);

        results.tests.controlTest = controlTest;

        // Final screenshot after control tests
        await screenshot('retina_solver_map_final');
        results.screenshots.push('retina_solver_map_final');

        // Step 6: Summary
        const totalTests = results.summary.passed + results.summary.failed + results.summary.warnings;
        const successRate = (results.summary.passed / totalTests) * 100;

        console.log('\\n📊 Puppeteer Validation Summary:');
        console.log(`   Tests passed: ${results.summary.passed}`);
        console.log(`   Tests failed: ${results.summary.failed}`);
        console.log(`   Warnings: ${results.summary.warnings}`);
        console.log(`   Success rate: ${successRate.toFixed(1)}%`);
        console.log(`   Screenshots: ${results.screenshots.join(', ')}`);

        results.status = successRate >= 80 ? 'PASS' : successRate >= 60 ? 'WARNING' : 'FAIL';

        if (results.status === 'PASS') {
            console.log('🎉 RETINASolver track initiation validation: PASSED');
        } else if (results.status === 'WARNING') {
            console.log('⚠️ RETINASolver track initiation validation: PASSED with warnings');
        } else {
            console.log('❌ RETINASolver track initiation validation: FAILED');
        }

    } catch (error) {
        console.error('❌ Puppeteer test error:', error);
        results.error = error.message;
        results.status = 'ERROR';
    }

    return results;
}

// Export for use with Puppeteer MCP
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { validateRETINASolverTracks };
}
"""

    with open("puppeteer_retina_solver_validation.js", "w") as f:
        f.write(puppeteer_script)

    print(
        "📝 Puppeteer validation script created: puppeteer_retina_solver_validation.js"
    )
    return "puppeteer_retina_solver_validation.js"


def run_integration_test():
    """Run the complete integration test."""
    print("🧪 RETINASolver Integration Test with Synthetic-ADSB")
    print("=" * 70)
    print("This test validates:")
    print("  1. Synthetic-ADSB data generation")
    print("  2. RETINASolver processing of radar detections")
    print("  3. Track initiation and management")
    print("  4. Visual confirmation via web interface")
    print("=" * 70)

    # Step 1: Setup
    setup_results = setup_test_environment()

    if not all(setup_results.values()):
        print("\\n❌ Setup failed. Cannot proceed with integration test.")
        print("Failed components:")
        for component, status in setup_results.items():
            if not status:
                print(f"  - {component}")
        return False

    print("\\n✅ Test environment setup complete!")

    # Step 2: Monitor track initiation
    monitoring_results = monitor_track_initiation(duration_minutes=3)

    # Step 3: Create Puppeteer test
    puppeteer_script = create_puppeteer_test_script()

    # Step 4: Final summary
    print("\\n" + "=" * 70)
    print("🎯 Integration Test Summary")
    print("=" * 70)

    print("✅ Environment Setup: All components operational")
    print(
        f"📊 Track Monitoring: {len(monitoring_results['tracks_detected'])} tracks detected"
    )
    print(
        f"🔧 RETINASolver Activity: {monitoring_results['retina_solver_calls']} calls"
    )
    print(
        f"🎯 Successful Localizations: {monitoring_results['successful_localizations']}"
    )
    print(f"🎭 Puppeteer Script: {puppeteer_script}")

    success_criteria = [
        monitoring_results["retina_solver_calls"] > 0,
        len(monitoring_results["tracks_detected"]) > 0,
        setup_results["synthetic_adsb"],
        setup_results["retina_solver"],
    ]

    if all(success_criteria):
        print("\\n🎉 INTEGRATION TEST PASSED!")
        print("   RETINASolver successfully processes synthetic-ADSB data")
        print("   Track initiation working correctly")
        print("   Ready for visual validation with Puppeteer")
    else:
        print("\\n⚠️ INTEGRATION TEST INCOMPLETE")
        print("   Some components may need adjustment")
        print("   Check logs for details")

    print("\\n📋 Next Steps:")
    print("   1. Run Puppeteer validation script for visual confirmation")
    print("   2. Use Claude Code with Puppeteer MCP:")
    print(f"      Load: {puppeteer_script}")
    print("      Execute: validateRETINASolverTracks(navigate, screenshot, evaluate)")
    print("   3. Review screenshots for track visualization")

    return all(success_criteria)


if __name__ == "__main__":
    run_integration_test()
