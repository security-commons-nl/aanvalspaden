# Uitdraai kritieke applicaties, kwartaal 3

Bron: CMDB, export van 2026-08-28. Kolomnamen zoals het beheersysteem ze levert.

| Applicatie | Verantwoordelijke | Netwerksegment | Backupsoort | Hersteltijd | Max. dataverlies |
|---|---|---|---|---|---|
| Paspoortuitgifte | Teamleider Burgerzaken | VLAN 42 / 10.20.42.0/24 | immutable + offsite | 4 uur | 1 uur |
| Uitkeringsadministratie | Afdelingshoofd Werk en Inkomen | VLAN 44 / 10.20.44.0/24 | immutable + offsite | 8 uur | 4 uur |
| Financieel systeem | Concerncontroller | VLAN 46 / 10.20.46.0/24 | snapshot + tape | 24 uur | 12 uur |

Licentie Office 365, contractnummer 2026-114, loopt tot 31-12-2027. Geen applicatie in deze zin.
