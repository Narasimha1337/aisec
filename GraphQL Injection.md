### **GraphQL Injection and Abuse**

| **Aspect**                   | **Details**                                                                                                                                           |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Description**              | GraphQL exposes a single flexible endpoint where clients shape their own queries. Attacks abuse introspection to map the schema, then exploit missing authorization, injection sinks behind resolvers, and the lack of query-cost limits. Common outcomes: data exposure, IDOR/BOLA through object fields, injection (SQL/NoSQL/command) inside resolver arguments, and denial of service via nested or batched queries. |
| **Conditions to be Vulnerable** | - Introspection enabled in production. <br> - Authorization enforced per-endpoint instead of per-field/per-object. <br> - Resolver arguments flow unsanitised into a database, OS command, or downstream API. <br> - No query depth, complexity, or rate limiting; aliasing/batching allowed. |
| **Where to Find**            | - `/graphql`, `/graphiql`, `/api/graphql`, `/v1/graphql`, `/query`. <br> - SPAs and mobile apps issuing POST bodies with `query` and `variables`. <br> - Endpoints returning `errors[].message` that leak field names. |
| **Common Exploits**          | - **Introspection dump** (`__schema`, `__type`) to recover the full schema even when disabled-looking. <br> - **Field-level IDOR/BOLA**: request another user's object by id. <br> - **Injection**: SQLi/NoSQLi/command injection inside filter or search arguments. <br> - **DoS**: deeply nested queries or thousands of aliases in one request. <br> - **Batching brute force**: many aliased mutations (e.g. login/OTP) bypass per-request rate limits. |
| **Example**                  | `query{__schema{types{name fields{name}}}}` to map the schema, then `query{user(id:2){email password}}` to read another user's fields, or 100 aliased `login` calls in one POST to brute force OTP under the rate limit. |
| **How to Test**              | 1. Send an introspection query; if blocked, try suggestions in error messages and field-name guessing. 2. Use **GraphQL Voyager / InQL** to visualise the schema. 3. Replay sensitive queries with another object's id to test authorization. 4. Inject `' OR 1=1`, `{"$ne":null}`, and `;id` into string args. 5. Test deep nesting and alias batching for cost limits. |
| **Tools**                    | Burp Suite **InQL** extension, `graphw00f` (engine fingerprint), `clairvoyance` (schema recovery without introspection), GraphQL Voyager, `graphql-cop`. |
| **Mitigation**               | - Disable introspection and field suggestions in production. <br> - Enforce authorization at the resolver/field level, not just the endpoint. <br> - Parameterise queries and validate resolver inputs. <br> - Apply query depth/complexity limits, disable or cap aliasing/batching, and rate limit. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| PortSwigger Web Security Academy | https://portswigger.net/web-security/graphql |
| OWASP GraphQL Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html |
| OWASP WSTG: Testing GraphQL | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/12-API_Testing/01-Testing_GraphQL |
| InQL (Burp extension) | https://github.com/doyensec/inql |
