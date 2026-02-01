#!/usr/bin/env python3
"""
Enhanced Puppeteer test script for 3lips map interface validation.
Tests for ellipsoids, radar placements, and visual elements on the Cesium map.
"""

import time


def test_map_interface_enhanced():
    """
    Enhanced test for 3lips map interface including ellipsoids and radar placements.
    Run this with Puppeteer MCP tools.
    """

    test_results = {
        "timestamp": time.time(),
        "tests": {},
        "summary": {"passed": 0, "failed": 0, "warnings": 0},
    }

    print("🗺️  Enhanced 3lips Map Interface Tests")
    print("=" * 50)

    # Test 1: Basic Map Loading
    print("\n1. Testing basic map interface...")

    # Instructions for Puppeteer MCP
    print("📋 Puppeteer Commands to Execute:")
    print("   1. mcp__puppeteer__puppeteer_navigate to http://localhost:5000")
    print("   2. mcp__puppeteer__puppeteer_screenshot with name 'main_page'")
    print("   3. Click Map button and navigate to map interface")
    print("   4. mcp__puppeteer__puppeteer_screenshot with name 'map_loaded'")

    # Test 2: Check for Cesium Elements
    test_cesium_elements = """
    // Test for Cesium map elements
    const cesiumResults = {
        cesiumContainer: !!document.querySelector('.cesium-widget'),
        cesiumCanvas: !!document.querySelector('.cesium-canvas'),
        cesiumToolbar: !!document.querySelector('.cesium-toolbar'),
        cesiumViewer: !!window.viewer || !!window.cesiumViewer,
        trackLegend: !!document.querySelector('[class*="legend"]') || !!document.querySelector('[id*="legend"]'),
        trackControls: document.querySelectorAll('button').length > 0
    };

    // Check for map data elements
    cesiumResults.hasDataElements = {
        totalButtons: document.querySelectorAll('button').length,
        buttonTexts: Array.from(document.querySelectorAll('button')).map(b => b.textContent?.trim()),
        hasShowTracks: Array.from(document.querySelectorAll('button')).some(b => b.textContent?.includes('Track')),
        hasShowPaths: Array.from(document.querySelectorAll('button')).some(b => b.textContent?.includes('Path')),
        hasShowLabels: Array.from(document.querySelectorAll('button')).some(b => b.textContent?.includes('Label'))
    };

    console.log('Cesium Interface Check:', cesiumResults);
    cesiumResults;
    """

    print("\n📋 Execute this JavaScript in Puppeteer:")
    print("   mcp__puppeteer__puppeteer_evaluate:")
    print(f"   {test_cesium_elements}")

    # Test 3: Check for Map Data Elements
    test_map_data = """
    // Check for radar and ellipsoid data on the map
    const mapDataResults = {
        timestamp: Date.now(),
        viewport: {
            width: window.innerWidth,
            height: window.innerHeight
        }
    };

    // Check for Cesium primitives and entities
    if (window.viewer) {
        const viewer = window.viewer;

        mapDataResults.cesiumEntities = {
            entityCount: viewer.entities.values.length,
            hasEntities: viewer.entities.values.length > 0,
            entityTypes: viewer.entities.values.map(e => ({
                id: e.id,
                name: e.name,
                hasPosition: !!e.position,
                hasEllipsoid: !!e.ellipsoid,
                hasPoint: !!e.point,
                hasModel: !!e.model,
                hasLabel: !!e.label
            }))
        };

        mapDataResults.cesiumPrimitives = {
            primitiveCount: viewer.scene.primitives.length,
            hasPrimitives: viewer.scene.primitives.length > 0
        };

        mapDataResults.camera = {
            position: viewer.camera.position,
            heading: viewer.camera.heading,
            pitch: viewer.camera.pitch,
            roll: viewer.camera.roll
        };

        // Check for specific data types
        mapDataResults.dataVisualization = {
            hasRadarMarkers: viewer.entities.values.some(e =>
                e.id && (e.id.includes('radar') || e.id.includes('station'))
            ),
            hasEllipsoids: viewer.entities.values.some(e => !!e.ellipsoid),
            hasAircraftTracks: viewer.entities.values.some(e =>
                e.id && (e.id.includes('track') || e.id.includes('aircraft'))
            ),
            hasDetectionData: viewer.entities.values.some(e =>
                e.id && (e.id.includes('detection') || e.id.includes('target'))
            )
        };

    } else {
        mapDataResults.error = 'Cesium viewer not found - map may not be loaded';
    }

    // Check console for any errors
    mapDataResults.consoleErrors = {
        hasErrors: window.console._errors && window.console._errors.length > 0,
        errorCount: window.console._errors ? window.console._errors.length : 0
    };

    console.log('Map Data Analysis:', mapDataResults);
    mapDataResults;
    """

    print("\n📋 Execute this JavaScript to check map data:")
    print("   mcp__puppeteer__puppeteer_evaluate:")
    print(f"   {test_map_data}")

    # Test 4: Check Network Requests
    test_network_requests = """
    // Monitor network requests for data fetching
    const networkResults = {
        timestamp: Date.now(),
        pendingRequests: 0,
        completedRequests: 0,
        errors: []
    };

    // Check if fetch is being called and what endpoints
    const originalFetch = window.fetch;
    let requestCount = 0;

    window.fetch = function(...args) {
        requestCount++;
        console.log('Fetch request #' + requestCount + ':', args[0]);

        return originalFetch.apply(this, arguments)
            .then(response => {
                console.log('Fetch response for:', args[0], 'Status:', response.status);
                return response;
            })
            .catch(error => {
                console.log('Fetch error for:', args[0], 'Error:', error.message);
                networkResults.errors.push({
                    url: args[0],
                    error: error.message,
                    timestamp: Date.now()
                });
                throw error;
            });
    };

    networkResults.fetchMonitorInstalled = true;
    networkResults.currentRequestCount = requestCount;

    // Wait a moment for any automatic requests
    setTimeout(() => {
        console.log('Network monitoring active. Current requests:', requestCount);
    }, 1000);

    networkResults;
    """

    print("\n📋 Execute this JavaScript to monitor network requests:")
    print("   mcp__puppeteer__puppeteer_evaluate:")
    print(f"   {test_network_requests}")

    # Test 5: Simulate Data Loading
    test_data_simulation = """
    // Test if we can manually trigger data updates
    const simulationResults = {
        timestamp: Date.now(),
        tests: {}
    };

    // Try to find and click data refresh buttons
    const buttons = Array.from(document.querySelectorAll('button'));
    const showTracksBtn = buttons.find(b => b.textContent?.includes('Track'));
    const showPathsBtn = buttons.find(b => b.textContent?.includes('Path'));
    const showLabelsBtn = buttons.find(b => b.textContent?.includes('Label'));

    simulationResults.availableButtons = buttons.map(b => b.textContent?.trim());

    // Test button clicks
    if (showTracksBtn) {
        showTracksBtn.click();
        simulationResults.tests.showTracksClicked = true;
        console.log('Clicked Show Tracks button');
    }

    if (showPathsBtn) {
        showPathsBtn.click();
        simulationResults.tests.showPathsClicked = true;
        console.log('Clicked Show Paths button');
    }

    if (showLabelsBtn) {
        showLabelsBtn.click();
        simulationResults.tests.showLabelsClicked = true;
        console.log('Clicked Show Labels button');
    }

    // Check if any data sources are being polled
    const checkDataPolling = () => {
        // Look for evidence of data polling in the page
        const scripts = Array.from(document.querySelectorAll('script')).map(s => s.src);
        const hasDataScripts = scripts.some(src =>
            src.includes('radar') || src.includes('track') || src.includes('ellipsoid')
        );

        simulationResults.tests.hasDataScripts = hasDataScripts;
        simulationResults.tests.scriptSources = scripts.filter(s => s.length > 0);

        return simulationResults;
    };

    setTimeout(checkDataPolling, 2000);

    simulationResults;
    """

    print("\n📋 Execute this JavaScript to test data simulation:")
    print("   mcp__puppeteer__puppeteer_evaluate:")
    print(f"   {test_data_simulation}")

    # Test 6: Validate Expected Elements
    test_validation = """
    // Final validation of expected map elements
    const validationResults = {
        timestamp: Date.now(),
        checks: {},
        score: 0,
        maxScore: 0
    };

    // Check 1: Basic Cesium functionality
    validationResults.maxScore++;
    if (window.viewer && document.querySelector('.cesium-widget')) {
        validationResults.checks.cesiumLoaded = true;
        validationResults.score++;
    } else {
        validationResults.checks.cesiumLoaded = false;
    }

    // Check 2: Track controls present
    validationResults.maxScore++;
    const hasTrackControls = document.querySelectorAll('button').length >= 3;
    if (hasTrackControls) {
        validationResults.checks.trackControls = true;
        validationResults.score++;
    } else {
        validationResults.checks.trackControls = false;
    }

    // Check 3: Camera positioned (not at default)
    validationResults.maxScore++;
    if (window.viewer) {
        const defaultPosition = window.viewer.camera.position;
        const hasCustomPosition = defaultPosition.x !== 0 || defaultPosition.y !== 0;
        if (hasCustomPosition) {
            validationResults.checks.cameraPositioned = true;
            validationResults.score++;
        } else {
            validationResults.checks.cameraPositioned = false;
        }
    }

    // Check 4: No critical console errors
    validationResults.maxScore++;
    const consoleErrors = window.console._errors || [];
    const criticalErrors = consoleErrors.filter(e =>
        e.includes('cesium') || e.includes('viewer') || e.includes('WebGL')
    );
    if (criticalErrors.length === 0) {
        validationResults.checks.noCriticalErrors = true;
        validationResults.score++;
    } else {
        validationResults.checks.noCriticalErrors = false;
        validationResults.criticalErrors = criticalErrors;
    }

    // Check 5: Data visualization elements (if data is available)
    validationResults.maxScore++;
    if (window.viewer) {
        const hasVisualizationElements =
            window.viewer.entities.values.length > 0 ||
            window.viewer.scene.primitives.length > 1; // > 1 because there's usually a default primitive

        if (hasVisualizationElements) {
            validationResults.checks.hasDataVisualization = true;
            validationResults.score++;
        } else {
            validationResults.checks.hasDataVisualization = false;
            validationResults.note = 'No data visualization found - may be normal if no data sources are active';
        }
    }

    validationResults.percentage = (validationResults.score / validationResults.maxScore) * 100;
    validationResults.status = validationResults.percentage >= 80 ? 'PASS' :
                              validationResults.percentage >= 60 ? 'WARNING' : 'FAIL';

    console.log('Final Validation Results:', validationResults);
    validationResults;
    """

    print("\n📋 Execute this JavaScript for final validation:")
    print("   mcp__puppeteer__puppeteer_evaluate:")
    print(f"   {test_validation}")

    # Expected screenshots to take
    print("\n📸 Screenshots to capture:")
    print("   1. 'main_page' - Initial 3lips page")
    print("   2. 'map_loaded' - Map interface after loading")
    print("   3. 'map_with_controls' - After clicking track controls")
    print("   4. 'map_final_state' - Final state for comparison")

    # Summary and next steps
    print("\n🎯 What to Look For:")
    print("   ✅ Cesium map loads without WebGL errors")
    print("   ✅ Track controls (Show Tracks, Show Paths, Show Labels) present")
    print("   ✅ Camera positioned over geographic area (not default 0,0,0)")
    print("   ✅ No critical JavaScript errors in console")
    print("   📊 Radar markers/stations visible (if data available)")
    print("   📊 Ellipsoids from localization (if processing data)")
    print("   📊 Aircraft tracks/detections (if synthetic-adsb working)")

    print("\n⚠️  Expected Issues in Development Mode:")
    print("   • 'Unexpected end of JSON input' - Normal when no live data")
    print("   • Empty entities collection - Normal when no radar sources")
    print("   • Fetch 404 errors - Normal for missing endpoints")

    return test_results


if __name__ == "__main__":
    test_map_interface_enhanced()
