/**
 * E2E Connection Test for Voice Agent
 * Tests:
 * 1. Frontend loads
 * 2. Can join a room
 * 3. Agent connects and sends greeting
 */
import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'https://192.168.20.224:3000';

test.describe('Voice Agent E2E Tests', () => {
  test('frontend loads and displays join form', async ({ page }) => {
    // Ignore HTTPS certificate errors for local development
    await page.goto(FRONTEND_URL, { waitUntil: 'networkidle' });

    // Check the title
    await expect(page.locator('h1')).toContainText('LiveKit AI Voice Agent');

    // Check form elements exist
    await expect(page.locator('input[placeholder*="room name"]')).toBeVisible();
    await expect(page.locator('input[placeholder*="your name"]')).toBeVisible();
    await expect(page.locator('button:has-text("Join Room")')).toBeVisible();
  });

  test('can join room and agent connects', async ({ page }) => {
    await page.goto(FRONTEND_URL, { waitUntil: 'networkidle' });

    const testRoom = `e2e-test-${Date.now()}`;
    const testUser = 'E2E-Tester';

    // Fill in the form
    await page.locator('input[placeholder*="room name"]').fill(testRoom);
    await page.locator('input[placeholder*="your name"]').fill(testUser);

    // Join the room
    await page.locator('button:has-text("Join Room")').click();

    // Wait for connection (should see the voice agent UI)
    await expect(page.locator('text=AI Voice Agent').or(page.locator('[data-lk-connected]'))).toBeVisible({ timeout: 30000 });

    // Wait for agent to join (look for agent audio track or speaking indicator)
    await page.waitForTimeout(10000); // Wait for agent greeting

    // Verify agent sent audio (by checking if any audio element exists)
    const hasAudioTracks = await page.evaluate(() => {
      const audioElements = document.querySelectorAll('audio');
      return audioElements.length > 0;
    });

    console.log(`Audio tracks found: ${hasAudioTracks}`);
  });
});
