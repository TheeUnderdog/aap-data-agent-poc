/**
 * AuthManager — MSAL.js 2.x wrapper for Entra ID authentication.
 *
 * Depends on:
 *   - msal-browser 2.x loaded globally (window.msal)
 *   - window.APP_CONFIG with msalConfig and fabricScopes
 *
 * Usage:
 *   await window.AuthManager.initialize();
 *   await window.AuthManager.login();
 *   const token = await window.AuthManager.getToken();
 */
(function () {
    "use strict";

    var TAG = "[Auth]";

    /** @type {msal.PublicClientApplication} */
    var msalInstance = null;

    /** @type {string[]} */
    var scopes = [];

    // ── helpers ──────────────────────────────────────────────────────────

    function log()    { console.log.apply(console, [TAG].concat(Array.prototype.slice.call(arguments))); }
    function warn()   { console.warn.apply(console, [TAG].concat(Array.prototype.slice.call(arguments))); }
    function error()  { console.error.apply(console, [TAG].concat(Array.prototype.slice.call(arguments))); }

    function currentAccount() {
        if (!msalInstance) return null;
        var accounts = msalInstance.getAllAccounts();
        return accounts.length > 0 ? accounts[0] : null;
    }

    // ── public API ──────────────────────────────────────────────────────

    window.AuthManager = {

        /**
         * Create the MSAL instance and handle any returning redirect.
         * Must be called once on page load before any other method.
         */
        initialize: function () {
            if (!window.msal) throw new Error(TAG + " msal-browser not loaded. Include the CDN script before auth.js.");
            if (!window.APP_CONFIG) throw new Error(TAG + " APP_CONFIG not found. Load config before initializing auth.");

            var cfg = window.APP_CONFIG.msalConfig && window.APP_CONFIG.msalConfig.auth;
            if (!cfg || !cfg.clientId || cfg.clientId === 'YOUR_CLIENT_ID' || cfg.clientId === 'TODO_CLIENT_ID') {
                warn("MSAL not configured — skipping initialization.");
                return Promise.resolve();
            }

            if (!cfg.authority || cfg.authority.indexOf('YOUR_TENANT_ID') !== -1 || cfg.authority.indexOf('TODO_TENANT_ID') !== -1) {
                warn("MSAL authority not configured — skipping initialization.");
                return Promise.resolve();
            }

            scopes = window.APP_CONFIG.fabricScopes || [];
            msalInstance = new msal.PublicClientApplication(window.APP_CONFIG.msalConfig);

            return msalInstance.handleRedirectPromise()
                .then(function (response) {
                    if (response) {
                        msalInstance.setActiveAccount(response.account);
                        log("Redirect login succeeded for", response.account.username);
                    } else if (currentAccount()) {
                        msalInstance.setActiveAccount(currentAccount());
                    }
                })
                .catch(function (err) {
                    error("handleRedirectPromise failed:", err);
                });
        },

        /** Trigger interactive login via redirect. */
        login: function () {
            return msalInstance.loginRedirect({ scopes: scopes });
        },

        /** Sign out and redirect to the app origin. */
        logout: function () {
            if (!msalInstance) {
                warn("MSAL not initialized — skipping logout redirect.");
                return Promise.resolve();
            }

            return msalInstance.logoutRedirect({
                postLogoutRedirectUri: window.location.origin
            });
        },

        /**
         * Acquire an access token for the Fabric API.
         * Tries silent acquisition first; falls back to redirect on interaction-required errors.
         * @returns {Promise<string>} The access token.
         */
        getToken: function () {
            var account = currentAccount();
            if (!account) {
                warn("No account found — redirecting to login.");
                return this.login();
            }

            var request = { scopes: scopes, account: account };

            return msalInstance.acquireTokenSilent(request)
                .then(function (response) {
                    return response.accessToken;
                })
                .catch(function (err) {
                    if (err instanceof msal.InteractionRequiredAuthError) {
                        warn("Silent token failed (interaction required) — redirecting.");
                        return msalInstance.acquireTokenRedirect(request);
                    }
                    // Unrecoverable token error — clear cache and force re-login.
                    error("Token refresh failed — clearing cache:", err);
                    msalInstance.clearCache();
                    return msalInstance.loginRedirect({ scopes: scopes });
                });
        },

        /**
         * Return basic profile info for the signed-in user, or null.
         * @returns {{ name: string, username: string } | null}
         */
        getUser: function () {
            var account = currentAccount();
            if (!account) return null;
            return { name: account.name, username: account.username };
        },

        /** @returns {boolean} True when at least one cached account exists. */
        isAuthenticated: function () {
            return currentAccount() !== null;
        }
    };
})();
