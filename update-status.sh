#!/bin/bash
# Usage: ./update-status.sh <agent> <icon> "<text>"
# Example: ./update-status.sh sam commit "Site pushed to GitHub Pages"
curl -s -X POST http://94.176.236.87:8080/update \
  -H "Content-Type: application/json" \
  -d "{\"agent\":\"$1\",\"icon\":\"$2\",\"text\":\"$3\",\"timeline\":\"$4\"}"
