### **Back Button Attack**

| **Aspect** | **Details** |
|---|---|
| **Description** | After a user logs out (or on a shared device), pressing the browser Back button or reopening cached pages reveals sensitive data or restores an authenticated view. This happens when the server lets responses be cached and does not fully invalidate the session. |
| **Conditions to be Vulnerable** | - Sensitive pages served with caching enabled. <br> - Session not invalidated server-side on logout. <br> - Missing `Cache-Control: no-store` on authenticated responses. |
| **Where to Find** | - Post-login dashboards, account pages, and transaction confirmation pages. <br> - Logout flows on shared or public computers. |
| **Common Exploits** | - Viewing cached private data after logout via Back navigation. <br> - Resubmitting forms or replaying actions from cached pages. <br> - Session restoration if the token remains valid server-side. |
| **Example** | A user logs out of a banking app on a public PC. The next person presses Back and the cached account summary page renders with balances still visible. |
| **How to Test** | 1. Log in, browse sensitive pages, then log out. <br> 2. Press the browser Back button and reload from cache (offline if needed). <br> 3. Check whether sensitive data renders and whether the old session token still works in Burp Repeater. |
| **Tools** | Burp Suite, OWASP ZAP, browser DevTools, curl |
| **Mitigation** | - Send `Cache-Control: no-store, no-cache` and `Pragma: no-cache` on authenticated pages. <br> - Invalidate the session server-side on logout. <br> - Avoid putting sensitive data in cacheable GET responses. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Logout Functionality | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/06-Testing_for_Logout_Functionality |
| OWASP Cheat Sheet - Session Management | https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html |
| MDN - Cache-Control | https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control |
