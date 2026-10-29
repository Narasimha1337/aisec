### **Arbitrary Cookie Flags**

| **Aspect** | **Details** |
|---|---|
| **Description** | Cookies that hold session or sensitive data are set without the proper security flags (`Secure`, `HttpOnly`, `SameSite`). This lets cookies travel over cleartext, be read by JavaScript, or be sent on cross-site requests, enabling theft and CSRF. |
| **Conditions to be Vulnerable** | - Session cookie set without `HttpOnly`. <br> - Session cookie set without `Secure` on an HTTPS site. <br> - Missing or `None` value for `SameSite` without justification. |
| **Where to Find** | - `Set-Cookie` response headers after login or session creation. <br> - Authentication, session, and CSRF-token cookies. |
| **Common Exploits** | - Cookie theft via XSS when `HttpOnly` is missing. <br> - Session capture over plaintext when `Secure` is missing. <br> - Cross-site request forgery when `SameSite` is absent or `None`. |
| **Example** | A login response returns `Set-Cookie: session=abc123; Path=/` with no flags. With a reflected XSS, an attacker reads it via `document.cookie` and hijacks the session. |
| **How to Test** | 1. Log in and capture the `Set-Cookie` headers in Burp Suite. <br> 2. Check each session/auth cookie for `Secure`, `HttpOnly`, and `SameSite`. <br> 3. Confirm cookies are not sent over HTTP and are not readable via `document.cookie`. |
| **Tools** | Burp Suite, OWASP ZAP, browser DevTools, curl, Cookie-Editor extension |
| **Mitigation** | - Set `HttpOnly` on all session and auth cookies. <br> - Set `Secure` and serve only over HTTPS. <br> - Use `SameSite=Lax` or `Strict`, and scope with `Path` and `Domain`. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Cookies Attributes | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/02-Testing_for_Cookies_Attributes |
| OWASP Cheat Sheet - Session Management | https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html |
| MDN - Set-Cookie | https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie |
