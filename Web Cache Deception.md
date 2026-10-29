### **Web Cache Deception**

| **Aspect** | **Details** |
|---|---|
| **Description** | Web cache deception tricks a caching layer into storing a victim's dynamic, sensitive response under a URL the attacker can later retrieve. It abuses the mismatch between how the cache decides what is cacheable and how the origin maps the path. |
| **Conditions to be Vulnerable** | - A cache (CDN/reverse proxy) caches based on file extension or path pattern. <br> - The origin ignores or maps the appended segment back to the dynamic page. <br> - Authenticated, user-specific content is served on the mapped path. |
| **Where to Find** | - Account/profile/settings pages behind a CDN (Cloudflare, Akamai, Fastly, Varnish). <br> - Endpoints reachable with appended path segments or fake extensions. |
| **Common Exploits** | - Caching a victim's account page so the attacker fetches it and reads PII/tokens. <br> - Leaking CSRF tokens or API keys embedded in cached authenticated responses. |
| **Example** | Lure a logged-in victim to `https://app.com/account/profile.css`. The CDN caches it as a static `.css`, but the origin still returns the profile page. The attacker then requests the same URL and reads the cached personal data. |
| **How to Test** | 1. Identify an authenticated dynamic page and append a static-looking suffix (`/nonexistent.css`, `;.jpg`, `/x.js`). <br> 2. Request it as the victim, then re-request as an unauthenticated user and check for cached personal content (look for `X-Cache: HIT`). <br> 3. Vary delimiters and extensions per cache behavior. Authorized targets only. |
| **Tools** | Burp Suite (Param Miner), curl, browser dev tools |
| **Mitigation** | - Cache only by explicit allowlist with correct `Cache-Control` on dynamic responses (`no-store`, `private`). <br> - Align cache rules with origin routing so extensions do not override content type decisions. <br> - Set `Cache-Control: no-store` on authenticated/user-specific pages. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| PortSwigger - Web cache deception | https://portswigger.net/web-security/web-cache-deception |
| OWASP - Web Cache Deception | https://owasp.org/www-community/attacks/Web_Cache_Deception |
| HackTricks - Web Cache Deception | https://book.hacktricks.wiki/en/pentesting-web/web-cache-deception.html |
