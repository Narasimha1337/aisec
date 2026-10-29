### **Weak Ciphers**

| **Aspect** | **Details** |
|---|---|
| **Description** | Weak ciphers are TLS cipher suites or cryptographic algorithms that offer insufficient strength, such as RC4, DES/3DES, export-grade, NULL, or anonymous suites. They allow decryption, downgrade, or integrity attacks against otherwise encrypted traffic. |
| **Conditions to be Vulnerable** | - The server negotiates RC4, DES/3DES, EXPORT, NULL, or anonymous (aNULL) suites. <br> - CBC-mode legacy suites or short keys are enabled; no forward secrecy. <br> - The server lets the client pick weak suites instead of enforcing strong server preference. |
| **Where to Find** | - HTTPS endpoints, mail/FTP over TLS, VPNs, and management interfaces. <br> - Legacy appliances and middleboxes that retain old cipher lists. |
| **Common Exploits** | - RC4 biases and SWEET32 (64-bit block 3DES) attacks recovering plaintext. <br> - Downgrade to export-grade keys (FREAK/Logjam) enabling decryption. |
| **Example** | `nmap --script ssl-enum-ciphers -p 443 target.com` reports `TLS_RSA_WITH_RC4_128_SHA` graded `D`, confirming RC4 is offered and exploitable. |
| **How to Test** | 1. Enumerate suites with `nmap --script ssl-enum-ciphers -p 443 target.com` or `sslscan target.com`. <br> 2. Flag RC4, 3DES, EXPORT, NULL, and anonymous suites and missing forward secrecy. <br> 3. Confirm grades with testssl.sh or SSL Labs. Authorized targets only. |
| **Tools** | testssl.sh, sslscan, nmap (ssl-enum-ciphers), OpenSSL, Qualys SSL Labs |
| **Mitigation** | - Disable RC4, DES/3DES, EXPORT, NULL, and anonymous suites. <br> - Prefer AEAD suites (AES-GCM, ChaCha20-Poly1305) with ECDHE forward secrecy. <br> - Enforce server cipher ordering and require TLS 1.2+ (prefer TLS 1.3). |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Weak Encryption | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/04-Testing_for_Weak_Encryption |
| OWASP Cheat Sheet - Transport Layer Security | https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html |
| Mozilla - TLS Configuration Guidelines | https://wiki.mozilla.org/Security/Server_Side_TLS |
