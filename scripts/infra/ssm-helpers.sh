#!/bin/bash
# Helpers for running SSM send-command + polling for output.
# Source this from other scripts: `source scripts/infra/ssm-helpers.sh`

# ssm_run <instance-id> <profile> <cmd-json-file> [timeout_seconds]
# Sends the command, polls until completion, prints stdout + stderr summary.
ssm_run() {
    local instance="$1"
    local profile="$2"
    local cmd_file="$3"
    local timeout="${4:-600}"
    local region="us-east-2"

    local cmd_id
    cmd_id=$(aws ssm send-command \
        --instance-ids "$instance" \
        --document-name AWS-RunShellScript \
        --parameters "file://$cmd_file" \
        --timeout-seconds "$timeout" \
        --region "$region" \
        --profile "$profile" \
        --query "Command.CommandId" \
        --output text)

    if [ -z "$cmd_id" ] || [ "$cmd_id" = "None" ]; then
        echo "ERROR: send-command failed" >&2
        return 1
    fi

    echo "CommandId: $cmd_id" >&2

    # Poll until the invocation reaches a terminal state
    local _ssm_status=Pending
    local deadline=$(( $(date +%s) + timeout + 30 ))
    while true; do
        if [ "$(date +%s)" -gt "$deadline" ]; then
            echo "ERROR: SSM command poll timeout" >&2
            break
        fi
        _ssm_status=$(aws ssm get-command-invocation \
            --command-id "$cmd_id" \
            --instance-id "$instance" \
            --region "$region" \
            --profile "$profile" \
            --query "Status" \
            --output text 2>/dev/null || echo "Pending")
        case "$_ssm_status" in
            Success|Failed|Cancelled|TimedOut) break ;;
            *) sleep 5 ;;
        esac
    done

    aws ssm get-command-invocation \
        --command-id "$cmd_id" \
        --instance-id "$instance" \
        --region "$region" \
        --profile "$profile" \
        --output json \
        --query "{status:Status,stdout:StandardOutputContent,stderr:StandardErrorContent}"

    # Return non-zero on failure so callers can react
    [ "$_ssm_status" = "Success" ]
}

# ssm_oneliner <instance-id> <profile> <bash-command> [timeout_seconds]
# Convenience: run a single shell command without needing a JSON file.
ssm_oneliner() {
    local instance="$1"
    local profile="$2"
    local cmd="$3"
    local timeout="${4:-300}"
    local tmp
    tmp=$(mktemp -t ssm-cmd.XXXXXX.json)
    python3 -c "import json,sys; print(json.dumps({'commands': [sys.argv[1]]}))" "$cmd" > "$tmp"
    ssm_run "$instance" "$profile" "$tmp" "$timeout"
    local rc=$?
    rm -f "$tmp"
    return $rc
}
