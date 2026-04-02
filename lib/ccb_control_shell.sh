#!/usr/bin/env bash

_ccb_control_targets_raw="${CCB_CONTROL_TARGETS:-gemini claude codex}"
read -r -a _CCB_CONTROL_TARGETS <<< "$_ccb_control_targets_raw"
if [ "${#_CCB_CONTROL_TARGETS[@]}" -eq 0 ]; then
  _CCB_CONTROL_TARGETS=(gemini claude codex)
fi

_ccb_control_target_file="${CCB_CONTROL_TARGET_FILE:-}"
_ccb_control_default_target="${CCB_CONTROL_DEFAULT_TARGET:-${_CCB_CONTROL_TARGETS[0]}}"

_ccb_control_read_target() {
  if [ -n "$_ccb_control_target_file" ] && [ -f "$_ccb_control_target_file" ]; then
    local current
    current="$(tr -d '\r\n' < "$_ccb_control_target_file" 2>/dev/null)"
    if [ -n "$current" ]; then
      printf '%s' "$current"
      return
    fi
  fi
  printf '%s' "$_ccb_control_default_target"
}

_ccb_control_write_target() {
  local target="$1"
  if [ -n "$_ccb_control_target_file" ]; then
    mkdir -p "$(dirname "$_ccb_control_target_file")" 2>/dev/null || true
    printf '%s\n' "$target" > "$_ccb_control_target_file"
  fi
}

ccb_target() {
  _ccb_control_read_target
}

ccb_set_target() {
  local requested="${1:-}"
  if [ -z "$requested" ]; then
    printf 'current target: %s\n' "$(ccb_target)"
    return 0
  fi
  local item
  for item in "${_CCB_CONTROL_TARGETS[@]}"; do
    if [ "$item" = "$requested" ]; then
      _ccb_control_write_target "$item"
      printf '\n[CCB-Control] target -> %s\n' "$item"
      return 0
    fi
  done
  printf 'unknown target: %s\n' "$requested" >&2
  return 1
}

ccb_rotate_target() {
  local current next item found=0
  current="$(ccb_target)"
  next="${_CCB_CONTROL_TARGETS[0]}"
  for item in "${_CCB_CONTROL_TARGETS[@]}"; do
    if [ "$found" -eq 1 ]; then
      next="$item"
      break
    fi
    if [ "$item" = "$current" ]; then
      found=1
    fi
  done
  _ccb_control_write_target "$next"
  printf '\n[CCB-Control] target -> %s\n' "$next"
}

ccb_send_line() {
  local payload target
  payload="${READLINE_LINE:-}"
  if [ -z "${payload// }" ]; then
    return 0
  fi
  target="$(ccb_target)"
  READLINE_LINE=""
  READLINE_POINT=0
  printf '\n[CCB-Control] sending to %s\n' "$target"
  ccb-send-pane "$target" "$payload"
}

ccb_send() {
  local payload="$*"
  if [ -z "${payload// }" ]; then
    printf 'usage: ccb_send <message>\n' >&2
    return 1
  fi
  ask "$(ccb_target)" "$payload"
}

_ccb_control_prompt() {
  printf '[to:%s] ' "$(ccb_target)"
}

_ccb_control_install_prompt() {
  local prompt_prefix
  prompt_prefix='$(_ccb_control_prompt)'
  if [ -n "${CCB_CONTROL_BASE_PS1:-}" ]; then
    PS1="${prompt_prefix}${CCB_CONTROL_BASE_PS1}"
  else
    PS1="${prompt_prefix}\u@\h:\w\$ "
  fi
}

_ccb_control_write_target "$(_ccb_control_read_target)"
_ccb_control_install_prompt

bind -x '"\C-]":ccb_rotate_target'
bind -x '"\C-m":ccb_send_line'
bind -x '"\C-j":ccb_send_line'

printf '[CCB-Control] Alt-r rotate pane | Ctrl-] rotate target | Enter send | current target: %s\n' "$(ccb_target)"
