# Windows code signing — Azure Artifact Signing

How the Windows binaries (`flatcam.exe` and the Inno Setup installer) are
signed, and how to set it up. We use **Azure Artifact Signing** (formerly
"Trusted Signing"), a Microsoft-managed signing service, under the organization
**eicauvelais.be**.

## Why this choice

- **Organization identity**: the binaries are published as the institution
  (`eicauvelais.be`), so the maintainer's personal legal name is **not** exposed
  in the certificate (unlike an individual Certum OV cert).
- **CI-friendly**: signed in GitHub Actions via the official
  [`azure/trusted-signing-action`](https://github.com/azure/trusted-signing-action),
  a single stable step (no fragile UI automation).
- **Cost**: Basic plan ~US$10/month (5000 signatures/month).
- **SmartScreen**: reputation is tied to the Microsoft-verified identity, so it
  builds faster than a plain OV cert. Note: this is *not* an EV cert, so the
  SmartScreen prompt may still appear until enough download reputation accrues.

Eligibility: Public Trust is available to organizations in the EU (Belgium ✓).
Individual developers are limited to US/Canada — hence signing via the org.

---

## One-time setup (Azure portal, done by a tenant admin)

> Prerequisites: admin on the `eicauvelais.be` Entra tenant, and an **Azure
> subscription** under it (create a pay-as-you-go one if needed; check Azure for
> Education credits). The billing/identity type must be **Organization**.

### 1. Register the resource provider
Subscriptions → (your subscription) → Resource providers → search
`Microsoft.CodeSigning` → **Register**.

### 2. Create the Artifact Signing account
Search "Artifact Signing Accounts" → **Create**:
- Resource group: e.g. `rg-flatcam-signing`
- Account name: e.g. `flatcam-signing` (3-24 alphanum, globally unique)
- **Region: West Europe** (endpoint `https://weu.codesigning.azure.net`)
- Pricing: **Basic**

### 3. Grant yourself the identity-verifier role
On the account → Access control (IAM) → add role
**`Artifact Signing Identity Verifier`** to your user (needed to create the
identity validation; otherwise the "New identity" button is greyed out).

### 4. Create the organization identity validation  ← longest step
On the account → Objects → **Identity validations** → select **Organization** →
**New Identity** → **Public**. Fill in the institution's **legal** details:
- Organization name = legal business entity (appears on the cert)
- Website URL, primary + secondary email (same domain), business identifier,
  full business address
- First/Last name of the representative (exact match to their government ID)

Then: email verification (link valid 7 days) + the representative completes a
**Verified ID** check (AU10TIX, via Microsoft Authenticator on mobile).

> **Processing: 1 to 20 business days.** Start this first. Make sure public
> records / business registration are current to speed it up.

### 5. Create the certificate profile
Once identity validation is **Completed**: account → Objects → **Certificate
profiles** → **Create** → type **Public Trust**:
- Profile name: e.g. `flatcam-public-trust`
- "Verified CN and O": select the completed identity validation
- Leave street/postal unchecked (less personal data on the cert)

### 6. Service principal for CI
Create an Entra **App registration** (e.g. `flatcam-ci-signing`) with a client
secret (or, preferred, an OIDC federated credential — no stored secret).
On the Artifact Signing account → IAM → assign role
**`Trusted Signing Certificate Profile Signer`** to that app.

### 7. GitHub repository secrets
Add under Settings → Secrets and variables → Actions:
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET` (omit if using OIDC federated credentials)
- `AZURE_SUBSCRIPTION_ID`

### 8. Values to hand off for the workflow
Note these for the CI step:
- **Endpoint**: `https://weu.codesigning.azure.net`
- **Account name**: (step 2)
- **Certificate profile name**: (step 5)

---

## CI integration (added once the resource exists)

A signing step using `azure/trusted-signing-action` will be added to
[release.yml](../.github/workflows/release.yml) to sign **`flatcam.exe`**
(before zipping/installer build) and the **`...-setup.exe`** installer, using
the endpoint/account/profile above and the `AZURE_*` secrets.

## Status

- [ ] Azure subscription under eicauvelais.be
- [ ] Artifact Signing account (West Europe)
- [ ] Organization identity validation **Completed**
- [ ] Certificate profile (Public Trust)
- [ ] Service principal + role + GitHub secrets
- [ ] CI signing step wired in release.yml
