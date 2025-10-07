import * as WebBrowser from 'expo-web-browser';

/**
 * Open a URL in the user's default browser (popup/tab).
 * Returns the result from expo-web-browser or null on failure.
 */
export async function openInBrowser(url: string) {
  try {
    const result = await WebBrowser.openBrowserAsync(url);
    return result;
  } catch (err) {
    // Don't throw for caller convenience; log and return null so UI can degrade gracefully.
    // eslint-disable-next-line no-console
    console.warn('[openInBrowser] failed to open url', url, err);
    return null;
  }
}

/**
 * Open an authentication popup (useful for OAuth flows).
 * On native this will open the system browser and listen for the redirect.
 * On web this typically opens a new tab/window.
 * Returns an object describing the session outcome.
 */
export async function openAuthPopup(authUrl: string, redirectUrl?: string) {
  try {
    const result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUrl);
    return result;
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[openAuthPopup] failed to open auth session', authUrl, err);
    return null;
  }
}

export default {
  openInBrowser,
  openAuthPopup,
};
