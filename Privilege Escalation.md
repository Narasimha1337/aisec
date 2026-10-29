### **Privilege Escalation**

| **Aspect** | **Details** |
|---|---|
| **Description** | Privilege escalation is when a user gains access or capabilities beyond what their role permits. Vertical escalation reaches higher privileges (user to admin); horizontal escalation reaches another user's data at the same level. |
| **Conditions to be Vulnerable** | - Authorization is enforced in the UI or client only, not server-side. <br> - Roles/permissions are trusted from client-controlled values (cookies, JWT claims, hidden fields). <br> - Admin or sensitive functions lack per-request access checks. |
| **Where to Find** | - Admin panels, user-management and role-assignment endpoints. <br> - Object references (`?userId=`, `?role=`), mass-assignment in JSON APIs, and JWT claims. |
| **Common Exploits** | - Forcing browsing to admin URLs/functions that skip server-side checks. <br> - Tampering role parameters or JWT claims (`"role":"admin"`) to elevate. <br> - Mass assignment of `isAdmin=true` during profile update. |
| **Example** | A standard user sends `POST /api/profile {"email":"x@y.com","role":"admin"}` and the API blindly persists `role`, granting admin. Or visiting `/admin/users` directly returns the admin page without authorization. |
| **How to Test** | 1. Map roles by logging in as low- and high-privilege accounts and recording requests. <br> 2. Replay privileged requests with the low-privilege session/token (Burp Autorize). <br> 3. Tamper role fields, JWT claims, and add extra fields to test mass assignment. Authorized accounts only. |
| **Tools** | Burp Suite (Autorize), OWASP ZAP, jwt_tool, AuthMatrix |
| **Mitigation** | - Enforce server-side, deny-by-default authorization on every request and object. <br> - Derive roles from the server session, never from client input or unsigned claims. <br> - Use allowlists for bindable fields to prevent mass assignment. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Privilege Escalation | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/03-Testing_for_Privilege_Escalation |
| OWASP Cheat Sheet - Authorization | https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html |
| PortSwigger - Access control vulnerabilities | https://portswigger.net/web-security/access-control |
