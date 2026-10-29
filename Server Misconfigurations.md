### **Server Misconfigurations**

| **Aspect** | **Details** |
|---|---|
| **Description** | Security misconfiguration covers insecure defaults, exposed admin interfaces, verbose errors, directory listing, and unhardened services. It is OWASP Top 10 A05 and is frequently the easiest path to sensitive data or further compromise. |
| **Conditions to be Vulnerable** | - Default credentials, sample apps, or debug modes left enabled. <br> - Directory listing on, verbose stack traces, or exposed `.git`, `.env`, backups. <br> - Unnecessary services/ports open or overly permissive permissions. |
| **Where to Find** | - Web/app server config (Apache, Nginx, IIS), cloud storage, management consoles. <br> - Hidden paths: `/.git/`, `/.env`, `/admin`, `/actuator`, `/server-status`, `phpinfo.php`. |
| **Common Exploits** | - Downloading `.env`/`.git` to recover secrets and source code. <br> - Logging into exposed panels with default creds; reading internals via debug endpoints. |
| **Example** | `GET /.git/config` returns repo metadata, then `git-dumper` reconstructs source. `GET /actuator/env` (Spring Boot) leaks environment variables and credentials. |
| **How to Test** | 1. Fingerprint the stack and enumerate common sensitive paths with ffuf/nuclei. <br> 2. Check for directory listing, default pages, debug/info endpoints, and exposed VCS files. <br> 3. Test default credentials on any discovered admin interface. Authorized targets only. |
| **Tools** | nuclei, ffuf, Nikto, git-dumper, Burp Suite |
| **Mitigation** | - Harden defaults: disable directory listing, debug modes, and sample content. <br> - Remove or block access to VCS, config, and backup files; suppress verbose errors. <br> - Apply a repeatable hardening baseline and least-privilege permissions. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP - A05:2021 Security Misconfiguration | https://owasp.org/Top10/A05_2021-Security_Misconfiguration/ |
| OWASP WSTG - Configuration and Deployment Management Testing | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/ |
| OWASP Cheat Sheet - Infrastructure as Code Security | https://cheatsheetseries.owasp.org/cheatsheets/Infrastructure_as_Code_Security_Cheat_Sheet.html |
