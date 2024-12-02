#!/usr/bin/env bash

set -e

for item in $(kubectl get namespaces --no-headers -o json | jq -r '.items[].metadata.name'); do         
  output=$(kubectl top pods --sort-by=cpu --no-headers -n ${item} 2>/dev/null);         
  if [ -n "$output" ]; then             
    echo "$output" | awk '{print "{\"pod\":\""$1"\", \"cpu\":\""$2"\", \"memory\":\""$3"\"}"}' | jq -s .;         
  else
    echo "{\"pod\":\"dummy-pod-in-${item}\", \"cpu\":\"0\", \"memory\":\"0Mi\"}" | jq -s .;         
  fi;     
done | tee metric.json
