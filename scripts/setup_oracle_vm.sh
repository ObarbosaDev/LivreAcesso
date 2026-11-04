#!/usr/bin/env bash
# Bootstrap do Livre Acesso 100% na VM gratuita da Oracle:
# Supabase self-hosted (Postgres + Auth + PostgREST) atras do Kong,
# Caddy fazendo TLS, e os containers da API/worker/frontend do proprio repo.
#
# Execute como usuario com acesso a Docker, a partir da raiz do repositorio
# JA CLONADO na VM. Idempotente: pode ser executado de novo apos uma falha.
#
# Nao versiona nem imprime segredos. Variaveis de dominio/e-mail sao lidas
# do ambiente ou perguntadas interativamente.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK_DIR="$REPO_ROOT/.supabase-stack"
SUPABASE_REF="${SUPABASE_UPSTREAM_REF:-master}"
COMPOSE_FILES=(
  -f "$STACK_DIR/docker-compose.yml"
  -f "$REPO_ROOT/supabase/self-hosted/docker-compose.override.yml"
  -f "$REPO_ROOT/docker-compose.oracle.yml"
)
COMPOSE=(docker compose -p livreacesso "${COMPOSE_FILES[@]}" --env-file "$STACK_DIR/.env")

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Comando obrigatorio ausente: $1" >&2
    exit 1
  }
}

ask_if_unset() {
  local var_name="$1" prompt="$2"
  if [ -z "${!var_name:-}" ]; then
    read -r -p "$prompt: " value
    export "$var_name"="$value"
  fi
}

echo "== 1. Dependencias =="
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo "Docker instalado. Saia e entre na sessao SSH de novo antes de continuar."
  exit 0
fi
require_cmd git
require_cmd curl
require_cmd openssl

echo "== 2. Dominios e e-mail do ACME =="
ask_if_unset APP_DOMAIN "Dominio do frontend (ex: app.seudominio.org)"
ask_if_unset API_DOMAIN "Dominio da API (ex: api.seudominio.org)"
ask_if_unset GATEWAY_DOMAIN "Dominio do gateway Supabase (ex: db.seudominio.org)"
ask_if_unset ACME_EMAIL "E-mail para o certificado TLS (Let's Encrypt)"

echo "== 3. Stack oficial do Supabase (self-hosted) =="
if [ ! -d "$STACK_DIR" ]; then
  tmp_clone="$(mktemp -d)"
  git clone --depth 1 --branch "$SUPABASE_REF" https://github.com/supabase/supabase.git "$tmp_clone"
  cp -r "$tmp_clone/docker" "$STACK_DIR"
  rm -rf "$tmp_clone"
fi

cd "$STACK_DIR"
if [ ! -f .env ]; then
  cp .env.example .env
  bash utils/generate-keys.sh --update-env
  bash utils/add-new-auth-keys.sh --update-env
  echo "Chaves geradas em $STACK_DIR/.env. NUNCA copie este arquivo para o Git."
else
  echo "$STACK_DIR/.env ja existe; mantendo chaves geradas anteriormente."
fi

{
  echo "APP_DOMAIN=$APP_DOMAIN"
  echo "API_DOMAIN=$API_DOMAIN"
  echo "GATEWAY_DOMAIN=$GATEWAY_DOMAIN"
  echo "ACME_EMAIL=$ACME_EMAIL"
} >>.env
sort -u -t= -k1,1 .env -o .env

cd "$REPO_ROOT"

echo "== 4. Subindo db, auth, rest, kong, caddy =="
"${COMPOSE[@]}" up -d db
echo "Aguardando o Postgres aceitar conexoes..."
until "${COMPOSE[@]}" exec -T db pg_isready -U postgres >/dev/null 2>&1; do
  sleep 2
done

echo "== 5. Aplicando migrations do Livre Acesso =="
for migration in "$REPO_ROOT"/supabase/migrations/*.sql; do
  echo "  -> $(basename "$migration")"
  "${COMPOSE[@]}" exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d postgres <"$migration"
done

echo "== 6. Subindo Auth, PostgREST, Kong e Caddy =="
"${COMPOSE[@]}" up -d auth rest kong caddy

echo "== 7. Build e subida da API, worker e frontend =="
"${COMPOSE[@]}" up -d --build api communication-worker frontend

cat <<'EOF'

== Falta fazer manualmente ==
1. Apontar o DNS de APP_DOMAIN, API_DOMAIN e GATEWAY_DOMAIN para o IP publico da VM.
2. Preencher .env.oracle.local na raiz do repo com SUPABASE_URL=https://$GATEWAY_DOMAIN,
   SUPABASE_PUBLISHABLE_KEY (valor de ANON_KEY em .supabase-stack/.env) e
   SUPABASE_SERVICE_ROLE_KEY (valor de SERVICE_ROLE_KEY em .supabase-stack/.env).
3. Criar a primeira conta pelo endpoint de signup do Auth e promover esse usuario
   a coordenador seguindo supabase/README.md ("Primeiro coordenador").
4. Rodar: python scripts/validate_oracle_env.py
   e depois: python scripts/verify_oracle_deployment.py --api-url https://$API_DOMAIN --frontend-url https://$APP_DOMAIN
EOF
