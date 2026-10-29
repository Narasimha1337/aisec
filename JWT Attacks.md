### **JWT Attacks**

| **Aspect**                   | **Details**                                                                                                                                           |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Description**              | JSON Web Tokens (JWT) are signed, base64url-encoded tokens (`header.payload.signature`) used for stateless auth. Attacks target weak or missing signature verification so an attacker can forge or tamper with claims (e.g. flip `"role":"user"` to `"admin"`, change the `sub`/user id) and gain account takeover or privilege escalation. |
| **Conditions to be Vulnerable** | - Server does not verify the signature, or accepts `alg: none`. <br> - HMAC secret is weak/guessable. <br> - Server confuses algorithms (RS256 verified as HS256 using the public key as the HMAC key). <br> - `kid`, `jku`, or `x5u` header values are trusted without validation. |
| **Where to Find**            | - `Authorization: Bearer <jwt>` headers, cookies, or request bodies. <br> - SPA/API login flows, OAuth/OIDC id_tokens and access_tokens. <br> - Anywhere a three-part dot-separated base64 string appears. |
| **Common Exploits**          | - **alg=none**: strip the signature and set `"alg":"none"`. <br> - **Weak HS256 secret**: brute force then re-sign forged claims. <br> - **Algorithm confusion (RS256 to HS256)**: sign with the public key as the HMAC secret. <br> - **kid injection**: path traversal or SQLi in `kid` to point at a known key. <br> - **jku/x5u spoofing**: point the key URL at an attacker-hosted JWKS. |
| **Example**                  | Decode the token, change `{"user":"alice","role":"user"}` to `role":"admin"`, set the header to `{"alg":"none"}`, drop the signature, and replay. If accepted, you escalate to admin. |
| **How to Test**              | 1. Decode header/payload (base64url). 2. Try `alg:none` and an empty signature. 3. Crack HS256 with `hashcat -m 16500` against a wordlist (rockyou + jwt.secrets). 4. If RS256, attempt HS256 confusion using the server's public key. 5. Fuzz `kid`, `jku`, `x5u`. Use the **Burp JWT Editor** extension to automate signing and key attacks. |
| **Tools**                    | Burp Suite **JWT Editor** extension, `jwt_tool` (ticarpi), `hashcat -m 16500`, jwt.io for decoding (never paste production tokens into online tools). |
| **Mitigation**               | - Pin and enforce a single expected `alg`; reject `none`. <br> - Use strong random secrets (HS*) or proper key management (RS*/ES*). <br> - Validate `iss`, `aud`, `exp`, `nbf`. <br> - Do not trust attacker-controllable `kid`/`jku`/`x5u`; allowlist key sources. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| PortSwigger Web Security Academy | https://portswigger.net/web-security/jwt |
| OWASP JWT Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html |
| jwt_tool | https://github.com/ticarpi/jwt_tool |
| RFC 7519 (JWT) | https://www.rfc-editor.org/rfc/rfc7519 |
