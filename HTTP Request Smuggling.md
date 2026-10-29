### **HTTP Request Smuggling**

| **Aspect**                   | **Details**                                                                                                                                           |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Description**              | HTTP Request Smuggling happens when a front-end server (proxy, load balancer, CDN) and a back-end server disagree on where one request ends and the next begins. An attacker abuses this desync to prepend a hidden request to another user's traffic, leading to cache poisoning, request hijacking, credential capture, bypassed front-end controls, and stored XSS. |
| **Conditions to be Vulnerable** | - A request passes through at least two HTTP processors (front-end + back-end) that parse `Content-Length` and `Transfer-Encoding` differently. <br> - HTTP/1.1 keep-alive connections are reused between users. <br> - Front-end forwards both headers, or one server ignores chunked encoding. |
| **Where to Find**            | - Sites behind a CDN, reverse proxy, or WAF (Cloudflare, Akamai, AWS ALB, nginx, HAProxy). <br> - Endpoints reachable over HTTP/1.1. <br> - HTTP/2 downgrade paths where the front-end speaks h2 but forwards as h1 (H2.CL, H2.TE). |
| **Common Exploits**          | - **CL.TE**: front-end uses `Content-Length`, back-end uses `Transfer-Encoding: chunked`. <br> - **TE.CL**: back-end uses `Content-Length`, front-end uses chunked. <br> - **TE.TE**: both support chunked but one is fooled by an obfuscated `Transfer-Encoding` header (e.g. `Transfer-Encoding: xchunked`). <br> - **H2.CL / H2.TE**: HTTP/2 to HTTP/1.1 downgrade smuggling. |
| **Example**                  | A `CL.TE` payload where `Content-Length` covers the whole body but a chunked terminator (`0\r\n\r\n`) ends the request early on the back-end, leaving `GET /admin` queued to prefix the next visitor's request. |
| **How to Test**              | 1. Use Burp Suite **HTTP Request Smuggler** extension to auto-detect CL.TE/TE.CL desyncs. <br> 2. Send a timing-based probe: a malformed chunked body that makes the back-end wait for more data causes a measurable delay. <br> 3. Confirm with a differential response: smuggle a request and verify the prefix lands on a second normal request. Always test against your own session first to avoid hitting other users. |
| **Tools**                    | Burp Suite (Repeater with "Update Content-Length" off, HTTP Request Smuggler extension), `smuggler.py` (defparam), `h2csmuggler`, `turbo intruder`. |
| **Mitigation**               | - Use HTTP/2 end to end and reject downgraded ambiguous requests. <br> - Make front-end and back-end normalise/reject conflicting `Content-Length` + `Transfer-Encoding`. <br> - Disable connection reuse to the back-end, or close the connection on any malformed header. <br> - Reject requests that contain both length headers per RFC 7230. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| PortSwigger Web Security Academy | https://portswigger.net/web-security/request-smuggling |
| PortSwigger (HTTP/2 desync) | https://portswigger.net/research/http2 |
| OWASP WSTG: HTTP Splitting/Smuggling | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/15-Testing_for_HTTP_Splitting_Smuggling |
| smuggler.py | https://github.com/defparam/smuggler |
