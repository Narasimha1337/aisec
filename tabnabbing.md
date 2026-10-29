### **Reverse Tabnabbing**

| **Aspect** | **Details** |
|---|---|
| **Description** | Reverse tabnabbing happens when a page opens a link in a new tab and the destination gains access to the opener via `window.opener`. The malicious destination can silently navigate the original tab to a phishing page while the victim is on the new tab. |
| **Conditions to be Vulnerable** | - A link or `window.open` opens external content in a new tab/window. <br> - The link lacks `rel="noopener"` (and ideally `noreferrer`). <br> - The destination URL can be attacker-influenced (user content, redirects). |
| **Where to Find** | - User-generated links in comments, profiles, forums, messages. <br> - `target="_blank"` anchors and `window.open()` calls to external sites. |
| **Common Exploits** | - The opened page runs `window.opener.location = 'https://phish.example'` to swap the original tab to a fake login. <br> - Phishing that abuses the user's trust in the already-open legitimate tab. |
| **Example** | A page links `<a href="https://evil.com" target="_blank">click</a>` without `rel="noopener"`. On `evil.com`: `if (window.opener) window.opener.location = 'https://app.com.evil.com/login';` redirects the victim's first tab. |
| **How to Test** | 1. Find `target="_blank"` links and `window.open` calls; check for `rel="noopener"`. <br> 2. Open a controlled destination and test whether `window.opener` is non-null. <br> 3. From the destination, attempt `window.opener.location` reassignment. Authorized targets only. |
| **Tools** | Browser dev tools, Burp Suite, custom HTML PoC page |
| **Mitigation** | - Add `rel="noopener noreferrer"` to all `target="_blank"` links. <br> - For `window.open`, null the opener (`win.opener = null`) or pass `noopener`. <br> - Modern browsers default to noopener for `_blank`, but enforce it explicitly. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP Cheat Sheet - HTML5 Security (Tabnabbing) | https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html |
| MDN - rel=noopener | https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/rel/noopener |
| OWASP - Reverse Tabnabbing | https://owasp.org/www-community/attacks/Reverse_Tabnabbing |
