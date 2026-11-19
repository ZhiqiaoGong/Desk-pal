#!/bin/zsh
unsetopt BG_NICE
cd -- "${0:A:h}" || exit 1
umask 077
key_dir="$HOME/Library/Application Support/ChestnutPal"
key_file="$key_dir/gemini-api-key"

if ! mkdir -p -- "$key_dir"; then
  print -u2 '无法创建小栗的本机配置目录。'
  exit 1
fi

if [[ -L "$key_file" || ( -e "$key_file" && ! -f "$key_file" ) ]]; then
  print -u2 '密钥文件路径异常，请检查小栗的本机配置目录。'
  exit 1
fi

if [[ ! -s "$key_file" || ${1:-} == --reset-key ]]; then
  printf '请粘贴 Gemini API Key，然后按回车（输入不会显示）：'
  IFS= read -rs new_key
  printf '\n'
  if [[ -z "$new_key" || "$new_key" == *[[:space:]]* ]]; then
    print -u2 '密钥为空或包含空白字符，请重新打开启动器。'
    exit 1
  fi
  key_temp=$(mktemp "$key_dir/.gemini-api-key.XXXXXX") || exit 1
  if ! printf '%s\n' "$new_key" > "$key_temp" || ! mv -f -- "$key_temp" "$key_file"; then
    rm -f -- "$key_temp"
    print -u2 '无法保存密钥。'
    exit 1
  fi
  unset new_key
fi

chmod 600 "$key_file" || exit 1
IFS= read -r GEMINI_API_KEY < "$key_file"
if [[ -z "$GEMINI_API_KEY" ]]; then
  print -u2 '无法读取密钥。'
  exit 1
fi
export GEMINI_API_KEY CHAT_PROVIDER=gemini PORT=8765
export GEMINI_CHAT_PROFILE=primary GEMINI_CHAT_THINKING_LEVEL=low
unset PAL_MOCK_AI PAL_DB

address="http://127.0.0.1:$PORT"
if /usr/bin/curl -fsS --max-time 1 "$address/api/health" >/dev/null 2>&1; then
  exec /usr/bin/open "$address/"
fi

(
  for attempt in {1..30}; do
    if /usr/bin/curl -fsS --max-time 1 "$address/api/health" >/dev/null 2>&1; then
      /usr/bin/open "$address/"
      break
    fi
    sleep 0.3
  done
) &
exec python3 server.py
