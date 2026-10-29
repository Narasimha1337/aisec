### **Credential Stuffing**

| **Aspect** | **Details** |
|---|---|
| **Description** | Attackers replay username/password pairs leaked from other breaches against a login endpoint, betting on password reuse. Unlike brute force, it uses known valid pairs, so even modest reuse yields account takeovers. |
| **Conditions to be Vulnerable** | - No rate limiting, MFA, or anomaly detection on login. <br> - Users reuse passwords across sites. <br> - Login responses distinguish valid from invalid accounts. |
| **Where to Find** | - Login and API authentication endpoints. <br> - Mobile and legacy auth endpoints lacking modern protections. |
| **Common Exploits** | - Mass automated login with breached credential lists. <br> - Distributed attempts across proxies/IPs to evade throttling. <br> - Pairing with username enumeration to refine the list. |
| **Example** | An attacker feeds a leaked `email:password` combo list to `POST /api/login`; pairs returning `200` with a session token mark successfully taken-over accounts. |
| **How to Test** | 1. With authorization, submit a known-test credential list and watch for rate limiting and lockout. <br> 2. Check whether responses leak valid vs invalid distinctions. <br> 3. Confirm MFA and bot defenses (device fingerprinting, CAPTCHA) are enforced. |
| **Tools** | Burp Suite (Intruder), OWASP ZAP, ffuf, hydra |
| **Mitigation** | - Enforce MFA and rate limiting/lockout per account and IP. <br> - Check passwords against breach corpora (e.g. Pwned Passwords). <br> - Add bot detection and uniform login responses. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP Cheat Sheet - Credential Stuffing Prevention | https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html |
| OWASP Automated Threats - Credential Stuffing (OAT-008) | https://owasp.org/www-project-automated-threats-to-web-applications/ |
| PortSwigger - Authentication vulnerabilities | https://portswigger.net/web-security/authentication |
