### **Information Disclosure**

| **Aspect** | **Details** |
|---|---|
| **Description** | The application unintentionally exposes sensitive data such as credentials, internal paths, API keys, PII, or system details. Even when not directly exploitable, it gives attackers material to plan deeper attacks. |
| **Conditions to be Vulnerable** | - Sensitive files or endpoints reachable without auth. <br> - Secrets committed to client-side code, comments, or repos. <br> - Verbose banners, headers, or directory listings enabled. |
| **Where to Find** | - JavaScript bundles, source maps, HTML comments, and metadata. <br> - `/.git/`, `.env`, backup files, `robots.txt`, `sitemap.xml`. <br> - Response headers (`Server`, `X-Powered-By`) and error pages. |
| **Common Exploits** | - Extracting API keys/tokens from front-end JS. <br> - Downloading exposed `.git` or backup archives to recover source. <br> - Harvesting internal hostnames, versions, and PII for follow-on attacks. |
| **Example** | A request to `https://app.example.com/.git/config` returns repository config, allowing an attacker to dump the full `.git` directory and reconstruct source code and secrets. |
| **How to Test** | 1. Crawl and review JS, comments, and source maps for secrets. <br> 2. Probe common sensitive paths (`/.git/`, `.env`, `.bak`) with ffuf. <br> 3. Inspect headers and error pages for version and path leakage. |
| **Tools** | Burp Suite, ffuf, gitleaks, gau, Nikto, nuclei |
| **Mitigation** | - Restrict or remove sensitive files and endpoints. <br> - Keep secrets server-side; rotate any that leaked. <br> - Suppress verbose banners, disable directory listing, and scan for secrets in CI. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Information Gathering | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/ |
| PortSwigger - Information disclosure | https://portswigger.net/web-security/information-disclosure |
| OWASP Top 10 - Cryptographic Failures | https://owasp.org/Top10/A02_2021-Cryptographic_Failures/ |
