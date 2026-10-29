### **Unrestricted File Upload**

| **Aspect** | **Details** |
|---|---|
| **Description** | Unrestricted file upload occurs when an application accepts files without validating type, content, name, or storage location. It can lead to remote code execution (web shells), stored XSS, or overwriting critical files. |
| **Conditions to be Vulnerable** | - No or weak validation of extension, MIME type, or magic bytes. <br> - Uploaded files are stored in a web-accessible directory and can be executed. <br> - The original filename is trusted, enabling path traversal or extension tricks. |
| **Where to Find** | - Avatar/profile picture uploads, document/attachment uploads, import features. <br> - Rich-text editors, support tickets, and any multipart form accepting files. |
| **Common Exploits** | - Uploading a server-side script (`.php`, `.jsp`, `.aspx`) to gain a web shell. <br> - Stored XSS via uploaded `.html`/`.svg`; DoS or overwrite via crafted filenames. |
| **Example** | Upload `shell.php` containing `<?php system($_GET['c']); ?>`, then browse `/uploads/shell.php?c=id`. Bypasses: `shell.php.jpg`, `shell.pHp`, null byte `shell.php%00.jpg`, fake `Content-Type: image/jpeg`, or polyglot with valid magic bytes. |
| **How to Test** | 1. Upload a benign file and note the stored path and naming scheme. <br> 2. Attempt script extensions and content-type/extension bypasses in Burp. <br> 3. Confirm execution by requesting the stored file. Authorized targets only. |
| **Tools** | Burp Suite, OWASP ZAP, fuxploider, weevely (for generating shells in lab use) |
| **Mitigation** | - Validate by allowlist of extensions and verify content (magic bytes), not just MIME. <br> - Store uploads outside the webroot or on a non-executing domain/bucket; rename files server-side. <br> - Enforce size limits and scan uploads; serve with `Content-Disposition: attachment`. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Unrestricted File Upload | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/09-Test_Upload_of_Unexpected_File_Types |
| OWASP Cheat Sheet - File Upload | https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html |
| PortSwigger - File upload vulnerabilities | https://portswigger.net/web-security/file-upload |
