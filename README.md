# Mock shipment server

This Mock Server is used to track shipment details, for TrustMesh the Shipment server is critical and extremely important, and it is used as a source of truth although TrustMesh avoid to trust the server blindly, it can't detect disruption or alterations of shipment server unless it has some history to refer to

## Security

To mitigate risk TrustMesh avoid to blindly trust the shipment server, and this helps avoid common issues like server tampering or scams
Her is a list of possible scenarios with explaination on how TrustMesh deals with it:

- State tampering: A shipment state was set to IN_TRANSIT in last request but the current request give use CREATED as response. This shows signs of server side tampering which means either an attack on server side or an error correction from the server admin but we can't be sure so TrustMesh cancels the escrow related to that specific shipment

- Wrong Shipment to Escrow: whether this is intentional or not the user gets a window time of N hours to confirm shipment, it can either dispute it or confirm release ahead of time(on reception). That window time avoids Release of Funds onn the fact the the shipment was delivered

- single shipment to Multiple Escrow: The smart contract explicit avoid assigning the same shipment id to multiple escrow. This is to avoid issues like Wrong shipment to Escrow and other issues that can be refered to as scam tentatives



Although in this demo the feedback server is a source of Truth, in production having multiple source of truth that are independant(oracle) and peform some additionnal checks to make it more secure


to start server: uvicorn main:app