This module provides the base integration with the **Dominio** API (Thomson Reuters).

It extends the **res.company** model with the necessary credentials and authentication
methods to connect to the Dominio fiscal platform, including:

- OAuth2 client credentials (client ID and secret) for token generation
- Environment selection (Production / Homologation) with separate integration keys
- Integration key activation and customer authorization verification endpoints

All authentication flows required by other Dominio modules (such as ``dominio_fiscal``)
are centralized here, providing a single configuration point per company.
