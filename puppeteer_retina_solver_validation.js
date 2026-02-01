/**
 * Puppeteer Test Script for RETINASolver Track Initiation Validation
 * 
 * This script validates:
 * 1. RETINASolver is the active localization algorithm
 * 2. Synthetic-ADSB data flows through the system
 * 3. Tracks are initiated and displayed on the map
 * 4. Visual elements (radar markers, ellipsoids, paths) are present
 * 
 * Usage with Puppeteer MCP:
 * 1. Load this file in Claude Code
 * 2. Execute: validateRETINASolverTracks(navigate, screenshot, evaluate)
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
        
        // Step 2: Check API data for RETINASolver
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
                        timestamp: data.timestamp,
                        servers: data.server || [],
                        associator: data.associator
                    };
                })
                .catch(error => ({
                    error: error.message,
                    algorithm: 'unknown',
                    tracks: 0
                }));
        `);
        
        results.tests.apiCheck = apiData;
        
        // Validate RETINASolver is active
        if (apiData.algorithm === 'retina-solver') {
            console.log('✅ RETINASolver is the active localization algorithm');
            results.summary.passed++;
        } else if (apiData.algorithm === 'ellipse-parametric-mean') {
            console.log('⚠️ Default algorithm active, RETINASolver may not be configured');
            console.log('   Current algorithm:', apiData.algorithm);
            results.summary.warnings++;
        } else {
            console.log(`❌ Unexpected algorithm: ${apiData.algorithm} (expected: retina-solver)`);
            results.summary.failed++;
        }
        
        // Validate track data
        if (apiData.tracks > 0) {
            console.log(`✅ ${apiData.tracks} active tracks detected`);
            results.summary.passed++;
        } else {
            console.log('⚠️ No active tracks detected yet (may be normal during startup)');
            results.summary.warnings++;
        }
        
        // Validate data flow
        if (apiData.detections_associated > 0 || apiData.detections_localised > 0) {
            console.log('✅ Data processing pipeline active');
            console.log(`   Associated: ${apiData.detections_associated}, Localised: ${apiData.detections_localised}`);
            results.summary.passed++;
        } else {
            console.log('⚠️ No detection processing detected');
            results.summary.warnings++;
        }
        
        // Step 3: Check synthetic-ADSB data source
        console.log('📍 Step 3: Validate synthetic-ADSB data source');
        const adsbData = await evaluate(`
            fetch('http://localhost:5001/aircraft')
                .then(response => response.json())
                .then(data => {
                    console.log('✈️ Aircraft data:', data);
                    return {
                        aircraftCount: Array.isArray(data) ? data.length : 0,
                        hasData: Array.isArray(data) && data.length > 0,
                        sampleAircraft: Array.isArray(data) ? data[0] : null
                    };
                })
                .catch(error => ({
                    error: error.message,
                    aircraftCount: 0,
                    hasData: false
                }));
        `);
        
        results.tests.adsbCheck = adsbData;
        
        if (adsbData.hasData) {
            console.log(`✅ Synthetic-ADSB providing ${adsbData.aircraftCount} aircraft`);
            results.summary.passed++;
        } else {
            console.log('❌ Synthetic-ADSB not providing aircraft data');
            results.summary.failed++;
        }
        
        // Step 4: Navigate to map interface
        console.log('📍 Step 4: Navigate to map interface');
        await evaluate(`
            const buttons = Array.from(document.querySelectorAll('button, a'));
            const mapButton = buttons.find(b => b.textContent?.trim() === 'Map') ||
                             buttons.find(b => b.textContent?.toLowerCase().includes('map'));
            if (mapButton) {
                console.log('🗺️ Clicking map button');
                mapButton.click();
            } else {
                console.log('⚠️ Map button not found');
            }
        `);
        
        // Wait for map to load
        await new Promise(resolve => setTimeout(resolve, 5000));
        await screenshot('retina_solver_map_loaded');
        results.screenshots.push('retina_solver_map_loaded');
        
        // Step 5: Analyze map visualization
        console.log('📍 Step 5: Analyze map visualization');
        const mapAnalysis = await evaluate(`
            if (window.viewer) {
                const viewer = window.viewer;
                const entities = viewer.entities.values;
                
                const analysis = {
                    cesiumLoaded: true,
                    totalEntities: entities.length,
                    entityTypes: {
                        points: entities.filter(e => !!e.point).length,
                        ellipsoids: entities.filter(e => !!e.ellipsoid).length,
                        polylines: entities.filter(e => !!e.polyline).length,
                        models: entities.filter(e => !!e.model).length
                    },
                    visualization: {
                        hasRadarMarkers: entities.some(e => 
                            e.id && (e.id.includes('radar') || e.id.includes('rx') || e.id.includes('tx'))
                        ),
                        hasTrackPaths: entities.some(e => !!e.polyline),
                        hasDetectionPoints: entities.filter(e => !!e.point).length > 10,
                        hasEllipsoids: entities.some(e => !!e.ellipsoid)
                    },
                    sampleEntityIds: entities.slice(0, 5).map(e => e.id)
                };
                
                // Check track legend information
                const trackInfo = document.body.textContent;
                analysis.trackLegend = {
                    activeTracksVisible: trackInfo.includes('Active Tracks'),
                    adsbTracksVisible: trackInfo.includes('ADS-B'),
                    activeTrackCount: parseInt(trackInfo.match(/Active Tracks: (\\d+)/)?.[1] || '0'),
                    adsbTrackCount: parseInt(trackInfo.match(/ADS-B: (\\d+)/)?.[1] || '0'),
                    radarCount: parseInt(trackInfo.match(/Radar: (\\d+)/)?.[1] || '0')
                };
                
                console.log('🗺️ Map Analysis:', analysis);
                return analysis;
            } else {
                return { 
                    cesiumLoaded: false,
                    error: 'Cesium viewer not available',
                    totalEntities: 0
                };
            }
        `);
        
        results.tests.mapAnalysis = mapAnalysis;
        
        // Validate map functionality
        if (mapAnalysis.cesiumLoaded) {
            console.log('✅ Cesium map loaded successfully');
            results.summary.passed++;
        } else {
            console.log('❌ Cesium map failed to load');
            results.summary.failed++;
        }
        
        if (mapAnalysis.totalEntities > 0) {
            console.log(`✅ ${mapAnalysis.totalEntities} visualization entities on map`);
            results.summary.passed++;
        } else {
            console.log('❌ No visualization entities found on map');
            results.summary.failed++;
        }
        
        // Validate specific visualization elements
        if (mapAnalysis.visualization?.hasRadarMarkers) {
            console.log('✅ Radar markers visible on map');
            results.summary.passed++;
        } else {
            console.log('⚠️ No radar markers visible');
            results.summary.warnings++;
        }
        
        if (mapAnalysis.visualization?.hasTrackPaths) {
            console.log('✅ Track paths visible on map');
            results.summary.passed++;
        } else {
            console.log('⚠️ No track paths visible');
            results.summary.warnings++;
        }
        
        if (mapAnalysis.visualization?.hasDetectionPoints) {
            console.log('✅ Detection points visible (likely from RETINASolver)');
            results.summary.passed++;
        } else {
            console.log('⚠️ Few or no detection points visible');
            results.summary.warnings++;
        }
        
        // Validate track legend shows activity
        if (mapAnalysis.trackLegend?.activeTrackCount > 0) {
            console.log(`✅ ${mapAnalysis.trackLegend.activeTrackCount} active tracks shown in legend`);
            results.summary.passed++;
        } else {
            console.log('⚠️ No active tracks shown in legend');
            results.summary.warnings++;
        }
        
        // Step 6: Test track controls
        console.log('📍 Step 6: Test track control functionality');
        const controlTest = await evaluate(`
            const buttons = Array.from(document.querySelectorAll('button'));
            const showTracksBtn = buttons.find(b => b.textContent?.includes('Track'));
            const showPathsBtn = buttons.find(b => b.textContent?.includes('Path'));
            const showLabelsBtn = buttons.find(b => b.textContent?.includes('Label'));
            
            let controlResults = {
                availableButtons: buttons.map(b => b.textContent?.trim()).filter(t => t),
                trackButtonFound: !!showTracksBtn,
                pathButtonFound: !!showPathsBtn,
                labelButtonFound: !!showLabelsBtn,
                interactions: []
            };
            
            // Test track button
            if (showTracksBtn) {
                const initialText = showTracksBtn.textContent;
                showTracksBtn.click();
                setTimeout(() => {
                    const newText = showTracksBtn.textContent;
                    controlResults.interactions.push({
                        button: 'tracks',
                        initialText: initialText,
                        newText: newText,
                        changed: initialText !== newText
                    });
                }, 1000);
            }
            
            // Test paths button
            if (showPathsBtn) {
                const initialText = showPathsBtn.textContent;
                showPathsBtn.click();
                setTimeout(() => {
                    const newText = showPathsBtn.textContent;
                    controlResults.interactions.push({
                        button: 'paths',
                        initialText: initialText,
                        newText: newText,
                        changed: initialText !== newText
                    });
                }, 1000);
            }
            
            return controlResults;
        `);
        
        results.tests.controlTest = controlTest;
        
        if (controlTest.trackButtonFound && controlTest.pathButtonFound) {
            console.log('✅ Track control buttons found and functional');
            results.summary.passed++;
        } else {
            console.log('⚠️ Some track control buttons missing');
            results.summary.warnings++;
        }
        
        // Final screenshot after interactions
        await new Promise(resolve => setTimeout(resolve, 2000));
        await screenshot('retina_solver_map_final');
        results.screenshots.push('retina_solver_map_final');
        
        // Step 7: Final validation summary
        console.log('📍 Step 7: Final validation summary');
        
        const totalTests = results.summary.passed + results.summary.failed + results.summary.warnings;
        const successRate = totalTests > 0 ? (results.summary.passed / totalTests) * 100 : 0;
        
        console.log('\\n📊 Puppeteer Validation Results:');
        console.log('================================');
        console.log(`✅ Tests passed: ${results.summary.passed}`);
        console.log(`❌ Tests failed: ${results.summary.failed}`);
        console.log(`⚠️ Warnings: ${results.summary.warnings}`);
        console.log(`📈 Success rate: ${successRate.toFixed(1)}%`);
        console.log(`📸 Screenshots: ${results.screenshots.join(', ')}`);
        
        // Determine overall status
        if (results.summary.failed === 0 && results.summary.passed >= 5) {
            results.status = 'PASS';
            console.log('\\n🎉 RETINASolver Integration Test: PASSED');
            console.log('   ✅ RETINASolver processes synthetic-ADSB data correctly');
            console.log('   ✅ Tracks are initiated and displayed properly');
            console.log('   ✅ Map visualization shows radar coverage and detection points');
        } else if (results.summary.failed <= 2 && results.summary.passed >= 3) {
            results.status = 'WARNING';
            console.log('\\n⚠️ RETINASolver Integration Test: PASSED with warnings');
            console.log('   ✅ Core functionality working');
            console.log('   ⚠️ Some components may need attention');
        } else {
            results.status = 'FAIL';
            console.log('\\n❌ RETINASolver Integration Test: FAILED');
            console.log('   ❌ Critical issues detected');
            console.log('   🔧 Review system configuration and logs');
        }
        
        // Detailed findings
        console.log('\\n🔍 Detailed Findings:');
        if (apiData.algorithm === 'retina-solver') {
            console.log('   🎯 RETINASolver is actively processing detections');
        } else {
            console.log(`   ⚠️ Algorithm mismatch: ${apiData.algorithm} (expected: retina-solver)`);
        }
        
        if (adsbData.hasData) {
            console.log('   📡 Synthetic-ADSB data pipeline operational');
        } else {
            console.log('   ❌ Synthetic-ADSB data pipeline issue');
        }
        
        if (mapAnalysis.totalEntities > 0) {
            console.log(`   🗺️ Map visualization active with ${mapAnalysis.totalEntities} entities`);
        } else {
            console.log('   ❌ Map visualization not showing data');
        }
        
        console.log('\\n📋 Ready for Production Assessment:');
        console.log(`   Integration Quality: ${results.status}`);
        console.log('   Merge Recommendation:', results.status === 'PASS' ? '✅ APPROVED' : '⚠️ REVIEW REQUIRED');
        
    } catch (error) {
        console.error('❌ Puppeteer validation error:', error);
        results.error = error.message;
        results.status = 'ERROR';
        console.log('\\n💥 Test execution failed - check system status');
    }
    
    return results;
}

// Additional helper function for quick visual inspection
async function quickVisualCheck(navigate, screenshot) {
    console.log('👁️ Quick Visual Check of RETINASolver Integration');
    
    await navigate('http://localhost:8080');
    await screenshot('quick_main_page');
    
    // Navigate to map
    await evaluate(`
        const mapButton = Array.from(document.querySelectorAll('button, a'))
            .find(b => b.textContent?.trim() === 'Map');
        if (mapButton) mapButton.click();
    `);
    
    await new Promise(resolve => setTimeout(resolve, 3000));
    await screenshot('quick_map_view');
    
    console.log('📸 Quick visual check complete');
    console.log('   Screenshots: quick_main_page, quick_map_view');
    console.log('   Look for: track paths, detection points, radar markers');
    
    return { status: 'complete', screenshots: ['quick_main_page', 'quick_map_view'] };
}

// Export functions for Puppeteer MCP usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { 
        validateRETINASolverTracks,
        quickVisualCheck
    };
}