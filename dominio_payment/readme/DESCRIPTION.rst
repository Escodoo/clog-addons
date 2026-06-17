Integrates Odoo **payment settlements** with the **Dominio** fiscal platform
(Thomson Reuters), sending the *baixa de parcelas* (installment write-off) XML
to the Dominio API.

Builds on ``dominio_fiscal``: once a fiscal document has been delivered to
Dominio and its invoice is paid, the corresponding payment settlement is sent
following the Dominio *Baixas* layout (entrada, saída and serviço).

**Key features:**

- ``Enviar Baixa Dominio`` button on the invoice (``account.move``) header.
- A **Dominio Baixas** page on the invoice listing every reconciled payment
  line (from the payment wizard or from a bank statement reconciliation) with a
  per-line **Enviar Baixa** button and delivery status.
- Automatic baixa submission right after the fiscal document is sent when the
  invoice is already paid.
- The baixa XML is built by string following the Dominio layout and submitted to
  the same ``batches`` endpoint used for fiscal documents.
- ``dominio_state`` field tracking the delivery status (Stored / Duplicated /
  Pending / Error) on each payment line, plus event logging.
