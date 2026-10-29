### **Improper Error Handling**

| **Aspect** | **Details** |
|---|---|
| **Description** | The application returns verbose errors, stack traces, or debug output that reveal internal details such as file paths, SQL queries, framework versions, or secrets. This aids attackers in mapping and exploiting the system. |
| **Conditions to be Vulnerable** | - Debug mode enabled in production. <br> - Unhandled exceptions surfaced directly to users. <br> - Detailed database or framework errors returned in responses. |
| **Where to Find** | - Form inputs that trigger validation or type errors. <br> - API endpoints with malformed or unexpected payloads. <br> - 404/500 pages and uncaught exception responses. |
| **Common Exploits** | - Leaking stack traces, file paths, and software versions. <br> - SQL error messages that guide SQL injection. <br> - Different error responses enabling user/resource enumeration. |
| **Example** | Submitting `id='` returns `SQLSTATE[42000]: Syntax error near ''' in /var/www/app/db.php:88`, exposing the DBMS, query context, and absolute file path. |
| **How to Test** | 1. Send malformed input (wrong types, broken syntax, oversized values). <br> 2. Inspect responses for stack traces, paths, versions, and SQL errors. <br> 3. Compare error responses across valid/invalid resources for enumeration leaks. |
| **Tools** | Burp Suite, OWASP ZAP, curl, ffuf, Nikto |
| **Mitigation** | - Disable debug mode and return generic error messages in production. <br> - Log full details server-side only. <br> - Use centralized exception handling and consistent, non-revealing responses. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Improper Error Handling | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling/01-Testing_For_Improper_Error_Handling |
| OWASP Cheat Sheet - Error Handling | https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html |
| OWASP Top 10 - Security Misconfiguration | https://owasp.org/Top10/A05_2021-Security_Misconfiguration/ |
