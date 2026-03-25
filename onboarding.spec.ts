import { test, expect } from '@playwright/test';
import { authenticateTestUser, getTestToken } from './helpers/test-auth';

const APP_URL = 'http://localhost:3000';
const API_BASE_URL = process.env.API_BASE_URL ?? 'http://localhost:3001';

const TEST_COMPANY = 'testonboardingflow2';
const TEST_ROLE = `${TEST_COMPANY}:admin`;

const AUTH_OPTIONS = {
    email: 'vladimir+test2@supplied.eu',
    companyName: TEST_COMPANY,
    role: TEST_ROLE,
    permissions: ['read:earnings', 'write:earnings', 'read:payment_details', 'read:users'],
};

async function setCreationStatus(status: string): Promise<void> {
    const token = await getTestToken(AUTH_OPTIONS);
    const response = await fetch(`${API_BASE_URL}/api/v1/profile/root`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ creationStatus: status }),
    });

    if (!response.ok) {
        throw new Error(
            `Failed to set creationStatus to "${status}": ${response.status} ${response.statusText}`,
        );
    }
}

test.describe('Onboarding Wizard', () => {
    test.beforeEach(async ({ page }) => {
        await setCreationStatus('draft');
        await authenticateTestUser(page, AUTH_OPTIONS);

        // Inject route state so the sidebar reads showOnboarding=true on first load.
        // React Router v7 stores location state under `usr` in history.state.
        // Uses a sessionStorage flag so it only fires once (the wizard reload after
        // completion would otherwise re-trigger the popup).
        await page.addInitScript(() => {
            if (!sessionStorage.getItem('__e2e_onboarding_opened')) {
                sessionStorage.setItem('__e2e_onboarding_opened', '1');
                window.history.replaceState({ usr: { showOnboarding: true } }, '');
            }
        });

        await page.goto(APP_URL);
    });

    test('should display the welcome screen', async ({ page }) => {
        const wizardHeading = page.getByRole('heading', { name: 'Setup Your Account' });
        await expect(wizardHeading).toBeVisible({ timeout: 10_000 });

        const getStartedButton = page.getByRole('button', { name: 'Get started' });
        await expect(getStartedButton).toBeVisible();
    });

    test('should fill in contact information step', async ({ page }) => {
        const wizardHeading = page.getByRole('heading', { name: 'Setup Your Account' });
        await expect(wizardHeading).toBeVisible({ timeout: 10_000 });

        await page.getByRole('button', { name: 'Get started' }).click();

        await expect(page.getByText('Step 1 out of 2')).toBeVisible();

        const emailInput = page.locator('input#email');
        await expect(emailInput).toBeVisible();
        await emailInput.clear();
        await emailInput.fill('onboarding-test@supplied.eu');

        const phoneInput = page.locator('input#phone');
        await expect(phoneInput).toBeVisible();
        await phoneInput.clear();
        await phoneInput.fill('+31612345678');

        const supportEmailInput = page.locator('input#customerSupportEmail');
        await expect(supportEmailInput).toBeVisible();
        await supportEmailInput.clear();
        await supportEmailInput.fill('support-test@supplied.eu');

        const continueButton = page.getByRole('button', { name: 'Continue', exact: true });
        await expect(continueButton).toBeEnabled();
        await continueButton.click();

        await expect(page.getByText('Step 2 out of 2')).toBeVisible();
    });

    test('should fill in tax information step and finish', async ({ page }) => {
        const wizardHeading = page.getByRole('heading', { name: 'Setup Your Account' });
        await expect(wizardHeading).toBeVisible({ timeout: 10_000 });

        // Navigate through welcome + contact info to reach tax step
        await page.getByRole('button', { name: 'Get started' }).click();
        await expect(page.getByText('Step 1 out of 2')).toBeVisible();

        await page.locator('input#email').fill('onboarding-test@supplied.eu');
        await page.locator('input#phone').fill('+31612345678');
        await page.locator('input#customerSupportEmail').fill('support-test@supplied.eu');
        await page.getByRole('button', { name: 'Continue', exact: true }).click();

        // Tax Information step
        await expect(page.getByText('Step 2 out of 2')).toBeVisible();

        const legalNameInput = page.locator('input#platformOperatorName');
        await expect(legalNameInput).toBeVisible();
        await legalNameInput.clear();
        await legalNameInput.fill('Test Platform Operator B.V.');

        const countrySelect = page.locator('select#country');
        await expect(countrySelect).toBeVisible();
        await countrySelect.selectOption('NL');

        const tinInput = page.locator('input#businessTin');
        await expect(tinInput).toBeVisible();
        await tinInput.clear();
        await tinInput.fill('123456789');

        const streetInput = page.locator('input#address_street');
        await expect(streetInput).toBeVisible();
        await streetInput.clear();
        await streetInput.fill('Keizersgracht 100');

        const postalInput = page.locator('input#address_postal');
        await expect(postalInput).toBeVisible();
        await postalInput.clear();
        await postalInput.fill('1015AA');

        const cityInput = page.locator('input#address_city');
        await expect(cityInput).toBeVisible();
        await cityInput.clear();
        await cityInput.fill('Amsterdam');

        const addressCountrySelect = page.locator('select#address_country');
        await expect(addressCountrySelect).toBeVisible();
        await addressCountrySelect.selectOption('NL');

        await page.getByRole('button', { name: 'Continue', exact: true }).click();

        // Finish screen
        const finishButton = page.getByRole('button', { name: 'Finish' });
        await expect(finishButton).toBeVisible();
        await finishButton.click();
    });
});
