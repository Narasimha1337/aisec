### **Path Traversal**

| **Aspect** | **Details** |
|---|---|
| **Description** | Path traversal (directory traversal) lets an attacker read or write files outside the intended directory by injecting `../` sequences into a file path the application builds from user input. It can expose source code, credentials, and system files. |
| **Conditions to be Vulnerable** | - User input is concatenated into a filesystem path. <br> - No canonicalization or allowlist validation of the resolved path. <br> - The process has filesystem permissions to reach sensitive files. |
| **Where to Find** | - File download/preview endpoints (`?file=`, `?path=`, `?template=`). <br> - Image loaders, log viewers, archive extractors, and import features. |
| **Common Exploits** | - Reading sensitive files such as `/etc/passwd` or app config and secrets. <br> - Writing to arbitrary paths (zip-slip, log poisoning) leading to code execution. |
| **Example** | `GET /download?file=../../../../etc/passwd`. Bypasses: URL-encode (`%2e%2e%2f`), double-encode (`%252e%252e%252f`), nested (`....//`), or absolute path `?file=/etc/passwd`. On Windows: `..\..\..\windows\win.ini`. |
| **How to Test** | 1. Find parameters that reference files; baseline a normal request in Burp. <br> 2. Inject traversal sequences toward `/etc/passwd` or `win.ini` and observe responses. <br> 3. Apply encoding and prefix-stripping bypasses if filtered. Authorized testing only. |
| **Tools** | Burp Suite, OWASP ZAP, ffuf, dotdotpwn |
| **Mitigation** | - Resolve the canonical path and verify it stays within an allowed base directory. <br> - Use an allowlist of identifiers mapped to safe filenames instead of raw paths. <br> - Run with least-privilege filesystem access. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing Directory Traversal File Include | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/01-Testing_Directory_Traversal_File_Include |
| PortSwigger - Directory traversal | https://portswigger.net/web-security/file-path-traversal |
| OWASP Cheat Sheet - Input Validation | https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html |
