# plusconnect

Kostra řešení pro synchronizaci Previo ↔ Loxone, multi‑hotel, s cron syncem, MySQL state a dashboardem.

## Struktura
- `www/plusconnect/` – kód synchronizace a API skeleton.
  - `sync.py` – CLI vstup pro cron.
  - `plusconnect/clients/` – klienti pro Previo XML/REST a Loxone.
  - `plusconnect/services/` – sync logika, health checker, state store.
  - `plusconnect/api/` – FastAPI skeleton pro dashboard.
  - `dashboard/` – statický UI (dark theme, akcent rgb(181,225,38)).
- `schemas.sql` – MySQL tabulky pro state, logy a health.
- `sample_config.yaml`, `sample_db.yaml` – vzory konfigurace.

## Rychlý postup nasazení
1) **Připrav strukturu na VPS** (doporučené umístění, příklad hotel_id `moravskygrunt`):
```
/opt/plusconnect/app/      # kód repozitáře (sync.py, requirements.txt, …)
/opt/plusconnect/secret/<hotel>/config/   # config.yaml, db.yaml (tajemství mimo kód)
/opt/plusconnect/logs/     # logy cronu
```
Vytvoření složek jedním příkazem:
```
sudo mkdir -p /opt/plusconnect/app /opt/plusconnect/secret/<hotel>/config /opt/plusconnect/logs && sudo chown -R $(whoami):$(whoami) /opt/plusconnect
```
```
/opt/plusconnect/secret/<hotel>/config/config.yaml
/opt/plusconnect/secret/<hotel>/config/db.yaml
```
Vyplň je dle `sample_config.yaml` a `sample_db.yaml`.
Do `config.yaml` přidej také `previo_hotel_id` (např. 747998).

2) **Vytvoř DB tabulky**:
```
mysql -u <user> -p plusconnect < schemas.sql
```

3) **Nainstaluj závislosti** (Python 3.10+, např. venv):
```
pip install -r requirements.txt
```

4) **Otestuj ručně sync** (v adresáři `/opt/plusconnect/app`, příklad hotel_id `moravskygrunt`):
```
python sync.py --config /opt/plusconnect/secret/moravskygrunt/config/config.yaml --db-config /opt/plusconnect/secret/moravskygrunt/config/db.yaml --hotel-id moravskygrunt
```

5) **Cron každých 5 minut**:
```
*/5 * * * * /opt/plusconnect/app/.venv/bin/python /opt/plusconnect/app/sync.py --config /opt/plusconnect/secret/moravskygrunt/config/config.yaml --db-config /opt/plusconnect/secret/moravskygrunt/config/db.yaml --hotel-id moravskygrunt >> /opt/plusconnect/logs/sync.log 2>&1
```

6) **Dashboard**:
- Frontend: statické soubory v `www/plusconnect/dashboard/`.
- API: `plusconnect/api/main.py` (FastAPI skeleton) – přidej autorizaci tokenem/key a napojení na DB tabulky `service_health`, `sync_runs`, `sync_logs`.

## Doplň co zbývá
- Implementace Previo XML `search_reservations` + mapování na `Reservation`.
- Napojení dashboard API na DB.
- Řešení storno/expirace podle `expiration_action`.
- Doplnění deployment skriptů dle hostingu.
