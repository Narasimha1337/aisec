### **Insufficient Security Controls**

| **Aspect** | **Details** |
|---|---|
| **Description** | Security defenses that should be present are missing, weak, or only partially applied, such as absent authorization checks, no rate limiting, missing input validation, or inconsistent enforcement across endpoints. Attackers exploit the gaps. |
| **Conditions to be Vulnerable** | - Controls enforced on some endpoints but not others. <br> - Client-side-only validation or authorization. <br> - Missing rate limiting, logging, or anomaly detection. |
| **Where to Find** | - New, legacy, or undocumented API endpoints. <br> - Admin functions reachable without server-side authorization. <br> - Bulk/automation-prone actions lacking throttling. |
| **Common Exploits** | - Accessing privileged actions by calling unprotected endpoints directly. <br> - Bypassing client-side validation by editing requests. <br> - Abusing missing rate limits for enumeration or brute force. |
| **Example** | The UI hides an admin button, but `POST /api/admin/users/delete` has no server-side role check, so any authenticated user can delete accounts directly. |
| **How to Test** | 1. Map all endpoints (including those not linked in the UI). <br> 2. Replay privileged requests as a low-privilege or anonymous user. <br> 3. Tamper with client-side validation and probe for missing rate limits. |
| **Tools** | Burp Suite, OWASP ZAP, ffuf, nuclei, Postman |
| **Mitigation** | - Enforce authentication, authorization, and validation server-side on every endpoint. <br> - Apply controls consistently and deny by default. <br> - Add rate limiting, logging, and monitoring. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP Top 10 - Broken Access Control | https://owasp.org/Top10/A01_2021-Broken_Access_Control/ |
| OWASP WSTG - Authorization Testing | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/ |
| OWASP ASVS | https://owasp.org/www-project-application-security-verification-standard/ |
