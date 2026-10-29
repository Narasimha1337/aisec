### **Unvalidated Redirects and Forwards**

| **Aspect** | **Details** |
|---|---|
| **Description** | Applications that redirect (client-side, 30x) or forward (server-side dispatch) to a destination taken from user input without validation can send users to malicious sites or bypass access controls on internal targets. |
| **Conditions to be Vulnerable** | - The redirect/forward target comes from a request parameter or header. <br> - No allowlist validation of the destination. <br> - Forwards reuse a path that skips authorization checks on the target resource. |
| **Where to Find** | - Redirect params (`?url=`, `?next=`, `?dest=`) and post-login landing logic. <br> - Server-side forwards (e.g., `RequestDispatcher.forward`, MVC forwards) driven by a parameter. |
| **Common Exploits** | - Phishing via a trusted-domain link that redirects to an attacker site. <br> - Authorization bypass when a forward routes to a privileged page without re-checking access. |
| **Example** | Redirect: `https://app.com/go?url=https://evil.com`. Forward: `https://app.com/dispatch?page=admin/dashboard` forwards server-side to the admin view while skipping its access check. |
| **How to Test** | 1. Find parameters controlling navigation; test redirects to an external domain and inspect `Location`. <br> 2. For forwards, try routing to restricted pages and check whether authorization is re-evaluated. <br> 3. Apply encoding/`//` bypasses if filtered. Authorized targets only. |
| **Tools** | Burp Suite, OWASP ZAP, curl, ffuf |
| **Mitigation** | - Avoid user-controlled destinations; use server-side allowlists or token-to-URL maps. <br> - For forwards, enforce authorization on the target resource itself, not the entry route. <br> - Reject absolute/external URLs; warn on any off-site redirect. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP Cheat Sheet - Unvalidated Redirects and Forwards | https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html |
| OWASP WSTG - Testing for Client-side URL Redirect | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/04-Testing_for_Client-side_URL_Redirect |
| PortSwigger - DOM-based open redirection | https://portswigger.net/web-security/dom-based/open-redirection |
