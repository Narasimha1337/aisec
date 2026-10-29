### **Unsecured API Endpoints**

| **Aspect** | **Details** |
|---|---|
| **Description** | Unsecured API endpoints expose functionality or data without proper authentication, authorization, or rate limiting. They are a top API risk (OWASP API Security Top 10) and often leak sensitive data or allow unauthorized actions. |
| **Conditions to be Vulnerable** | - Endpoints lack authentication or rely on hidden/obscure URLs only. <br> - Missing object-level (BOLA/IDOR) or function-level authorization. <br> - Undocumented, debug, or deprecated endpoints left reachable; no rate limiting. |
| **Where to Find** | - REST/GraphQL routes, mobile-app backends, internal APIs exposed externally. <br> - JS bundles and Swagger/OpenAPI docs revealing endpoint paths and parameters. |
| **Common Exploits** | - Accessing other users' objects by changing an ID (BOLA/IDOR). <br> - Calling admin/internal functions directly; data scraping due to no rate limits. |
| **Example** | `GET /api/v1/users/1024/invoices` returns another user's invoices when only the ID is changed and no ownership check exists. Or `GET /api/internal/debug/config` is reachable without auth and leaks secrets. |
| **How to Test** | 1. Enumerate endpoints from JS files, Swagger/OpenAPI, and traffic (Burp, kiterunner). <br> 2. Call each without a token, then with a low-privilege token, and tamper object IDs. <br> 3. Test method overrides, versioned/legacy routes, and rate-limit absence. Authorized targets only. |
| **Tools** | Burp Suite, Postman, kiterunner, ffuf, arjun |
| **Mitigation** | - Require authentication and enforce object- and function-level authorization server-side. <br> - Inventory and retire undocumented/deprecated endpoints; protect docs and debug routes. <br> - Apply rate limiting, input validation, and least-privilege scopes. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP API Security Top 10 | https://owasp.org/API-Security/editions/2023/en/0x11-t10/ |
| OWASP Cheat Sheet - REST Security | https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html |
| PortSwigger - API testing | https://portswigger.net/web-security/api-testing |
