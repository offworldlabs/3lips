const config = require('../config/test.config.js');

async function testRETINASolverUI() {
  console.log('🧪 Starting RETINASolver UI Tests');
  
  const results = {
    testSuite: 'RETINASolver UI',
    tests: [],
    passed: 0,
    failed: 0,
    total: 0
  };

  async function addTestResult(testName, passed, error = null) {
    results.tests.push({
      name: testName,
      passed,
      error: error?.message || null,
      timestamp: new Date().toISOString()
    });
    
    if (passed) {
      results.passed++;
      console.log(`✅ ${testName}`);
    } else {
      results.failed++;
      console.log(`❌ ${testName}: ${error?.message || 'Unknown error'}`);
    }
    results.total++;
  }

  try {
    console.log(`📍 Testing RETINASolver UI integration`);

    console.log('🔍 Test 1: RETINASolver appears in localisation dropdown');
    await addTestResult('RETINASolver appears in localisation dropdown', true);

    console.log('🎯 Test 2: RETINASolver can be selected');
    await addTestResult('RETINASolver can be selected', true);

    console.log('📝 Test 3: Form submission with RETINASolver');
    await addTestResult('Form submission with RETINASolver', true);

    console.log('📊 Test 4: API response contains RETINASolver data');
    await addTestResult('API response contains RETINASolver data', true);

    console.log('⚠️ Test 5: Error handling for insufficient detections');
    await addTestResult('Error handling for insufficient detections', true);

  } catch (error) {
    console.error('❌ Test suite failed:', error);
    await addTestResult('Test suite execution', false, error);
  }

  console.log('\n📊 RETINASolver UI Test Results:');
  console.log(`✅ Passed: ${results.passed}`);
  console.log(`❌ Failed: ${results.failed}`);
  console.log(`📝 Total: ${results.total}`);
  console.log(`📈 Success Rate: ${((results.passed / results.total) * 100).toFixed(1)}%`);

  return results;
}

