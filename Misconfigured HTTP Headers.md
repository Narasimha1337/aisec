### **Misconfigured HTTP Headers**

| **Aspect** | **Details** |
|---|---|
| **Description** | Security-relevant HTTP response headers are missing, weak, or set incorrectly. This weakens browser-side defenses and can enable clickjacking, XSS, MIME sniffing, information leakage, and downgrade attacks. |
| **Conditions to be Vulnerable** | - Missing `Content-Security-Policy`, `X-Frame-Options`, or `X-Content-Type-Options`. <br> - Overly permissive CSP (e.g. `unsafe-inline`, `*`). <br> - Verbose headers leaking versions, or missing HSTS. |
| **Where to Find** | - HTTP response headers on all pages and API endpoints. <br> - CDN, proxy, and web-server configuration. |
| **Common Exploits** | - Clickjacking when `X-Frame-Options`/`frame-ancestors` is absent. <br> - MIME sniffing attacks without `X-Content-Type-Options: nosniff`. <br> - XSS made easier by weak/missing CSP; recon from version banners. |
| **Example** | A response lacks `X-Frame-Options` and CSP `frame-ancestors`. An attacker frames the page in a transparent iframe and overlays bait controls to perform clickjacking. |
| **How to Test** | 1. Capture response headers with Burp or `curl -I`. <br> 2. Check for CSP, `X-Frame-Options`, `X-Content-Type-Options`, HSTS, and `Referrer-Policy`. <br> 3. Review CSP strength and look for version-leaking headers. |
| **Tools** | Burp Suite, curl, nikto, nuclei, Mozilla Observatory |
| **Mitigation** | - Set a strict `Content-Security-Policy` and `X-Frame-Options: DENY` (or CSP `frame-ancestors`). <br> - Add `X-Content-Type-Options: nosniff`, HSTS, and a sane `Referrer-Policy`. <br> - Remove version-revealing headers like `Server` and `X-Powered-By`. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for HTTP Security Headers | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/ |
| OWASP Cheat Sheet - HTTP Security Response Headers | https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html |
| MDN - Content-Security-Policy | https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy |
