### **Insecure Object Storage**

| **Aspect** | **Details** |
|---|---|
| **Description** | Cloud object storage (S3, Azure Blob, GCS) is misconfigured so buckets or objects are world-readable, writable, or listable. This exposes sensitive files and can allow tampering or content injection. |
| **Conditions to be Vulnerable** | - Public-read or public-list bucket ACLs/policies. <br> - Public-write permissions allowing uploads/overwrites. <br> - Predictable bucket names and no access logging. |
| **Where to Find** | - Asset, upload, and backup buckets referenced in HTML/JS. <br> - `*.s3.amazonaws.com`, `*.blob.core.windows.net`, `storage.googleapis.com` URLs. |
| **Common Exploits** | - Listing and downloading private files from a public bucket. <br> - Uploading or overwriting objects to deface or inject malicious content. <br> - Recovering secrets or PII from exposed backups. |
| **Example** | `https://app-backups.s3.amazonaws.com/` returns an XML listing of objects, and `aws s3 ls s3://app-backups --no-sign-request` lets an anonymous user enumerate and pull database dumps. |
| **How to Test** | 1. Identify bucket URLs from page source and DNS. <br> 2. Test anonymous list/read/write with the AWS CLI `--no-sign-request` (or equivalent). <br> 3. Enumerate candidate bucket names and check ACLs/policies. |
| **Tools** | AWS CLI, s3scanner, cloud_enum, Burp Suite, nuclei |
| **Mitigation** | - Block public access and apply least-privilege bucket policies. <br> - Disable anonymous list/read/write; use signed URLs for sharing. <br> - Enable logging, encryption, and regular configuration audits. |

---

## Resources

| **Credit** | **URL** |
|---|---|
| OWASP WSTG - Testing Cloud Storage | https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/11-Test_Cloud_Storage |
| OWASP Top 10 - Security Misconfiguration | https://owasp.org/Top10/A05_2021-Security_Misconfiguration/ |
| HackTricks - AWS S3 | https://cloud.hacktricks.wiki/en/pentesting-cloud/aws-security/aws-services/aws-s3-athena-and-glacier-enum.html |
