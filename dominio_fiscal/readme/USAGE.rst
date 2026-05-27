**Prerequisites**

Before using this module, configure the Dominio API credentials in the company form
via the ``dominio_base`` module: **Company > Accounting Integration** tab.

---

**Sending a fiscal document to Dominio (individual)**

1. Open a fiscal document (**Fiscal > Documents > NF-e / NFS-e / CT-e**).
2. Click the **Send to Dominio** button on the form header.
3. The ``state_dominio`` field will update to *Stored*, *Duplicated*, or *Error*.

The same button is also available directly from **Invoices** (``account.move``).

---

**Sending documents in batch via fiscal closing**

1. Go to **Fiscal > Period Closing** and open or create a closing period.
2. The batch send is triggered automatically by the closing workflow;
   all documents in the period are submitted to the Dominio API.

---

**Importing documents from Dominio**

1. Go to **Fiscal > Documents > Dominio > Import from Dominio**.
2. Select the **Company**, **From** date, and **To** date.
3. Click **Import**.
4. After processing, the wizard displays:

   - **Imported**: number of successfully imported documents.
   - **Skipped**: number of documents already existing (duplicate detection by
     ``document_key``).
   - **Errors**: number of documents that failed to import.

For supplier documents (NFe with ``emit`` CNPJ different from the company), an
``account.move`` invoice is automatically created alongside the fiscal document.
