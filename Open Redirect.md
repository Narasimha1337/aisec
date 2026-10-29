### **Open Redirect**

| **Aspect** | **Details** |
|---|---|
| **Description** | An open redirect occurs when an application takes a user-controlled value and uses it as the target of a redirect without validation. Attackers abuse the trusted domain to send victims to malicious sites, aiding phishing, credential theft, and OAuth token theft. |
| **Conditions to be Vulnerable** | - A redirect target is read from a request parameter, header, or path. <br> - The destination is not validated against an allowlist of trusted URLs. <br> - Relative-only enforcement is missing, so absolute external URLs are accepted. |
| **Where to Find** | - Login/logout flows with `?next=`, `?returnUrl=`, `?redirect=`, `?url=` parameters. <br> - OAuth/SSO `redirect_uri` handling and email verification links. |
| **Common Exploits** | - Phishing by sending victims a link on the trusted domain that bounces to an attacker site. <br> - Stealing OAuth tokens or codes by redirecting the authorization response to an attacker-controlled origin. |
| **Example** | `https://trusted.com/login?next=https://evil.com` redirects an authenticated victim to the attacker site. Bypasses for naive filters: `next=//evil.com`, `next=https:evil.com`, `next=/%2f%2fevil.com`. |
| **How to Test** | 1. Identify redirect parameters by browsing auth flows and reviewing 30x `Location` headers in Burp. <br> 2. Set the value to an external domain (`https://evil.com`) and watch for an external `Location`. <br> 3. If blocked, try bypasses (`//`, `\/\/`, whitelisted-host prefix `evil.com.trusted.com`, encoded slashes). Only test authorized targets. |
| **Tools** | Burp Suite, OWASP ZAP, curl, ffuf |
| **Mitigation** | - Use a server-side allowlist of permitted destinations or map a token to a known URL. <br> - Accept only relative paths and reject any value containing a scheme or `//`. <br> - Show an interstitial warning page for any off-site redirect. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Client-side URL Redirect | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/04-Testing_for_Client-side_URL_Redirect |
| OWASP Cheat Sheet - Unvalidated Redirects and Forwards | https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html |
| PortSwigger - OAuth account hijacking via redirect_uri | https://portswigger.net/web-security/oauth |
