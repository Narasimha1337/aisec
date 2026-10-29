### **Broken Authentication**

| **Aspect** | **Details** |
|---|---|
| **Description** | Flaws in how an application confirms a user's identity, letting attackers compromise passwords, tokens, or sessions and assume other users' identities. It is one of the highest-impact web risks (OWASP Top 10: Identification and Authentication Failures). |
| **Conditions to be Vulnerable** | - Weak or missing rate limiting on login and reset flows. <br> - Predictable or non-rotated session tokens. <br> - Credentials sent over HTTP, or weak password policy and no MFA. |
| **Where to Find** | - Login, registration, password reset, and "remember me" flows. <br> - Session token issuance and multi-factor verification steps. |
| **Common Exploits** | - Credential stuffing and brute force from weak rate limiting. <br> - Session fixation and token prediction or replay. <br> - Account takeover via weak password-reset tokens or MFA bypass. |
| **Example** | A reset link uses a sequential numeric token: `https://app.example.com/reset?token=1042`. An attacker enumerates tokens (`1041`, `1043`) to reset other users' passwords. |
| **How to Test** | 1. Probe login and reset endpoints for rate limiting and lockout (ffuf, hydra). <br> 2. Inspect session tokens for entropy and rotation after login (Burp Sequencer). <br> 3. Test password-reset token uniqueness, expiry, and MFA enforcement. |
| **Tools** | Burp Suite, hydra, ffuf, OWASP ZAP, Burp Sequencer |
| **Mitigation** | - Enforce rate limiting, lockout, and strong password policy. <br> - Require MFA and rotate session tokens on login. <br> - Use cryptographically strong, single-use, expiring reset tokens over TLS. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Authentication Testing | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/ |
| OWASP Top 10 - Identification and Authentication Failures | https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/ |
| OWASP Cheat Sheet - Authentication | https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html |
