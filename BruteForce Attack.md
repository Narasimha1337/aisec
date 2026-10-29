### **Brute Force Attack**

| **Aspect** | **Details** |
|---|---|
| **Description** | An attacker systematically tries many credentials, tokens, or values until one works. It succeeds when an endpoint lacks rate limiting, lockout, or sufficient secret entropy. |
| **Conditions to be Vulnerable** | - No rate limiting or account lockout on sensitive endpoints. <br> - Weak passwords or short, predictable tokens/PINs. <br> - No CAPTCHA or progressive delay after repeated failures. |
| **Where to Find** | - Login forms, MFA/OTP fields, password reset, and API auth endpoints. <br> - Coupon codes, gift cards, and any short secret values. |
| **Common Exploits** | - Password brute forcing and dictionary attacks. <br> - OTP/2FA code guessing (e.g. 4-6 digit codes). <br> - Token or ID enumeration where space is small. |
| **Example** | A login at `POST /login` accepts unlimited attempts. An attacker runs `hydra -l admin -P rockyou.txt example.com http-post-form` until valid credentials return a 302 redirect. |
| **How to Test** | 1. Send many failed login attempts and watch for lockout, delay, or CAPTCHA. <br> 2. Automate guesses with Burp Intruder or ffuf and compare response codes/lengths. <br> 3. Test OTP fields for limited attempts and code expiry. |
| **Tools** | Burp Suite (Intruder), hydra, ffuf, medusa, patator |
| **Mitigation** | - Enforce rate limiting, exponential backoff, and account lockout. <br> - Require strong passwords and MFA. <br> - Add CAPTCHA after failures and alert on anomalies. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Weak Lock Out Mechanism | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/03-Testing_for_Weak_Lock_Out_Mechanism |
| PortSwigger - Brute-force attacks | https://portswigger.net/web-security/authentication/password-based |
| OWASP Cheat Sheet - Authentication | https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html |
