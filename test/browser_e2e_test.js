/**
 * Browser E2E Test for LiveKit Voice Agent
 * Automates real browser testing with detailed per-component latency measurement
 *
 * Usage: node test/browser_e2e_test.js
 */

const { chromium } = require('playwright');

const FRONTEND_URL = process.env.FRONTEND_URL || 'https://192.168.20.62:3000';

async function runE2ETest() {
    console.log('\n' + '='.repeat(70));
    console.log('Browser E2E Voice Agent Test - Per-Component Performance Capture');
    console.log('='.repeat(70) + '\n');
    console.log(`Target URL: ${FRONTEND_URL}\n`);

    const browser = await chromium.launch({
        headless: true,
        args: [
            '--use-fake-ui-for-media-stream',
            '--use-fake-device-for-media-stream',
            '--ignore-certificate-errors',
            '--allow-insecure-localhost',
            '--autoplay-policy=no-user-gesture-required',
            '--no-sandbox',
        ],
    });

    const context = await browser.newContext({
        ignoreHTTPSErrors: true,
        permissions: ['microphone'],
    });

    const page = await context.newPage();

    // Detailed per-component metrics
    const metrics = {
        // Connection Phase
        pageLoad: null,
        tokenFetch: null,
        websocketConnect: null,
        roomJoined: null,
        agentJoined: null,

        // Per-Component Latencies
        components: {
            stt: [],       // Speech-to-Text latencies
            llm: [],       // LLM inference latencies
            tts: [],       // Text-to-Speech latencies
            total: [],     // Total round-trip latencies
        },

        // Transcript Events
        transcripts: {
            userMessages: 0,
            agentMessages: 0,
            firstUserTranscript: null,
            firstAgentResponse: null,
        },

        // Network Metrics
        network: {
            wsMessages: 0,
            dataChannelMessages: 0,
            bytesReceived: 0,
        },

        // Performance Timeline
        timeline: [],

        errors: [],
    };

    // Helper to add timeline event
    const addTimelineEvent = (event, details = {}) => {
        const entry = {
            time: Date.now(),
            elapsed: metrics.timeline.length > 0 ? Date.now() - metrics.timeline[0].time : 0,
            event,
            ...details,
        };
        metrics.timeline.push(entry);
        console.log(`[${String(entry.elapsed).padStart(6)}ms] ${event}${details.latency ? ` (${details.latency}ms)` : ''}`);
    };

    // Capture console logs for component-level latency
    page.on('console', msg => {
        const text = msg.text();

        // Capture component-specific latencies from console
        if (text.includes('[LATENCY]') || text.includes('[PERF]')) {
            console.log(`  [BROWSER] ${text}`);

            // Parse component latencies
            const sttMatch = text.match(/STT[:\s]+(\d+)\s*ms/i);
            const llmMatch = text.match(/LLM[:\s]+(\d+)\s*ms/i);
            const ttsMatch = text.match(/TTS[:\s]+(\d+)\s*ms/i);
            const totalMatch = text.match(/Total[:\s]+(\d+)\s*ms/i) || text.match(/(\d+)\s*ms/);

            if (sttMatch) metrics.components.stt.push(parseInt(sttMatch[1]));
            if (llmMatch) metrics.components.llm.push(parseInt(llmMatch[1]));
            if (ttsMatch) metrics.components.tts.push(parseInt(ttsMatch[1]));
            if (totalMatch && !sttMatch && !llmMatch && !ttsMatch) {
                metrics.components.total.push(parseInt(totalMatch[1]));
            }
        }

        // Capture transcript events
        if (text.includes('transcript') || text.includes('SAID:')) {
            if (text.includes('user') || text.includes('User')) {
                metrics.transcripts.userMessages++;
                if (!metrics.transcripts.firstUserTranscript) {
                    metrics.transcripts.firstUserTranscript = Date.now();
                    addTimelineEvent('First user transcript');
                }
            }
            if (text.includes('agent') || text.includes('Agent') || text.includes('Trinity')) {
                metrics.transcripts.agentMessages++;
                if (!metrics.transcripts.firstAgentResponse) {
                    metrics.transcripts.firstAgentResponse = Date.now();
                    addTimelineEvent('First agent response');
                }
            }
        }
    });

    // Capture network events for WebSocket metrics
    page.on('request', request => {
        const url = request.url();
        if (url.includes('rtc') || url.includes('ws') || url.includes('token')) {
            addTimelineEvent(`Request: ${request.method()} ${url.split('?')[0]}`);
        }
    });

    page.on('response', response => {
        const url = response.url();
        if (url.includes('token')) {
            metrics.tokenFetch = Date.now() - metrics.timeline[0]?.time;
            addTimelineEvent('Token received', { latency: metrics.tokenFetch });
        }
    });

    page.on('pageerror', error => {
        metrics.errors.push(error.message);
        addTimelineEvent(`ERROR: ${error.message}`);
    });

    try {
        // ====== PHASE 1: Page Load ======
        console.log('\n--- PHASE 1: Page Load ---');
        addTimelineEvent('Test started');
        const startTime = Date.now();

        await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
        metrics.pageLoad = Date.now() - startTime;
        addTimelineEvent('Page DOM loaded', { latency: metrics.pageLoad });

        // Wait for React to mount
        await page.waitForFunction(() => document.querySelectorAll('input').length >= 2, { timeout: 10000 });
        addTimelineEvent('React mounted');

        // ====== PHASE 2: Join Room ======
        console.log('\n--- PHASE 2: Join Room ---');
        const roomName = `e2e-perf-${Date.now()}`;

        const inputs = await page.$$('input');
        if (inputs.length >= 2) {
            await inputs[0].click();
            await inputs[0].fill(roomName);
            await inputs[1].click();
            await inputs[1].fill('E2E-Tester');
        }
        addTimelineEvent(`Form filled: room=${roomName}`);

        const joinTime = Date.now();
        await page.click('button:has-text("Join Room")');
        addTimelineEvent('Join button clicked');

        // ====== PHASE 3: Connection Establishment ======
        console.log('\n--- PHASE 3: Connection ---');

        // Wait for room UI
        await page.waitForFunction(() => {
            return document.body.innerText.includes('Trinity AI Voice Agent') ||
                   document.body.innerText.includes('Disconnect') ||
                   document.body.innerText.includes('Listening');
        }, { timeout: 20000 });

        metrics.roomJoined = Date.now() - joinTime;
        addTimelineEvent('Room connected', { latency: metrics.roomJoined });

        // ====== PHASE 4: Agent Detection ======
        console.log('\n--- PHASE 4: Agent Detection ---');

        try {
            await page.waitForFunction(() => {
                return document.body.innerText.includes('Agent') ||
                       document.body.innerText.includes('speaking') ||
                       document.querySelectorAll('[class*="transcript"]').length > 0;
            }, { timeout: 15000 });

            metrics.agentJoined = Date.now() - joinTime;
            addTimelineEvent('Agent joined', { latency: metrics.agentJoined });
        } catch {
            addTimelineEvent('Agent detection timeout');
        }

        // ====== PHASE 5: Greeting Detection ======
        console.log('\n--- PHASE 5: Greeting Detection ---');

        try {
            await page.waitForFunction(() => {
                const text = document.body.innerText;
                return text.includes('Hello') ||
                       text.includes('Trinity') ||
                       text.includes('assistant') ||
                       text.toLowerCase().includes('hi there') ||
                       document.querySelectorAll('[class*="transcript"] > div').length > 0;
            }, { timeout: 20000 });

            addTimelineEvent('Greeting detected');
        } catch {
            addTimelineEvent('Greeting detection timeout');
        }

        // ====== PHASE 6: Monitor Performance ======
        console.log('\n--- PHASE 6: Performance Monitoring (20s) ---');

        // Inject performance collector into page
        await page.evaluate(() => {
            window.__perfMetrics = {
                stt: [],
                llm: [],
                tts: [],
                total: [],
            };

            // Listen for data channel messages
            const origRTCDataChannel = window.RTCDataChannel;
            if (origRTCDataChannel) {
                const origSend = origRTCDataChannel.prototype.send;
                origRTCDataChannel.prototype.send = function(data) {
                    console.log('[PERF] DataChannel send:', typeof data === 'string' ? data.substring(0, 100) : 'binary');
                    return origSend.apply(this, arguments);
                };
            }
        });

        // Collect metrics for 20 seconds
        for (let i = 0; i < 4; i++) {
            await page.waitForTimeout(5000);

            const uiMetrics = await page.evaluate(() => {
                const text = document.body.innerText;

                // Parse all visible latency metrics
                const metrics = {
                    responseTime: null,
                    avgTime: null,
                    sttTime: null,
                    llmTime: null,
                    ttsTime: null,
                    transcriptCount: 0,
                };

                // Extract response times from UI
                const responseMatch = text.match(/Response Time:\s*([\d.]+)s/);
                const avgMatch = text.match(/Avg[^:]*:\s*([\d.]+)s/);
                const sttMatch = text.match(/STT[^:]*:\s*([\d.]+)(?:s|ms)/i);
                const llmMatch = text.match(/LLM[^:]*:\s*([\d.]+)(?:s|ms)/i);
                const ttsMatch = text.match(/TTS[^:]*:\s*([\d.]+)(?:s|ms)/i);

                if (responseMatch) metrics.responseTime = parseFloat(responseMatch[1]) * 1000;
                if (avgMatch) metrics.avgTime = parseFloat(avgMatch[1]) * 1000;
                if (sttMatch) {
                    const val = parseFloat(sttMatch[1]);
                    metrics.sttTime = sttMatch[0].includes('ms') ? val : val * 1000;
                }
                if (llmMatch) {
                    const val = parseFloat(llmMatch[1]);
                    metrics.llmTime = llmMatch[0].includes('ms') ? val : val * 1000;
                }
                if (ttsMatch) {
                    const val = parseFloat(ttsMatch[1]);
                    metrics.ttsTime = ttsMatch[0].includes('ms') ? val : val * 1000;
                }

                metrics.transcriptCount = document.querySelectorAll('[class*="transcript"] > div').length;

                return metrics;
            });

            // Record component metrics
            if (uiMetrics.sttTime) metrics.components.stt.push(uiMetrics.sttTime);
            if (uiMetrics.llmTime) metrics.components.llm.push(uiMetrics.llmTime);
            if (uiMetrics.ttsTime) metrics.components.tts.push(uiMetrics.ttsTime);
            if (uiMetrics.responseTime) metrics.components.total.push(uiMetrics.responseTime);

            addTimelineEvent(`Sample ${i + 1}/4: ${uiMetrics.transcriptCount} transcripts`, {
                stt: uiMetrics.sttTime ? `${Math.round(uiMetrics.sttTime)}ms` : 'N/A',
                llm: uiMetrics.llmTime ? `${Math.round(uiMetrics.llmTime)}ms` : 'N/A',
                tts: uiMetrics.ttsTime ? `${Math.round(uiMetrics.ttsTime)}ms` : 'N/A',
            });
        }

        // ====== PHASE 7: Final Metrics Collection ======
        console.log('\n--- PHASE 7: Final Collection ---');

        // Get final state
        const finalState = await page.evaluate(() => {
            const text = document.body.innerText;
            return {
                pageContent: text.substring(0, 2000),
                hasDisconnect: text.includes('Disconnect'),
                hasTranscripts: document.querySelectorAll('[class*="transcript"]').length > 0,
                isConnected: text.includes('Listening') || text.includes('Agent'),
            };
        });

        addTimelineEvent(`Final state: connected=${finalState.isConnected}, transcripts=${finalState.hasTranscripts}`);

        // Screenshot
        await page.screenshot({ path: 'test/e2e_screenshot.png', fullPage: true });
        addTimelineEvent('Screenshot saved');

    } catch (error) {
        console.log(`\n[ERROR] ${error.message}`);
        metrics.errors.push(error.message);
        await page.screenshot({ path: 'test/e2e_error.png', fullPage: true });
        addTimelineEvent(`Test error: ${error.message}`);
    }

    // ====== RESULTS SUMMARY ======
    console.log('\n' + '='.repeat(70));
    console.log('E2E TEST RESULTS - PER-COMPONENT PERFORMANCE');
    console.log('='.repeat(70));

    // Connection Metrics
    console.log('\n📡 CONNECTION METRICS:');
    console.log(`  Page Load:         ${metrics.pageLoad ? metrics.pageLoad + 'ms' : 'N/A'}`);
    console.log(`  Token Fetch:       ${metrics.tokenFetch ? metrics.tokenFetch + 'ms' : 'N/A'}`);
    console.log(`  Room Joined:       ${metrics.roomJoined ? metrics.roomJoined + 'ms' : 'N/A'}`);
    console.log(`  Agent Joined:      ${metrics.agentJoined ? metrics.agentJoined + 'ms' : 'N/A'}`);

    // Component Latencies
    console.log('\n⚡ COMPONENT LATENCIES:');

    const calcStats = (arr) => {
        if (arr.length === 0) return { avg: null, min: null, max: null };
        return {
            avg: Math.round(arr.reduce((a, b) => a + b, 0) / arr.length),
            min: Math.round(Math.min(...arr)),
            max: Math.round(Math.max(...arr)),
        };
    };

    const sttStats = calcStats(metrics.components.stt);
    const llmStats = calcStats(metrics.components.llm);
    const ttsStats = calcStats(metrics.components.tts);
    const totalStats = calcStats(metrics.components.total);

    console.log(`  STT (Speech-to-Text):`);
    console.log(`    Samples: ${metrics.components.stt.length}`);
    console.log(`    Avg: ${sttStats.avg !== null ? sttStats.avg + 'ms' : 'N/A'}`);
    console.log(`    Min: ${sttStats.min !== null ? sttStats.min + 'ms' : 'N/A'}`);
    console.log(`    Max: ${sttStats.max !== null ? sttStats.max + 'ms' : 'N/A'}`);

    console.log(`  LLM (Language Model):`);
    console.log(`    Samples: ${metrics.components.llm.length}`);
    console.log(`    Avg: ${llmStats.avg !== null ? llmStats.avg + 'ms' : 'N/A'}`);
    console.log(`    Min: ${llmStats.min !== null ? llmStats.min + 'ms' : 'N/A'}`);
    console.log(`    Max: ${llmStats.max !== null ? llmStats.max + 'ms' : 'N/A'}`);

    console.log(`  TTS (Text-to-Speech):`);
    console.log(`    Samples: ${metrics.components.tts.length}`);
    console.log(`    Avg: ${ttsStats.avg !== null ? ttsStats.avg + 'ms' : 'N/A'}`);
    console.log(`    Min: ${ttsStats.min !== null ? ttsStats.min + 'ms' : 'N/A'}`);
    console.log(`    Max: ${ttsStats.max !== null ? ttsStats.max + 'ms' : 'N/A'}`);

    console.log(`  TOTAL (Round-Trip):`);
    console.log(`    Samples: ${metrics.components.total.length}`);
    console.log(`    Avg: ${totalStats.avg !== null ? totalStats.avg + 'ms' : 'N/A'}`);
    console.log(`    Min: ${totalStats.min !== null ? totalStats.min + 'ms' : 'N/A'}`);
    console.log(`    Max: ${totalStats.max !== null ? totalStats.max + 'ms' : 'N/A'}`);

    // Transcript Metrics
    console.log('\n💬 TRANSCRIPT METRICS:');
    console.log(`  User Messages:     ${metrics.transcripts.userMessages}`);
    console.log(`  Agent Messages:    ${metrics.transcripts.agentMessages}`);

    // Performance Assessment
    console.log('\n📊 PERFORMANCE ASSESSMENT:');

    const assessComponent = (name, avgMs, thresholds) => {
        if (avgMs === null) return `  ${name}: No data`;
        if (avgMs < thresholds.good) return `  ${name}: ✅ GOOD (${avgMs}ms < ${thresholds.good}ms)`;
        if (avgMs < thresholds.acceptable) return `  ${name}: ⚠️  ACCEPTABLE (${avgMs}ms < ${thresholds.acceptable}ms)`;
        return `  ${name}: ❌ SLOW (${avgMs}ms >= ${thresholds.acceptable}ms)`;
    };

    console.log(assessComponent('STT', sttStats.avg, { good: 500, acceptable: 1000 }));
    console.log(assessComponent('LLM', llmStats.avg, { good: 1000, acceptable: 2000 }));
    console.log(assessComponent('TTS', ttsStats.avg, { good: 300, acceptable: 600 }));
    console.log(assessComponent('Total', totalStats.avg, { good: 2000, acceptable: 4000 }));

    // Errors
    if (metrics.errors.length > 0) {
        console.log('\n❌ ERRORS:');
        metrics.errors.forEach(e => console.log(`  - ${e}`));
    }

    // Timeline Summary
    console.log('\n📅 TIMELINE SUMMARY:');
    metrics.timeline.slice(-10).forEach(t => {
        console.log(`  [${String(t.elapsed).padStart(6)}ms] ${t.event}`);
    });

    console.log('\n' + '='.repeat(70));

    // Overall verdict
    const overallAvg = totalStats.avg || (sttStats.avg || 0) + (llmStats.avg || 0) + (ttsStats.avg || 0);
    if (overallAvg && overallAvg < 2000) {
        console.log('🎉 OVERALL: PASS - Latency under 2s target!');
    } else if (overallAvg && overallAvg < 4000) {
        console.log('⚠️  OVERALL: ACCEPTABLE - Latency 2-4s, optimization recommended');
    } else if (overallAvg) {
        console.log('❌ OVERALL: NEEDS WORK - Latency over 4s');
    } else {
        console.log('❓ OVERALL: INCONCLUSIVE - Insufficient latency data captured');
    }

    console.log('='.repeat(70) + '\n');

    await browser.close();
    return metrics;
}

runE2ETest()
    .then(m => process.exit(m.errors.length > 0 ? 1 : 0))
    .catch(e => { console.error('Crash:', e); process.exit(1); });
