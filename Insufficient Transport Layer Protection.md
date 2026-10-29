### **Insufficient Transport Layer Protection**

| **Aspect** | **Details** |
|---|---|
| **Description** | Data in transit is not adequately protected by TLS, due to missing HTTPS, mixed content, weak protocols/ciphers, or no HSTS. Attackers on the network can intercept or tamper with traffic, including credentials and session tokens. |
| **Conditions to be Vulnerable** | - Sensitive pages served over HTTP or with mixed content. <br> - HSTS not set, so users can be downgraded to HTTP. <br> - Deprecated protocols (SSLv3, TLS 1.0/1.1) or weak ciphers enabled. |
| **Where to Find** | - Login, payment, and any page handling sensitive data. <br> - TLS configuration of the web server and load balancer. <br> - Resource references (scripts, images) loaded over HTTP. |
| **Common Exploits** | - Man-in-the-middle sniffing of credentials and session cookies. <br> - SSL stripping / downgrade to HTTP when HSTS is missing. <br> - Exploiting weak ciphers/protocols (e.g. via known TLS attacks). |
| **Example** | A login form posts to `http://example.com/login`. An attacker on the same Wi-Fi captures the cleartext request with credentials, since no TLS protects the submission. |
| **How to Test** | 1. Scan TLS config with `testssl.sh` or `sslscan` for weak protocols/ciphers. <br> 2. Check for HTTP-to-HTTPS redirects and an `Strict-Transport-Security` header. <br> 3. Inspect pages for mixed content and cleartext form submissions. |
| **Tools** | testssl.sh, sslscan, nmap (ssl-enum-ciphers), Burp Suite, SSL Labs |
| **Mitigation** | - Enforce HTTPS everywhere and redirect HTTP to HTTPS. <br> - Enable HSTS (with preload) and disable old protocols/weak ciphers. <br> - Eliminate mixed content and keep TLS libraries patched. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Weak Transport Layer Security | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/01-Testing_for_Weak_Transport_Layer_Security |
| OWASP Cheat Sheet - Transport Layer Security | https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html |
| OWASP Cheat Sheet - HTTP Strict Transport Security | https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html |
