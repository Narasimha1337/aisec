### **Missing Security Headers**

| **Aspect** | **Details** |
|---|---|
| **Description** | Missing or misconfigured HTTP response headers remove defense-in-depth protections, leaving the app more exposed to clickjacking, MIME sniffing, protocol downgrade, and cross-site scripting. The headers do not fix root causes but reduce exploitability. |
| **Conditions to be Vulnerable** | - Responses omit `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`/`frame-ancestors`, or `X-Content-Type-Options`. <br> - Headers are present but weak (overly broad CSP, missing HSTS `max-age`). |
| **Where to Find** | - All HTTP responses, especially the main app, login, and API endpoints. <br> - Behind proxies/CDNs where header injection may be inconsistent. |
| **Common Exploits** | - Clickjacking when framing is not restricted. <br> - Reflected/stored XSS impact amplified without CSP; HTTPS downgrade without HSTS. |
| **Example** | A response missing `X-Frame-Options: DENY` and CSP `frame-ancestors 'none'` can be embedded in an attacker iframe for UI-redress (clickjacking). Missing `Strict-Transport-Security` allows SSL-strip downgrade. |
| **How to Test** | 1. Inspect response headers with `curl -I https://target.com` or Burp. <br> 2. Note which protective headers are absent or weak. <br> 3. Scan with securityheaders.com or Mozilla Observatory for a graded summary. Authorized targets only. |
| **Tools** | curl, Burp Suite, OWASP ZAP, securityheaders.com, Mozilla Observatory |
| **Mitigation** | - Set a strict `Content-Security-Policy` and `frame-ancestors 'none'` (or `X-Frame-Options: DENY`). <br> - Add `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy`. <br> - Apply headers centrally at the server/proxy so all responses are covered. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP - HTTP Security Response Headers Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html |
| MDN - Content-Security-Policy | https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy |
| OWASP - Secure Headers Project | https://owasp.org/www-project-secure-headers/ |
