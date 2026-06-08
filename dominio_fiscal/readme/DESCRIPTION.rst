Integrates Odoo **Fiscal Documents** (``l10n_br_fiscal.document``) and **Invoices**
(``account.move``) with the **Dominio** fiscal platform (Thomson Reuters).

Provides a **two-way integration**:

- **Send** fiscal documents from Odoo to Dominio (individually or in batch via fiscal closing).
- **Import** fiscal documents and invoices from Dominio into Odoo.

**Key features:**

- Individual "Send to Dominio" button on each fiscal document and invoice.
- Batch XML submission through the fiscal closing process.
- Import wizard to fetch documents from the Dominio API by company and date range.
- Automatic creation of fiscal documents (``l10n_br_fiscal.document``) and supplier
  invoices (``account.move``) from imported XMLs.
- Duplicate detection to avoid re-importing existing documents.
- ``state_dominio`` field tracking the delivery status (Stored / Duplicated / Error)
  directly on the document list and form views.
