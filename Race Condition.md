### **Race Condition**

| **Aspect** | **Details** |
|---|---|
| **Description** | A race condition occurs when concurrent requests hit a time-of-check-to-time-of-use (TOCTOU) gap, letting an operation execute more times than the logic intended. It commonly breaks limits on redemptions, withdrawals, votes, and one-time actions. |
| **Conditions to be Vulnerable** | - A check and an update are not performed atomically. <br> - No locking, unique constraints, or idempotency on sensitive operations. <br> - The action has measurable value when repeated (balance, coupon, quota). |
| **Where to Find** | - Coupon/gift-card redemption, balance transfers, withdrawals. <br> - Account actions: registration, voting, like/follow, OTP validation, file uploads. |
| **Common Exploits** | - Applying a single-use coupon multiple times for extra discount. <br> - Withdrawing or transferring funds beyond the actual balance (double-spend). |
| **Example** | Send 30 parallel `POST /api/redeem {"code":"SAVE50"}` requests using HTTP/2 single-packet attack (Burp Turbo Intruder). Several succeed before the "already used" flag is written, applying the discount repeatedly. |
| **How to Test** | 1. Identify a limited or one-time action and capture the request. <br> 2. Fire many concurrent copies with Turbo Intruder (single-packet attack) or a parallel script. <br> 3. Check whether the action succeeded more than its allowed count. Authorized targets only. |
| **Tools** | Burp Suite (Turbo Intruder, Repeater parallel), ffuf, custom Go/Python scripts |
| **Mitigation** | - Make check-and-update atomic via DB transactions, row locks, or `SELECT ... FOR UPDATE`. <br> - Enforce uniqueness/idempotency keys on sensitive operations. <br> - Rate-limit and serialize per-user critical actions. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| PortSwigger - Race conditions | https://portswigger.net/web-security/race-conditions |
| OWASP WSTG - Testing for the Circumvention of Work Flows | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/06-Testing_for_the_Circumvention_of_Work_Flows |
| HackTricks - Race Condition | https://book.hacktricks.wiki/en/pentesting-web/race-condition.html |
