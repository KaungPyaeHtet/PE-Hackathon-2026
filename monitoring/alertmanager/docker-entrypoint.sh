#!/bin/sh
# Renders Alertmanager config with Discord webhook URL from env.
# Called by docker-compose; use .env for DISCORD_WEBHOOK_URL (never commit secrets).
set -e

TEMPLATE_FILE=/etc/alertmanager/alertmanager.yml
RENDERED_FILE=/tmp/alertmanager.yml

raw="${DISCORD_WEBHOOK_URL:-}"
# Strip CRLF, trim spaces, optional surrounding " or '
url=$(printf '%s' "$raw" | tr -d '\r\n' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")

if [ -z "$url" ]; then
  echo "alertmanager: DISCORD_WEBHOOK_URL is empty — add your webhook to .env, then: docker compose up -d alertmanager"
  url='https://discord.com/api/webhooks/0/invalid'
elif
  case "$url" in *YOUR_ID*|*YOUR_TOKEN*) true ;; *) false ;; esac
then
  echo "alertmanager: DISCORD_WEBHOOK_URL still looks like a placeholder — paste a real Discord webhook URL"
  url='https://discord.com/api/webhooks/0/invalid'
fi

# Escape URL for safe sed replacement.
escaped_url=$(printf '%s' "$url" | sed -e 's/[\/&]/\\&/g')
sed "s/__DISCORD_WEBHOOK_URL__/$escaped_url/g" "$TEMPLATE_FILE" > "$RENDERED_FILE"
chmod 0600 "$RENDERED_FILE" 2>/dev/null || true
echo "alertmanager: Discord webhook configured ($(printf '%s' "$url" | wc -c | tr -d ' ') bytes, no URL logged)."

exec /bin/alertmanager \
  --config.file="$RENDERED_FILE" \
  --storage.path=/alertmanager \
  --web.listen-address=0.0.0.0:9093 \
  "$@"
