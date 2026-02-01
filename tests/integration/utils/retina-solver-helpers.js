/**
 * Helper utilities for RETINASolver integration tests
 */

/**
 * Wait for synthetic aircraft data to be available
 * @param {Function} navigate - Puppeteer navigate function
 * @param {Function} evaluate - Puppeteer evaluate function
 * @param {number} maxAttempts - Maximum number of attempts
 * @returns {Object|null} Aircraft data or null if not available
 */
async function waitForSyntheticAircraft(navigate, evaluate, maxAttempts = 30) {
  console.log('⏳ Waiting for synthetic aircraft data...');
  
  for (let i = 0; i < maxAttempts; i++) {
    try {
      await navigate('http://localhost:5001/data/aircraft.json');
      const data = await evaluate('JSON.parse(document.body.textContent)');
      
      if (data && data.aircraft && data.aircraft.length > 0) {
        console.log(`✅ Found ${data.aircraft.length} aircraft`);
        return data;
      }
    } catch (error) {
      console.log(`  Attempt ${i + 1}/${maxAttempts}: ${error.message}`);
    }
    
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  console.log('❌ No aircraft data found');
  return null;
}

/**
 * Verify RETINASolver output format
 * @param {Object} output - RETINASolver output data
 * @returns {Object} Validation result with passed boolean and errors array
 */
function verifyRETINASolverOutput(output) {
  const errors = [];
  let passed = true;
  
  if (!output) {
    errors.push('Output is null or undefined');
    return { passed: false, errors };
  }
  
  // Check for expected output structure
  if (typeof output === 'string') {
    // String output is acceptable (might be JSON string)
    try {
      const parsed = JSON.parse(output);
      output = parsed;
    } catch {
      // Not JSON, but still valid string output
      return { passed: true, errors: [] };
    }
  }
  
  // Check for detection data
  if (output.detections) {
    if (!Array.isArray(output.detections)) {
      errors.push('detections is not an array');
      passed = false;
    }
  }
  
  // Check for data field
  if (output.data) {
    if (typeof output.data !== 'object') {
      errors.push('data is not an object');
      passed = false;
    }
  }
  
  // Check for error field
  if (output.error) {
    errors.push(`Error in output: ${output.error}`);
    passed = false;
  }
  
  return { passed, errors };
}

/**
 * Calculate position accuracy between two points
 * @param {Object} actual - Actual position {lat, lon, alt}
 * @param {Object} expected - Expected position {lat, lon, alt}
 * @returns {Object} Accuracy metrics
 */
function calculatePositionAccuracy(actual, expected) {
  if (!actual || !expected) {
    return {
      valid: false,
      error: 'Missing position data'
    };
  }
  
  // Haversine distance formula
  const R = 6371000; // Earth radius in meters
  const phi1 = actual.lat * Math.PI / 180;
  const phi2 = expected.lat * Math.PI / 180;
  const deltaPhi = (expected.lat - actual.lat) * Math.PI / 180;
  const deltaLambda = (expected.lon - actual.lon) * Math.PI / 180;
  
  const a = Math.sin(deltaPhi/2) * Math.sin(deltaPhi/2) +
            Math.cos(phi1) * Math.cos(phi2) *
            Math.sin(deltaLambda/2) * Math.sin(deltaLambda/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  
  const horizontalError = R * c;
  const verticalError = Math.abs((actual.alt || 0) - (expected.alt || 0));
  
  return {
    valid: true,
    horizontalError: horizontalError,
    verticalError: verticalError,
    totalError: Math.sqrt(horizontalError * horizontalError + verticalError * verticalError),
    details: {
      actualLat: actual.lat,
      actualLon: actual.lon,
      actualAlt: actual.alt,
      expectedLat: expected.lat,
      expectedLon: expected.lon,
      expectedAlt: expected.alt
    }
  };
}

/**
 * Wait for all services to be ready
 * @param {Function} navigate - Puppeteer navigate function
 * @param {Function} evaluate - Puppeteer evaluate function
 * @returns {Object} Status of each service
 */
async function waitForAllServices(navigate, evaluate) {
  console.log('🔄 Checking all services...');
  
  const services = {
    syntheticAdsb: false,
    adsb2dd: false,
    radar1: false,
    radar2: false,
    radar3: false,
    api: false
  };
  
  // Check synthetic ADS-B
  try {
    await navigate('http://localhost:5001/data/aircraft.json');
    const loaded = await evaluate('document.readyState === "complete"');
    services.syntheticAdsb = loaded;
  } catch (error) {
    console.log('❌ Synthetic ADS-B not ready');
  }
  
  // Check ADSB2DD
  try {
    await navigate('http://localhost:49155/api/status');
    const loaded = await evaluate('document.readyState === "complete"');
    services.adsb2dd = loaded;
  } catch (error) {
    console.log('❌ ADSB2DD not ready');
  }
  
  // Check radars
  const radarPorts = [49158, 49159, 49160];
  for (let i = 0; i < radarPorts.length; i++) {
    try {
      await navigate(`http://localhost:${radarPorts[i]}/api/config`);
      const loaded = await evaluate('document.readyState === "complete"');
      services[`radar${i + 1}`] = loaded;
    } catch (error) {
      console.log(`❌ Radar ${i + 1} not ready`);
    }
  }
  
  // Check 3lips API
  try {
    await navigate('http://localhost:8080');
    const loaded = await evaluate('document.readyState === "complete"');
    services.api = loaded;
  } catch (error) {
    console.log('❌ 3lips API not ready');
  }
  
  const allReady = Object.values(services).every(status => status === true);
  console.log(allReady ? '✅ All services ready!' : '⚠️ Some services not ready');
  
  return services;
}

/**
 * Configure RETINASolver in the UI
 * @param {Function} evaluate - Puppeteer evaluate function
 * @param {Function} click - Puppeteer click function
 * @returns {boolean} Success status
 */
async function configureRETINASolver(evaluate, click) {
  try {
    // Select RETINASolver
    await evaluate(`
      const select = document.querySelector('select[name="localisation"]');
      if (select) {
        select.value = 'RETINASolverLocalisation';
        select.dispatchEvent(new Event('change', { bubbles: true }));
      }
    `);
    
    // Select all servers
    await evaluate(`
      const serverButtons = document.querySelectorAll('button[name="server"]');
      serverButtons.forEach(btn => {
        if (!btn.classList.contains('active')) {
          btn.click();
        }
      });
    `);
    
    // Verify configuration
    const isConfigured = await evaluate(`
      const locSelect = document.querySelector('select[name="localisation"]');
      const activeServers = document.querySelectorAll('button[name="server"].active');
      locSelect && locSelect.value === 'RETINASolverLocalisation' && activeServers.length >= 3
    `);
    
    return isConfigured;
  } catch (error) {
    console.error('Failed to configure RETINASolver:', error);
    return false;
  }
}

module.exports = {
  waitForSyntheticAircraft,
  verifyRETINASolverOutput,
  calculatePositionAccuracy,
  waitForAllServices,
  configureRETINASolver
};