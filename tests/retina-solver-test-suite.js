/**
 * Complete RETINASolver Test Suite
 * 
 * This file provides a comprehensive test suite for RETINASolver integration
 * with the 3lips system. Run this with Claude Code Puppeteer MCP.
 */

// Import all test modules
const { testRETINASolverUIWithPuppeteer } = require('./integration/tests/mvp-retina-solver.test.js');
const { testRETINASolverPipelineWithPuppeteer } = require('./integration/tests/retina-solver-pipeline.test.js');
const { testRETINASolverE2EWithPuppeteer } = require('./integration/tests/e2e-retina-solver.test.js');
const { waitForAllServices } = require('./integration/utils/retina-solver-helpers.js');

async function runRETINASolverTestSuite(navigate, screenshot, evaluate, click) {
  console.log('🚀 Starting Complete RETINASolver Test Suite');
  console.log('=====================================');
  
  const suiteResults = {
    testSuite: 'Complete RETINASolver Integration',
    startTime: Date.now(),
    suites: [],
    totalPassed: 0,
    totalFailed: 0,
    totalTests: 0
  };

  // Check services first
  console.log('\n🔍 Pre-flight: Checking all services...');
  const serviceStatus = await waitForAllServices(navigate, evaluate);
  const allServicesReady = Object.values(serviceStatus).every(status => status === true);
  
  if (!allServicesReady) {
    console.log('❌ Some services are not ready. Please run:');
    console.log('   docker compose -f tests/docker-compose.retina.yml up -d');
    console.log('   ./tests/verify-retina-services.sh');
    return;
  }
  
  console.log('✅ All services are ready!\n');

  try {
    // Run UI Integration Tests
    console.log('🧪 Running UI Integration Tests...');
    console.log('-----------------------------------');
    const uiResults = await testRETINASolverUIWithPuppeteer(navigate, screenshot, evaluate, click);
    suiteResults.suites.push(uiResults);
    suiteResults.totalPassed += uiResults.passed;
    suiteResults.totalFailed += uiResults.failed;
    suiteResults.totalTests += uiResults.total;
    
    console.log('\n⏳ Waiting before next test suite...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Run Pipeline Integration Tests
    console.log('\n🧪 Running Pipeline Integration Tests...');
    console.log('---------------------------------------');
    const pipelineResults = await testRETINASolverPipelineWithPuppeteer(navigate, screenshot, evaluate, click);
    suiteResults.suites.push(pipelineResults);
    suiteResults.totalPassed += pipelineResults.passed;
    suiteResults.totalFailed += pipelineResults.failed;
    suiteResults.totalTests += pipelineResults.total;
    
    console.log('\n⏳ Waiting before next test suite...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Run End-to-End Tests
    console.log('\n🧪 Running End-to-End Tests...');
    console.log('-----------------------------');
    const e2eResults = await testRETINASolverE2EWithPuppeteer(navigate, screenshot, evaluate, click);
    suiteResults.suites.push(e2eResults);
    suiteResults.totalPassed += e2eResults.passed;
    suiteResults.totalFailed += e2eResults.failed;
    suiteResults.totalTests += e2eResults.total;
    
  } catch (error) {
    console.error('❌ Test suite execution failed:', error);
  }

  // Final results
  const duration = (Date.now() - suiteResults.startTime) / 1000;
  const successRate = (suiteResults.totalPassed / suiteResults.totalTests) * 100;
  
  console.log('\n📊 FINAL RETINA SOLVER TEST RESULTS');
  console.log('===================================');
  console.log(`✅ Total Passed: ${suiteResults.totalPassed}`);
  console.log(`❌ Total Failed: ${suiteResults.totalFailed}`);
  console.log(`📝 Total Tests: ${suiteResults.totalTests}`);
  console.log(`📈 Success Rate: ${successRate.toFixed(1)}%`);
  console.log(`⏱️ Total Duration: ${duration.toFixed(1)}s`);
  
  console.log('\n📋 Test Suite Breakdown:');
  suiteResults.suites.forEach(suite => {
    const suiteSuccess = (suite.passed / suite.total) * 100;
    console.log(`  ${suite.testSuite}: ${suite.passed}/${suite.total} (${suiteSuccess.toFixed(1)}%)`);
  });
  
  if (successRate === 100) {
    console.log('\n🎉 All RETINASolver integration tests passed!');
    console.log('The RETINASolver is fully integrated and working correctly.');
  } else {
    console.log('\n⚠️ Some tests failed. Please review the results above.');
  }
  
  return suiteResults;
}

// Export for use with Puppeteer MCP
module.exports = {
  runRETINASolverTestSuite
};

// If running standalone, provide instructions
if (require.main === module) {
  console.log('🧪 RETINASolver Test Suite');
  console.log('==========================');
  console.log('');
  console.log('This test suite requires Claude Code with Puppeteer MCP to run.');
  console.log('');
  console.log('Setup:');
  console.log('1. Start the RETINA test environment:');
  console.log('   docker compose -f tests/docker-compose.retina.yml up -d');
  console.log('');
  console.log('2. Verify all services are running:');
  console.log('   ./tests/verify-retina-services.sh');
  console.log('');
  console.log('3. Run this test suite in Claude Code with Puppeteer MCP:');
  console.log('   Load this file and call runRETINASolverTestSuite()');
  console.log('');
  console.log('Test Coverage:');
  console.log('- UI Integration: RETINASolver dropdown selection and form submission');
  console.log('- Pipeline Integration: Data flow from synthetic ADS-B to RETINASolver');
  console.log('- End-to-End: Complete aircraft tracking and visualization');
}