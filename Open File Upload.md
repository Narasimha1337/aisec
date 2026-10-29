

### **Open File Upload (Publicly Exposed Uploads)**

This page covers the specific angle of upload functionality and uploaded files being exposed without proper access control. For full exploitation of upload validation flaws (web shells, extension and content-type bypasses), see the sibling [Unrestricted File Upload](/web-application-pentesting/vulnerabilities/unrestricted-file-upload) page.

| **Aspect** | **Details** |
|---|---|
| **Description** | Upload features or already-uploaded files are reachable by anyone, with no authentication or authorization. Even when file type is validated, exposed storage can leak sensitive documents (IDs, invoices, internal files) or let unauthenticated users upload content. |
| **Where to Find** | - Upload endpoints reachable without logging in. <br> - Public upload directories such as `/uploads/`, `/files/`, `/media/`, `/attachments/`. <br> - Object storage buckets and CDNs holding user uploads. |
| **How to Test** | 1. Access the upload feature while logged out and confirm whether it works. <br> 2. Upload a file as one user, then try retrieving it as another user or anonymously. <br> 3. Check for directory listing on upload paths (e.g. browse `/uploads/`). <br> 4. Test for predictable or enumerable file names/IDs (sequential, timestamp, original filename). <br> Authorized targets only. |
| **Tools** | Burp Suite, OWASP ZAP, ffuf/dirsearch (for path and directory discovery) |
| **Mitigation** | - Enforce authentication and authorization on both upload and retrieval. <br> - Disable directory listing on upload locations. <br> - Use random, unguessable file identifiers and serve files through an access-checked handler. <br> - Store uploads outside the webroot or in private storage with signed, expiring URLs. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP Cheat Sheet - File Upload | https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html |
| OWASP WSTG - Testing Directory Traversal File Include | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/01-Testing_Directory_Traversal_File_Include |
| PortSwigger - File upload vulnerabilities | https://portswigger.net/web-security/file-upload |

---

|S.N | Credit|
|-----|------|
|Zlatan H  | https://www.linkedin.com/in/zlatanh/|

![image](https://github.com/user-attachments/assets/9e914b34-b108-462a-bc97-844621887aa9)
