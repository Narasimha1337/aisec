### **Web Cache Poisoning**

| **Aspect**                   | **Details**                                                                                                                                           |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Description**              | Web Cache Poisoning tricks a caching layer (CDN, reverse proxy, in-app cache) into storing a harmful response, which is then served to every user who requests the same cached key. Unlike Web Cache Deception (which leaks one victim's private page), poisoning weaponises a single request to attack all visitors, typically delivering stored XSS, redirects, or denial of service. |
| **Conditions to be Vulnerable** | - A response is cached and the cache key ignores some input that still influences the response (an "unkeyed input"). <br> - Unkeyed headers (e.g. `X-Forwarded-Host`, `X-Forwarded-Scheme`, `X-Host`) are reflected into the body, links, or redirects. <br> - The cache serves stale or shared responses across users. |
| **Where to Find**            | - Static-ish endpoints with caching (`Cache-Control: public`, `Age`, `X-Cache: hit/miss`). <br> - Responses that reflect headers like Host overrides, language, or cookies that are not part of the cache key. <br> - Cache key normalisation flaws (cache key flaws, fat GET, parameter cloaking). |
| **Common Exploits**          | - Reflect `X-Forwarded-Host` into a `<script src>` or canonical link to load attacker JS. <br> - Poison a redirect via `X-Forwarded-Scheme: nothttps`. <br> - **DoS**: send an oversized or malformed unkeyed header that makes the cached response an error page. <br> - Cache deception/key confusion via path delimiters. |
| **Example**                  | Request `GET /en?cb=1` with `X-Forwarded-Host: evil.com`. If the app reflects it into `<script src="//evil.com/a.js">` and the cache stores it keyed only on the path, every later visitor of `/en?cb=1` runs attacker JavaScript. |
| **How to Test**              | 1. Add a cache buster (unique query param) so you never poison real users. <br> 2. Add candidate unkeyed headers (`X-Forwarded-Host`, `X-Forwarded-For`, `X-Original-URL`) and watch for reflection. <br> 3. Confirm the response is cached (`X-Cache: hit`, `Age` increases) and that a clean request without your header returns the poisoned content. |
| **Tools**                    | Burp Suite with the **Param Miner** extension (header/parameter guessing, cache poisoning scan), Burp Repeater, `curl` for header injection and cache-header inspection. |
| **Mitigation**               | - Include every input that affects the response in the cache key, or do not reflect unkeyed inputs. <br> - Disable caching for dynamic/personalised responses (`Cache-Control: no-store, private`). <br> - Strip or reject untrusted forwarding headers at the edge. <br> - Normalise cache keys and avoid trusting client-supplied Host overrides. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| PortSwigger Web Security Academy | https://portswigger.net/web-security/web-cache-poisoning |
| PortSwigger (Practical Cache Poisoning research) | https://portswigger.net/research/practical-web-cache-poisoning |
| OWASP: Cache Poisoning | https://owasp.org/www-community/attacks/Cache_Poisoning |
