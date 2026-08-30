# Despregue en produción (Raspberry Pi)

Stack completo (`db` + `api` + `web`) para correr na Pi con imaxes
precompiladas en GHCR (GitHub Container Registry). A Pi non compila nada:
só descarga as imaxes e arranca.

- Web: `http://192.168.1.155:3000`
- API: `http://192.168.1.155:8000` (health en `/api/health`)

## Requisitos na Pi

- Raspberry Pi 4/5 con OS de 64 bits (`uname -m` → `aarch64`).
- Docker Engine + compose plugin:
  `curl -fsSL https://get.docker.com | sh` e engade `pi` ao grupo `docker`.
- IP fixa (192.168.1.155) configurada no router (DHCP reservation).

## Primeiro despregue

```bash
sudo mkdir -p /opt/granxa
sudo chown pi:pi /opt/granxa
cp -r <repo-api>/deploy/* /opt/granxa/
cd /opt/granxa
cp .env.example .env
# edita .env: POSTGRES_PASSWORD e JWT_SECRET (openssl rand -hex 32)
chmod +x deploy.sh backup.sh restore.sh
./deploy.sh
```

O primeiro `./deploy.sh` descarga as imaxes (tarda uns minutos). Os
seguintes son case instantáneos (só descargan as capas que cambiaron).

## Acceso ás imaxes GHCR

As imaxes `ghcr.io/samuvlad/granxa-api` e `ghcr.io/samuvlad/granxa-web`
son privadas por defecto. Dúas opcións:

1. **Facer públicas** (sinxelo): en GitHub → teu paquete → Package
   settings → change visibility → public. Entón a Pi non necesita login.
2. **Login con PAT**: crea un Personal Access Token con permiso
   `read:packages` e na Pi:
   `echo "$TOKEN" | docker login ghcr.io -u samuvlad --password-stdin`

## Despregar unha nova versión

Cada push a `master` de calquera dos dous repos constrúe e publica a
imaxe en GHCR (workflows `api.yml` e `web.yml`). Para actualizar a Pi:

```bash
cd /opt/granxa
./deploy.sh
```

`RUN_MIGRATIONS=1`: a API executa `alembic upgrade head` no arranque.

## Backups horarios

O script `backup.sh` fai `pg_dump -Fc` de `granxa_maps` a
`/opt/granxa/backups/` e rota: conserva 48 horarios + 14 diarios (00:00).

Instalar o cron (unha vez):

```bash
sudo tee /etc/cron.d/granxa-backup >/dev/null <<'EOF'
0 * * * * pi /opt/granxa/backup.sh >> /opt/granxa/backups/backup.log 2>&1
EOF
```

Proba a restauración cun dump recente sobre unha BD temporal antes de
confiar nel:

```bash
cd /opt/granxa
# exemplo sobre BD temporal
docker compose -f docker-compose.prod.yml exec -T db \
    createdb -U granxa granxa_restore_test
docker compose -f docker-compose.prod.yml exec -T db \
    pg_restore -U granxa -d granxa_restore_test < backups/granxa_$(ls backups | tail -1)
```

`restore.sh` fai o mesmo sobre a BD real (pide confirmación).

## Cambiar a IP da web

`NEXT_PUBLIC_API_URL` (a URL que o navegador usa para chamar á API) é
**build-time**: inxectase no CI desde a variable de repo de GitHub
(`Settings → Secrets and variables → Actions` → variable
`NEXT_PUBLIC_API_URL=http://192.168.1.155:8000`). Se cambia a IP,
actualiza a variable, fai un push calquera a `master` e volve a
`./deploy.sh` na Pi.