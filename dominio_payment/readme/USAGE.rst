**Prerequisites**

- Configure the Dominio API credentials in the company form via ``dominio_base``.
- Install and configure ``dominio_fiscal`` and send the fiscal document to
  Dominio first (its ``state_dominio`` must be *Stored* or *Duplicated*).
- Optionally set the **Dominio Especie** field on each fiscal document type
  (**Fiscal > Configuration > Document Types**). When empty, the document type
  code is used as ``modelo`` (55 for NF-e, 65 for NFC-e, 03 for NFS-e).

---

**Sending a baixa from the invoice**

1. Open a paid invoice (``account.move``).
2. Click **Enviar Baixa Dominio** on the form header to submit every reconciled
   payment, or open the **Dominio Baixas** page and click **Enviar Baixa** on a
   specific payment line.
3. The ``dominio_state`` of each payment line updates to *Stored*,
   *Duplicated*, *Pending* or *Error*.

---

**Automatic baixa on fiscal document send**

When you click **Send to Dominio** on an invoice (or its fiscal document) that is
already paid, the related payment settlements are submitted automatically right
after the fiscal document is stored.
