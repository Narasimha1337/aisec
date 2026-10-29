### **Remote Code Execution (RCE)**

| **Aspect** | **Details** |
|---|---|
| **Description** | Remote code execution lets an attacker run arbitrary commands or code on the target server. It is one of the most severe web vulnerabilities, typically yielding full server compromise, data theft, and lateral movement. |
| **Conditions to be Vulnerable** | - User input reaches a code/command sink (eval, deserialization, OS command, template). <br> - File upload accepts executable server-side scripts in a web-accessible path. <br> - Vulnerable or outdated components with known RCE bugs are deployed. |
| **Where to Find** | - File upload features, dynamic includes, command/eval wrappers, template engines. <br> - Deserialization endpoints, import/export tools, and outdated frameworks/plugins. |
| **Common Exploits** | - Uploading a web shell, then executing OS commands through it. <br> - Injecting into eval/command sinks or insecure deserialization to spawn a reverse shell. |
| **Example** | Vulnerable PHP sink: `<?php echo shell_exec($_GET['cmd']); ?>` exploited via `http://example.com/rce.php?cmd=whoami`. A simple webshell accepts a command via POST and returns output: `if (isset($_POST['cmd'])) { echo "<pre>".htmlspecialchars(shell_exec($_POST['cmd']))."</pre>"; }`. |
| **How to Test** | 1. Identify sinks/uploads; for command sinks inject `;id`, `&&whoami`, or `$(id)` and observe output. <br> 2. For uploads, place a server-side script (e.g. PHP webshell) and request it; if `.php` is blocked, try extension/content-type bypasses (`shell.php.jpg`, `Content-Type: image/jpeg`). A `.jpg`-upload-to-EXE reverse-shell trick: drop a PHP stub that writes a gzinflate(base64)-decoded binary to a temp dir and executes it with attacker IP/port. <br> 3. Confirm execution with a benign command (`id`/`whoami`) or an out-of-band callback. Authorized targets only. |
| **Tools** | Burp Suite, weevely, msfvenom/Metasploit, commix, nuclei |
| **Mitigation** | - Never pass user input to eval/exec/command APIs; use safe libraries and parameterization. <br> - Validate uploads by allowlist and store outside the webroot on a non-executing path; rename files. <br> - Patch components promptly and run services with least privilege. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Command Injection | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/12-Testing_for_Command_Injection |
| PortSwigger - OS command injection | https://portswigger.net/web-security/os-command-injection |
| OWASP Cheat Sheet - File Upload | https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html |
