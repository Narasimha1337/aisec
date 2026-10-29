### **Host Header Injection**

| **Aspect** | **Details** |
|---|---|
| **Description** | The application trusts the client-supplied `Host` header (or related headers like `X-Forwarded-Host`) when building URLs, links, or routing decisions. An attacker can spoof it to poison links, reset emails, or caches. |
| **Conditions to be Vulnerable** | - Server reflects the `Host` header into responses or generated URLs. <br> - Password-reset links built from the request host. <br> - Caches keyed without normalizing host, or ambiguous virtual-host routing. |
| **Where to Find** | - Password reset and email-link generation flows. <br> - Absolute redirects, canonical tags, and cached pages. |
| **Common Exploits** | - Password-reset poisoning: reset link points to attacker host. <br> - Web cache poisoning via `X-Forwarded-Host`. <br> - Routing-based SSRF or access bypass via spoofed host. |
| **Example** | A reset request sent with `Host: evil.com` produces an email link `https://evil.com/reset?token=...`; when the victim clicks it, the token is delivered to the attacker. |
| **How to Test** | 1. Change the `Host` header in Burp and watch for reflection in links/redirects. <br> 2. Add `X-Forwarded-Host: evil.com` and check if generated URLs follow it. <br> 3. Trigger a password reset with a spoofed host and inspect the email link. |
| **Tools** | Burp Suite, OWASP ZAP, curl, Param Miner extension |
| **Mitigation** | - Validate the `Host` header against an allowlist of expected domains. <br> - Use a configured canonical base URL instead of the request host. <br> - Ignore untrusted forwarding headers and normalize cache keys. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Host Header Injection | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/17-Testing_for_Host_Header_Injection |
| PortSwigger - HTTP Host header attacks | https://portswigger.net/web-security/host-header |
| HackTricks - Host Header Injection | https://hacktricks.wiki/en/pentesting-web/abusing-hop-by-hop-headers.html |
