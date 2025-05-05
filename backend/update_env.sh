#!/bin/bash

# Terraformの出力を取得
LAMBDA_URL=$(terraform output -raw lambda_url)

# .envファイルの内容を更新
cat > ../frontend/app/.env << EOF
VITE_LAMBDA_URL=${LAMBDA_URL}
EOF

echo "Updated .env file with Lambda URL: ${LAMBDA_URL}" 
