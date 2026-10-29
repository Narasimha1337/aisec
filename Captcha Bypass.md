### **Captcha Bypass**

| **Aspect** | **Details** |
|---|---|
| **Description** | A CAPTCHA is meant to block automated requests, but flawed implementation lets attackers skip or solve it programmatically. Bypassing it re-enables brute force, spam, and other automation the control was meant to stop. |
| **Conditions to be Vulnerable** | - CAPTCHA validated client-side only, or token reusable. <br> - Server accepts requests when the CAPTCHA parameter is missing or empty. <br> - Same CAPTCHA answer accepted repeatedly, or weak/static images. |
| **Where to Find** | - Login, registration, password reset, contact, and checkout forms. <br> - Any endpoint protected by CAPTCHA to throttle automation. |
| **Common Exploits** | - Removing or blanking the CAPTCHA token in the request. <br> - Replaying a single valid token across many requests. <br> - Solving via OCR or third-party solver services for weak CAPTCHAs. |
| **Example** | A form submits `g-recaptcha-response=...`. Removing that parameter (or sending a previously valid one) still returns `200 OK`, so the server never verifies it server-side. |
| **How to Test** | 1. Intercept the submission in Burp and delete or empty the CAPTCHA parameter. <br> 2. Capture one valid token and replay it across multiple requests. <br> 3. Confirm server-side verification with the provider's verify API is actually enforced. |
| **Tools** | Burp Suite, OWASP ZAP, ffuf, tesseract (OCR), curl |
| **Mitigation** | - Verify CAPTCHA server-side and enforce single-use tokens. <br> - Reject requests with missing or invalid CAPTCHA values. <br> - Combine with rate limiting and bot-detection signals. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for CAPTCHA | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/09-Testing_for_Weak_Security_Question_Answer |
| OWASP Automated Threats - CAPTCHA Defeat | https://owasp.org/www-project-automated-threats-to-web-applications/ |
| HackTricks - Captcha Bypass | https://hacktricks.wiki/en/pentesting-web/captcha-bypass.html |
