### **Outdated TLS Version**

| **Aspect** | **Details** |
|---|---|
| **Description** | A server supporting deprecated protocols (SSLv2/v3, TLS 1.0, TLS 1.1) exposes traffic to known attacks and weakens transport security. These versions are formally deprecated (RFC 8996) and fail modern compliance baselines. |
| **Conditions to be Vulnerable** | - The server negotiates SSLv3, TLS 1.0, or TLS 1.1. <br> - Insecure renegotiation or downgrade protection (TLS_FALLBACK_SCSV) is missing. <br> - Legacy cipher suites tied to old protocols remain enabled. |
| **Where to Find** | - HTTPS endpoints, API gateways, load balancers, and mail/FTP services over TLS. <br> - Internal services and legacy appliances often lag on protocol hardening. |
| **Common Exploits** | - POODLE (SSLv3) and BEAST (TLS 1.0 CBC) attacks against confidentiality. <br> - Protocol downgrade forcing a client onto a weaker version, then exploiting it. |
| **Example** | `openssl s_client -connect target.com:443 -tls1` succeeds, confirming TLS 1.0 is still accepted. A network attacker can then attempt a downgrade to the weakest mutually supported version. |
| **How to Test** | 1. Run `nmap --script ssl-enum-ciphers -p 443 target.com` to list supported protocols and ciphers. <br> 2. Confirm individual versions with `openssl s_client -connect target.com:443 -tls1` / `-tls1_1`. <br> 3. Cross-check with testssl.sh or SSL Labs for a graded report. Authorized targets only. |
| **Tools** | testssl.sh, nmap (ssl-enum-ciphers), sslscan, OpenSSL, Qualys SSL Labs |
| **Mitigation** | - Disable SSLv2/v3, TLS 1.0, and TLS 1.1; require TLS 1.2+ (prefer TLS 1.3). <br> - Enable TLS_FALLBACK_SCSV and HSTS, and remove legacy ciphers. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Weak Transport Layer Security | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/01-Testing_for_Weak_Transport_Layer_Security |
| RFC 8996 - Deprecating TLS 1.0 and TLS 1.1 | https://www.rfc-editor.org/rfc/rfc8996 |
| OWASP Cheat Sheet - Transport Layer Security | https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html |
