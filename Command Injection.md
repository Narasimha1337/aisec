### **Command Injection**

| **Aspect** | **Details** |
|---|---|
| **Description** | The application passes user-controlled input into an operating-system shell command without sanitization, letting an attacker run arbitrary commands on the host. It often leads to full server compromise. |
| **Conditions to be Vulnerable** | - User input reaches a shell call (e.g. `system`, `exec`, backticks) unsanitized. <br> - No allowlisting or safe argument passing. <br> - Functionality that wraps OS utilities (ping, nslookup, image/PDF conversion). |
| **Where to Find** | - Network diagnostic tools (ping, traceroute, whois). <br> - File processing, export, and admin/maintenance features. <br> - Parameters that feed into command-line tools. |
| **Common Exploits** | - Chaining commands with `;`, `&&`, `\|`, `\|\|`. <br> - Subshells via `$( )` or backticks. <br> - Blind/out-of-band exfiltration via DNS or HTTP callbacks. |
| **Example** | A host field `127.0.0.1; id` sent to a ping feature runs `ping -c 1 127.0.0.1; id`, executing `id` and returning `uid=33(www-data)`. |
| **How to Test** | 1. Inject separators and observe output: `; id`, `&& whoami`, `\| cat /etc/passwd`. <br> 2. For blind cases, force a delay (`; sleep 10`) or out-of-band callback to Burp Collaborator. <br> 3. Confirm with controlled, authorized payloads only and document evidence. |
| **Tools** | Burp Suite (Collaborator), commix, ffuf, curl, interactsh |
| **Mitigation** | - Avoid shell calls; use language-native APIs and parameterized exec. <br> - Allowlist and strictly validate input. <br> - Run with least privilege and escape arguments if a shell is unavoidable. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing for Command Injection | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/12-Testing_for_Command_Injection |
| PortSwigger - OS command injection | https://portswigger.net/web-security/os-command-injection |
| OWASP Cheat Sheet - OS Command Injection Defense | https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html |
