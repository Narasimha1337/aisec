### **Session Fixation**

| **Aspect** | **Details** |
|---|---|
| **Description** | Session fixation lets an attacker set or predict a victim's session identifier before login, then reuse that identifier after the victim authenticates to hijack their session. The flaw is the failure to rotate the session ID at privilege change. |
| **Conditions to be Vulnerable** | - The session identifier is not regenerated on login. <br> - Session IDs can be supplied via URL, query parameter, or attacker-set cookie. <br> - The app accepts externally provided session tokens as valid. |
| **Where to Find** | - Authentication flows and any place a session token appears in the URL. <br> - Apps that accept a session cookie from an unauthenticated request and keep it post-login. |
| **Common Exploits** | - Planting a known session ID in the victim's browser, then using it after they log in. <br> - Distributing links with a fixed `;jsessionid=` to lock the victim onto an attacker-known session. |
| **Example** | Attacker visits the site, obtains `SESSIONID=ATTACKER123`, sends the victim `https://app.com/?SESSIONID=ATTACKER123`. After the victim logs in, the same ID remains valid, so the attacker is now authenticated as the victim. |
| **How to Test** | 1. Capture the pre-auth session cookie/value in Burp. <br> 2. Log in and compare the post-auth session ID to the pre-auth one. <br> 3. If unchanged, replay the old ID in a separate session to confirm authenticated access. Authorized accounts only. |
| **Tools** | Burp Suite, OWASP ZAP, browser dev tools, curl |
| **Mitigation** | - Regenerate the session identifier on login and on privilege elevation. <br> - Never accept session IDs from the URL; use `HttpOnly`, `Secure`, `SameSite` cookies. <br> - Bind sessions to attributes and expire them on logout/idle. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Session Fixation | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/03-Testing_for_Session_Fixation |
| OWASP Cheat Sheet - Session Management | https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html |
| PortSwigger - Session fixation | https://portswigger.net/kb/issues/00400600_session-fixation |
