To configure the Dominio API integration:

1. Go to **Fiscal > Configuration > Company** and select your company.
2. Open the **Accounting Integration** tab.
3. Fill in the fields:

   - **Environment**: Choose between *Production* or *Homologation*.
   - **Client ID Token**: The OAuth2 client identifier provided by Dominio.
   - **Client Secret Token**: The OAuth2 client secret provided by Dominio.
   - **Integration Production Token**: The integration key for the production environment.
   - **Integration Homologation Token**: The integration key for the homologation environment.

The authentication methods (token generation, key activation, customer verification)
are consumed automatically by ``dominio_fiscal`` and other dependent modules —
no further manual steps are required.
