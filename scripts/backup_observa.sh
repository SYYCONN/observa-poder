#!/bin/sh
# Encrypt a logical backup to an age recipient. Run from the project directory.
set -eu
umask 077
env_file=${1:?Informe o arquivo de ambiente de produção}
recipient=${2:?Informe o destinatário público age}
destination=${3:?Informe o destino externo do backup .dump.age}
case "$destination" in *.dump.age) ;; *) exit 2 ;; esac
if [ -e "$destination" ]; then
    printf '%s\n' "O arquivo de destino já existe." >&2
    exit 2
fi
work="$(mktemp -d "${destination}.XXXXXXXX")"
trap 'rm -f "$work/dump.age"; rmdir "$work"' EXIT
fifo="$work/dump"
mkfifo "$fifo"
trap 'rm -f "$fifo" "$work/dump.age"; rmdir "$work"' EXIT
docker compose --env-file "$env_file" -f compose.production.yaml exec -T --user postgres db \
    pg_dump --no-owner --no-privileges --format=custom -U observa_bootstrap -d observa > "$fifo" &
dump_pid=$!
if ! age -r "$recipient" -o "$work/dump.age" < "$fifo"; then
    wait "$dump_pid" || true
    exit 1
fi
wait "$dump_pid"
ln "$work/dump.age" "$destination"