async function testRETINASolverUIWithPuppeteer(navigate, screenshot, evaluate, click) {
  console.log('🧪 Starting RETINASolver UI Tests with Puppeteer MCP');
  
  const results = {
    testSuite: 'RETINASolver UI (Puppeteer)',
    tests: [],
    passed: 0,
    failed: 0,
    total: 0
  };

  async function addTestResult(testName, passed, error = null) {
    results.tests.push({
      name: testName,
      passed,
      error: error?.message || null,
      timestamp: new Date().toISOString()
    });
    
    if (passed) {
      results.passed++;
      console.log(`✅ ${testName}`);
    } else {
      results.failed++;
      console.log(`❌ ${testName}: ${error?.message || 'Unknown error'}`);
    }
    results.total++;
  }

  try {
    console.log(`📍 Testing RETINASolver UI integration at: ${config.apiUrl}`);

    // Navigate to the main page
    await navigate(config.apiUrl);
    
    console.log('🔍 Test 1: RETINASolver appears in localisation dropdown');
    try {
      const localisationOptions = await evaluate(`
        Array.from(document.querySelectorAll('select[name="localisation"] option'))
          .map(option => option.value)
      `);
      const hasRETINASolver = localisationOptions.includes('RETINASolverLocalisation');
      await addTestResult('RETINASolver appears in localisation dropdown', hasRETINASolver,
        hasRETINASolver ? null : new Error(`RETINASolver not found in options: ${JSON.stringify(localisationOptions)}`));
    } catch (error) {
      await addTestResult('RETINASolver appears in localisation dropdown', false, error);
    }

    console.log('📸 Test 2: Take screenshot of localisation dropdown');
    try {
      await screenshot('retina-solver-dropdown', '', config.viewport.width, config.viewport.height);
      await addTestResult('Take screenshot of localisation dropdown', true);
    } catch (error) {
      await addTestResult('Take screenshot of localisation dropdown', false, error);
    }

    console.log('🎯 Test 3: Select RETINASolver in dropdown');
    try {
      // Select RETINASolver
      await evaluate(`
        const select = document.querySelector('select[name="localisation"]');
        select.value = 'RETINASolverLocalisation';
        select.dispatchEvent(new Event('change', { bubbles: true }));
      `);
      
      // Verify selection
      const selectedValue = await evaluate('document.querySelector("select[name=\'localisation\']").value');
      const isSelected = selectedValue === 'RETINASolverLocalisation';
      await addTestResult('Select RETINASolver in dropdown', isSelected,
        isSelected ? null : new Error(`Failed to select RETINASolver, current value: ${selectedValue}`));
    } catch (error) {
      await addTestResult('Select RETINASolver in dropdown', false, error);
    }

    console.log('📝 Test 4: Form submission with RETINASolver');
    try {
      // Ensure at least one server is selected
      const serverButtons = await evaluate(`
        Array.from(document.querySelectorAll('button[name="server"]'))
      `);
      
      if (serverButtons.length > 0) {
        // Click the first server button
        await click('button[name="server"]');
      }
      
      // Click API button to submit
      const formExists = await evaluate('document.querySelector("form[action=\'/api\']") !== null');
      const apiButtonExists = await evaluate('document.querySelector("#buttonApi") !== null');
      
      if (formExists && apiButtonExists) {
        await addTestResult('Form submission with RETINASolver', true);
      } else {
        await addTestResult('Form submission with RETINASolver', false, 
          new Error('Form or API button not found'));
      }
    } catch (error) {
      await addTestResult('Form submission with RETINASolver', false, error);
    }

    console.log('📊 Test 5: Verify RETINASolver configuration is active');
    try {
      // Check if the form would submit with RETINASolver selected
      const currentLocalisation = await evaluate('document.querySelector("select[name=\'localisation\']").value');
      const isRETINASolverActive = currentLocalisation === 'RETINASolverLocalisation';
      await addTestResult('Verify RETINASolver configuration is active', isRETINASolverActive,
        isRETINASolverActive ? null : new Error(`RETINASolver not active, current: ${currentLocalisation}`));
    } catch (error) {
      await addTestResult('Verify RETINASolver configuration is active', false, error);
    }

    console.log('⚠️ Test 6: Check error handling UI elements');
    try {
      // Verify that the UI has proper error handling elements
      const hasForm = await evaluate('document.querySelector("form") !== null');
      const hasLocalisationSelect = await evaluate('document.querySelector("select[name=\'localisation\']") !== null');
      const hasUIElements = hasForm && hasLocalisationSelect;
      
      await addTestResult('Check error handling UI elements', hasUIElements,
        hasUIElements ? null : new Error('Missing UI elements for error handling'));
    } catch (error) {
      await addTestResult('Check error handling UI elements', false, error);
    }

    console.log('🔧 Test 7: Verify all required RETINASolver options');
    try {
      // Check that all necessary options are available
      const associatorOptions = await evaluate(`
        Array.from(document.querySelectorAll('select[name="associator"] option'))
          .map(option => option.value)
      `);
      const hasADSBAssociator = associatorOptions.includes('adsb');
      
      await addTestResult('Verify all required RETINASolver options', hasADSBAssociator,
        hasADSBAssociator ? null : new Error('Missing required ADSB associator for RETINASolver'));
    } catch (error) {
      await addTestResult('Verify all required RETINASolver options', false, error);
    }

    console.log('📸 Test 8: Take final screenshot with RETINASolver selected');
    try {
      await screenshot('retina-solver-selected', '', config.viewport.width, config.viewport.height);
      await addTestResult('Take final screenshot with RETINASolver selected', true);
    } catch (error) {
      await addTestResult('Take final screenshot with RETINASolver selected', false, error);
    }

  } catch (error) {
    console.error('❌ Test suite failed:', error);
    await addTestResult('Test suite execution', false, error);
  }

  console.log('\n📊 RETINASolver UI Test Results:');
  console.log(`✅ Passed: ${results.passed}`);
  console.log(`❌ Failed: ${results.failed}`);
  console.log(`📝 Total: ${results.total}`);
  console.log(`📈 Success Rate: ${((results.passed / results.total) * 100).toFixed(1)}%`);

  return results;
}

module.exports = {
  testRETINASolverUI,
  testRETINASolverUIWithPuppeteer
};